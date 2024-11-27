from datetime import datetime
from itertools import combinations
import json

from django.test import TestCase
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer

from Krakenbot import settings
from Krakenbot.models.firebase import FirebaseLiveTrade, FirebaseOrderBook, FirebaseToken, FirebaseWallet
from Krakenbot.backtest import indicator_names
from Krakenbot.utils import acc_calc
from Krakenbot.views import LiveTradeView, ManualTradeView, MarketView, RecalibrateBotView, SimulationView, TradeView


TEST_UID = '7AnP4NG225Sy7a7OAwLbBOK5Qmg2'
TEST_STRATEGY = 'ATR & STOCHF (General trend and momentum analysis, 1H'
TEST_TIMEFRAME = '1d'


def load_response(response: Response):
	response.accepted_renderer = JSONRenderer()
	response.accepted_media_type = "application/json"
	response.renderer_context = {}
	response.render()
	status_code = response.status_code

	if not (200 <= status_code < 300):
		return (None, status_code)
	return (json.loads(response.content), response.status_code)


class GET:
	query_params = {}

	def __init__(self, **kwargs):
		self.query_params = { **self.query_params, **kwargs }


class POST:
	data = {}

	def __init__(self, **kwargs):
		self.data = { **self.data, **kwargs }


class TestMarket(TestCase):
	def test_convert_from(self):
		request = GET(convert_from = 'GBP')
		response = MarketView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIsInstance(result, list)

		result = {res['token']: res for res in result}
		self.assertIn('GBP', result)

		all_tokens = FirebaseToken().filter(is_active=True)
		for token in all_tokens:
			self.assertIn(token['token_id'], result)

		self.assertLess(result['BTC']['price'], 5000)
		self.assertIsInstance(result['BTC']['price_str'], str)
		self.assertLess(float(result['BTC']['price']), 5000)

	def test_convert_to(self):
		request = GET(convert_to = 'GBP')
		response = MarketView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIsInstance(result, list)

		result = {res['token']: res for res in result}
		self.assertIn('GBP', result)

		all_tokens = FirebaseToken().filter(is_active=True)
		for token in all_tokens:
			self.assertIn(token['token_id'], result)

		self.assertGreater(result['BTC']['price'], 5000)
		self.assertIsInstance(result['BTC']['price_str'], str)
		self.assertGreater(float(result['BTC']['price']), 5000)

	def test_exclude(self):
		request = GET(convert_from = 'GBP', exclude = 'GBP')
		response = MarketView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIsInstance(result, list)

		result = {res['token']: res for res in result}
		self.assertNotIn('GBP', result)

		request = GET(convert_to = 'GBP', exclude = 'GBP')
		response = MarketView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIsInstance(result, list)

		result = {res['token']: res for res in result}
		self.assertNotIn('GBP', result)

	def test_convert_specific(self):
		request = GET(convert_from='GBP', convert_to = 'BTC')
		response = MarketView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIsInstance(result, list)
		self.assertEqual(len(result), 1)

		result = result[0]
		self.assertEqual(result['token'], 'BTC')
		self.assertLess(result['price'], 5000)
		self.assertIsInstance(result['price_str'], str)
		self.assertLess(float(result['price_str']), 5000)

	def test_inactive(self):
		request = GET(convert_to='1INCH')
		response = MarketView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIsInstance(result, list)
		self.assertEqual(len(result), 0)

		request = GET(convert_to='1INCH', include_inactive='INCLUDE')
		response = MarketView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIsInstance(result, list)
		self.assertGreater(len(result), 0)

		result = {res['token']: res for res in result}
		self.assertIn('USD', result)
		self.assertNotIn('GBP', result)

	def test_force(self):
		request = GET(convert_to='GBP', include_inactive='INCLUDE')
		response = MarketView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIsInstance(result, list)

		result = {res['token']: res for res in result}
		self.assertNotIn('1INCH', result)
		self.assertNotIn('ARB', result)

		request = GET(convert_to='GBP', force_convert='FORCE', include_inactive='INCLUDE')
		response = MarketView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIsInstance(result, list)

		result = {res['token']: res for res in result}
		self.assertIn('USD', result)
		self.assertIn('1INCH', result)
		self.assertIn('ARB', result)

	def test_get_simulation(self):
		request = GET(get_simulation = 'GET SIMULATION', convert_from = 'GBP', convert_to = 'BTC')
		response = MarketView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIn('simulation_data', result)
		self.assertIn('graph_min', result)
		self.assertIn('graph_max', result)
		self.assertNotIn('backtest_decision', result)
		self.assertLess(result['graph_min'], result['simulation_data'][0])
		self.assertGreater(result['graph_max'], result['simulation_data'][0])
		self.assertEqual(result['simulation_data'][0] - result['graph_min'], result['graph_max'] - result['simulation_data'][0])
		self.assertEqual(len(result['simulation_data']), 120)


class TestSimulation(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.test_data = [
			{ 'Open': 0.3588, 'Close': 0.3589, 'High': 0.3597, 'Low': 0.3564 },
			{ 'Open': 0.3587, 'Close': 0.3593, 'High': 0.3621, 'Low': 0.3586 },
			{ 'Open': 0.3592, 'Close': 0.3614, 'High': 0.3620, 'Low': 0.3582 },
			{ 'Open': 0.3614, 'Close': 0.3597, 'High': 0.3625, 'Low': 0.3596 },
			{ 'Open': 0.3598, 'Close': 0.3598, 'High': 0.3604, 'Low': 0.3581 },
			{ 'Open': 0.3598, 'Close': 0.3574, 'High': 0.3598, 'Low': 0.3558 },
			{ 'Open': 0.3576, 'Close': 0.3559, 'High': 0.3576, 'Low': 0.3551 },
			{ 'Open': 0.3557, 'Close': 0.3590, 'High': 0.3593, 'Low': 0.3547 },
			{ 'Open': 0.3589, 'Close': 0.3593, 'High': 0.3604, 'Low': 0.3583 },
			{ 'Open': 0.3593, 'Close': 0.3620, 'High': 0.3645, 'Low': 0.3586 },
			{ 'Open': 0.3625, 'Close': 0.3599, 'High': 0.3645, 'Low': 0.3596 },
			{ 'Open': 0.3600, 'Close': 0.3629, 'High': 0.3659, 'Low': 0.3597 },
			{ 'Open': 0.3628, 'Close': 0.3612, 'High': 0.3638, 'Low': 0.3612 },
			{ 'Open': 0.3612, 'Close': 0.3622, 'High': 0.3630, 'Low': 0.3591 },
			{ 'Open': 0.3622, 'Close': 0.3626, 'High': 0.3628, 'Low': 0.3607 },
			{ 'Open': 0.3626, 'Close': 0.3638, 'High': 0.3658, 'Low': 0.3625 },
			{ 'Open': 0.3638, 'Close': 0.3587, 'High': 0.3649, 'Low': 0.3572 },
			{ 'Open': 0.3586, 'Close': 0.3602, 'High': 0.3613, 'Low': 0.3582 },
			{ 'Open': 0.3603, 'Close': 0.3606, 'High': 0.3609, 'Low': 0.3583 },
			{ 'Open': 0.3606, 'Close': 0.3588, 'High': 0.3610, 'Low': 0.3575 },
			{ 'Open': 0.3586, 'Close': 0.3589, 'High': 0.3594, 'Low': 0.3566 },
			{ 'Open': 0.3587, 'Close': 0.3589, 'High': 0.3611, 'Low': 0.3586 },
			{ 'Open': 0.3588, 'Close': 0.3568, 'High': 0.3588, 'Low': 0.3552 },
			{ 'Open': 0.3566, 'Close': 0.3585, 'High': 0.3585, 'Low': 0.3552 },
		]

	def test_get_strategies(self):
		request = GET(get_strategies = 'GET STRATEGIES')
		response = SimulationView().get(request)
		result, status_code = load_response(response)

		expected_length = len(list(combinations(indicator_names.values(), 2)))

		self.assertEqual(status_code, 200)
		self.assertEqual(len(result), expected_length)
		self.assertIsInstance(result, list)
		self.assertIsInstance(result[0], str)

	def test_generate_data(self):
		simulation = SimulationView()
		starting_price = 52500
		fluctuations = {
			'close_mean': 1,
			'close_std_dev': 0.001,
			'high_mean': 1.005,
			'high_std_dev': 0.001,
			'low_mean': 0.995,
			'low_std_dev': 0.001,
		}
		simulated_data = simulation.generate_simulated_prices(starting_price, fluctuations, 120)
		simulated_ohlc = simulation.generate_simulated_ohlc(simulated_data, fluctuations)

		for i in range(len(simulated_ohlc)):
			self.assertAlmostEqual(simulated_ohlc[i]['Close'] / simulated_ohlc[i]['Open'], 1, delta=0.005)
			self.assertAlmostEqual(simulated_ohlc[i]['High'] / simulated_ohlc[i]['Open'], 1.005, delta=0.005)
			self.assertAlmostEqual(simulated_ohlc[i]['Low'] / simulated_ohlc[i]['Open'], 0.995, delta=0.005)
			self.assertGreaterEqual(simulated_ohlc[i]['High'], simulated_ohlc[i]['Open'])
			self.assertGreaterEqual(simulated_ohlc[i]['High'], simulated_ohlc[i]['Close'])
			self.assertLessEqual(simulated_ohlc[i]['Low'], simulated_ohlc[i]['Open'])
			self.assertLessEqual(simulated_ohlc[i]['Low'], simulated_ohlc[i]['Close'])
			if i != 0:
				self.assertAlmostEqual(simulated_data[i] / simulated_data[i - 1], 1, delta=0.005)
				self.assertEqual(simulated_ohlc[i]['Open'], simulated_ohlc[i - 1]['Close'])

	def test_combine_ohlc(self):
		ohlc = SimulationView().combine_ohlc(self.test_data, 1)
		ohlc_opens = [ohlc['Open'] for ohlc in ohlc]
		ohlc_closes = [ohlc['Close'] for ohlc in ohlc]
		ohlc_highs = [ohlc['High'] for ohlc in ohlc]
		ohlc_lows = [ohlc['Low'] for ohlc in ohlc]
		self.assertListEqual(ohlc_opens, [ohlc['Open'] for ohlc in self.test_data])
		self.assertListEqual(ohlc_closes, [ohlc['Close'] for ohlc in self.test_data])
		self.assertListEqual(ohlc_highs, [ohlc['High'] for ohlc in self.test_data])
		self.assertListEqual(ohlc_lows, [ohlc['Low'] for ohlc in self.test_data])

		ohlc_4 = SimulationView().combine_ohlc(self.test_data, 4)
		ohlc_4_opens = [ohlc['Open'] for ohlc in ohlc_4]
		ohlc_4_closes = [ohlc['Close'] for ohlc in ohlc_4]
		ohlc_4_highs = [ohlc['High'] for ohlc in ohlc_4]
		ohlc_4_lows = [ohlc['Low'] for ohlc in ohlc_4]
		self.assertListEqual(ohlc_4_opens, [0.3588, 0.3598, 0.3589, 0.3628, 0.3638, 0.3586])
		self.assertListEqual(ohlc_4_closes, [0.3597, 0.359, 0.3629, 0.3638, 0.3588, 0.3585])
		self.assertListEqual(ohlc_4_highs, [0.3625, 0.3604, 0.3659, 0.3658, 0.3649, 0.3611])
		self.assertListEqual(ohlc_4_lows, [0.3564, 0.3547, 0.3583, 0.3591, 0.3572, 0.3552])

		ohlc_24 = SimulationView().combine_ohlc(self.test_data, 24)
		ohlc_24_opens = [ohlc['Open'] for ohlc in ohlc_24]
		ohlc_24_closes = [ohlc['Close'] for ohlc in ohlc_24]
		ohlc_24_highs = [ohlc['High'] for ohlc in ohlc_24]
		ohlc_24_lows = [ohlc['Low'] for ohlc in ohlc_24]
		self.assertListEqual(ohlc_24_opens, [0.3588])
		self.assertListEqual(ohlc_24_closes, [0.3585])
		self.assertListEqual(ohlc_24_highs, [0.3659])
		self.assertListEqual(ohlc_24_lows, [0.3547])

	def test_simulate_backtest_result(self):
		decisions = SimulationView().simulate_backtest(self.test_data, 'MACD & Aroon', '1h')
		self.assertListEqual(decisions, [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, 0])

		decisions = SimulationView().simulate_backtest(self.test_data, 'MACD & Aroon', '4h')
		self.assertListEqual(decisions, [-1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0])

		decisions = SimulationView().simulate_backtest(self.test_data, 'MACD & Aroon', '1d')
		self.assertListEqual(decisions, [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

	def test_get_simulation_with_backtest(self):
		request = GET(convert_from = 'GBP', convert_to = 'BTC', strategy = 'MACD & Aroon', timeframe = '4h', funds = '500', stop_loss = '480', take_profit = '520')
		response = SimulationView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIn('simulation_data', result)
		self.assertIn('graph_min', result)
		self.assertIn('graph_max', result)
		self.assertIn('funds_values', result)
		self.assertIn('bot_actions', result)
		self.assertIn('stopped_by', result)
		self.assertIn('stopped_at', result)

		self.assertLess(result['graph_min'], result['simulation_data'][0])
		self.assertGreater(result['graph_max'], result['simulation_data'][0])
		self.assertEqual(result['simulation_data'][0] - result['graph_min'], result['graph_max'] - result['simulation_data'][0])
		self.assertEqual(len(result['simulation_data']), 120)
		self.assertEqual(len(result['funds_values']), 120)
		self.assertEqual(len(result['bot_actions']), 120)

		for index in range(120):
			prev_funds = 500 if index == 0 else result['funds_values'][index - 1]
			data = result['simulation_data'][index]
			cur_funds = result['funds_values'][index]
			action = result['bot_actions'][index]

			self.assertIn(action, [-1, 0, 1])

			if action == 1:
				self.assertAlmostEqual(float(acc_calc(prev_funds, '/', data)), cur_funds, 18)

			elif action == -1:
				self.assertEqual(float(acc_calc(prev_funds, '*', data, 2)), cur_funds)

			elif action == 0:
				self.assertEqual(prev_funds, cur_funds)

	def test_get_simulation(self):
		request = GET(convert_from = 'GBP', convert_to = 'BTC')
		response = SimulationView().get(request)
		result, status_code = load_response(response)

		self.assertEqual(status_code, 200)
		self.assertIn('simulation_data', result)
		self.assertIn('graph_min', result)
		self.assertIn('graph_max', result)
		self.assertNotIn('backtest_decision', result)
		self.assertLess(result['graph_min'], result['simulation_data'][0])
		self.assertGreater(result['graph_max'], result['simulation_data'][0])
		self.assertEqual(result['simulation_data'][0] - result['graph_min'], result['graph_max'] - result['simulation_data'][0])
		self.assertEqual(len(result['simulation_data']), 120)

		request = GET(convert_from = 'GBP', convert_to = 'BTC')
		response = SimulationView().get(request)
		result_2 = load_response(response)[0]
		self.assertEqual(result_2['simulation_data'][0], result['simulation_data'][0])
		self.assertNotEqual(result_2['simulation_data'], result['simulation_data'])

	def test_get_simulation_invalid_token(self):
		request = GET(convert_from = '1INCH', convert_to = 'BTC')
		response = SimulationView().get(request)
		result, status_code = load_response(response)
		self.assertEqual(status_code, 400)
		self.assertIsNone(result)

		request = GET(convert_from = 'USD', convert_to = 'INVALID')
		response = SimulationView().get(request)
		result, status_code = load_response(response)
		self.assertEqual(status_code, 400)
		self.assertIsNone(result)

	def test_get_simulation_invalid_strategy(self):
		request = GET(convert_from = 'GBP', convert_to = 'BTC', strategy = 'INVALID STRATEGY', timeframe = '1d', funds = '500')
		response = SimulationView().get(request)
		result, status_code = load_response(response)
		self.assertEqual(status_code, 400)
		self.assertIsNone(result)

	def test_get_simulation_invalid_timeframe(self):
		request = GET(convert_from = 'GBP', convert_to = 'BTC', strategy = 'MACD & Aroon', timeframe = '000', funds = '500')
		response = SimulationView().get(request)
		result, status_code = load_response(response)
		self.assertEqual(status_code, 400)
		self.assertIsNone(result)

	def test_get_simulation_invalid_take_profit(self):
		request = GET(convert_from = 'GBP', convert_to = 'BTC', strategy = 'INVALID STRATEGY', timeframe = '1d', funds = '500', take_profit = '400')
		response = SimulationView().get(request)
		result, status_code = load_response(response)
		self.assertEqual(status_code, 400)
		self.assertIsNone(result)

	def test_get_simulation_invalid_stop_loss(self):
		request = GET(convert_from = 'GBP', convert_to = 'BTC', strategy = 'MACD & Aroon', timeframe = '000', funds = '500', stop_loss = '800')
		response = SimulationView().get(request)
		result, status_code = load_response(response)
		self.assertEqual(status_code, 400)
		self.assertIsNone(result)

		request = GET(convert_from = 'GBP', convert_to = 'BTC', strategy = 'INVALID STRATEGY', timeframe = '1d', funds = '500', stop_loss = '-5')
		response = SimulationView().get(request)
		result, status_code = load_response(response)
		self.assertEqual(status_code, 400)
		self.assertIsNone(result)


class TestLiveTrade(TestCase):
	def setUp(self):
		self.created_livetrade_id = None
		self.created_order_id = None
		self.original_wallet = None

		firebase_wallet = FirebaseWallet(TEST_UID)
		original_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_btc_wallet = firebase_wallet.get_wallet('BTC')
		if len(original_btc_wallet) > 0:
			original_btc_wallet = original_btc_wallet[0]
		else:
			original_btc_wallet = {}

		self.original_wallet = {
			'GBP': (
				original_gbp_wallet.get(FirebaseWallet.USER_AMOUNT),
				original_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR),
				original_gbp_wallet.get(FirebaseWallet.BOT_AMOUNT),
				original_gbp_wallet.get(FirebaseWallet.BOT_AMOUNT_STR),
				original_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT),
				original_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR)
			),
			'BTC': (
				original_btc_wallet.get(FirebaseWallet.USER_AMOUNT),
				original_btc_wallet.get(FirebaseWallet.USER_AMOUNT_STR),
				original_btc_wallet.get(FirebaseWallet.BOT_AMOUNT),
				original_btc_wallet.get(FirebaseWallet.BOT_AMOUNT_STR),
				original_btc_wallet.get(FirebaseWallet.HOLD_AMOUNT),
				original_btc_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR)
			),
		}

	def tearDown(self):
		if self.created_livetrade_id is not None:
			FirebaseLiveTrade(TEST_UID).close(self.created_livetrade_id)
			self.created_order_id = None
		if self.created_order_id is not None:
			FirebaseOrderBook().cancel_order(self.created_order_id)
		if self.original_wallet is not None:
			for token in self.original_wallet:
				(user, user_str, bot, bot_str, hold, hold_str) = self.original_wallet[token]
				data = {
					FirebaseWallet.USER_AMOUNT: user,
					FirebaseWallet.USER_AMOUNT_STR: user_str,
					FirebaseWallet.BOT_AMOUNT: bot,
					FirebaseWallet.BOT_AMOUNT_STR: bot_str,
					FirebaseWallet.HOLD_AMOUNT: hold,
					FirebaseWallet.HOLD_AMOUNT_STR: hold_str
				}
				FirebaseWallet(TEST_UID)._edit(token, data)

	def test_reserve(self):
		firebase_wallet = FirebaseWallet(TEST_UID)
		original_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_user_amount = original_wallet.get('amount_str', '0')
		original_bot_amount = original_wallet.get('krakenbot_amount_str', '0')

		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME,
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)

		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)

		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		self.assertEqual(result['uid'], TEST_UID)
		self.assertLess(datetime.strptime(result['start_time'], '%Y-%m-%dT%H:%M:%S.%fZ'), datetime.now())
		self.assertEqual(result['strategy'], TEST_STRATEGY)
		self.assertEqual(result['timeframe'], TEST_TIMEFRAME)
		self.assertEqual(result['cur_token'], 'GBP')
		self.assertEqual(result['fiat'], 'GBP')
		self.assertEqual(result['token_id'], 'BTC')
		self.assertEqual(result['initial_amount'], 100)
		self.assertEqual(result['initial_amount_str'], '100')
		self.assertEqual(result['amount'], 100)
		self.assertEqual(result['amount_str'], '100')
		self.assertEqual(result['is_active'], True)
		self.assertEqual(result['take_profit'], 110)
		self.assertEqual(result['stop_loss'], 90)
		self.assertEqual(result['status'], 'READY_TO_TRADE')
		self.assertEqual(result['order']['status'], 'OPEN')

		new_wallet = firebase_wallet.get_wallet('GBP')[0]
		new_user_amount = new_wallet.get('amount_str', '0')
		new_bot_amount = new_wallet.get('krakenbot_amount_str', '0')

		self.assertTrue(acc_calc(acc_calc(original_user_amount, '-', new_user_amount), '==', 100))
		self.assertTrue(acc_calc(acc_calc(new_bot_amount, '-', original_bot_amount), '==', 100))

	def test_reserve_invalid_amount(self):
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '-50',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_livetrade_id = result['id']
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_reserve_invalid_stop_loss(self):
		# Stop loss < 0
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '90',
			stop_loss = '-5',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_livetrade_id = result['id']
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

		# Stop loss > amount
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '120',
			stop_loss = '110',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_livetrade_id = result['id']
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

		# Stop loss == amount
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '120',
			stop_loss = '100',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_livetrade_id = result['id']
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_reserve_invalid_take_profit(self):
		# Take Profit < 0
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '-5',
			stop_loss = '110',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_livetrade_id = result['id']
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

		# Take Profit <= amount
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '90',
			stop_loss = '80',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_livetrade_id = result['id']
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

		# Take Profit <= amount
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '100',
			stop_loss = '80',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_livetrade_id = result['id']
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_reserve_invalid_timeframe(self):
		# Invalid timeframe
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '100',
			stop_loss = '100',
			strategy = TEST_STRATEGY,
			timeframe = ''
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_livetrade_id = result['id']
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_reserve_invalid_strategy(self):
		# Invalid strategy
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '100',
			stop_loss = '100',
			strategy = '',
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_livetrade_id = result['id']
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_update_invalid_stop_loss(self):
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		# Stop loss == amount
		request = POST(
			uid = TEST_UID,
			livetrade = 'UPDATE',
			livetrade_id = self.created_livetrade_id,
			stop_loss = '100',
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

		# Stop loss > amount
		request = POST(
			uid = TEST_UID,
			livetrade = 'UPDATE',
			livetrade_id = self.created_livetrade_id,
			stop_loss = '110',
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

		# Stop loss < 0
		request = POST(
			uid = TEST_UID,
			livetrade = 'UPDATE',
			livetrade_id = self.created_livetrade_id,
			stop_loss = '-5',
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_update_invalid_take_profit(self):
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		# Take profit == amount
		request = POST(
			uid = TEST_UID,
			livetrade = 'UPDATE',
			livetrade_id = self.created_livetrade_id,
			take_profit = '100',
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

		# Take profit < amount
		request = POST(
			uid = TEST_UID,
			livetrade = 'UPDATE',
			livetrade_id = self.created_livetrade_id,
			take_profit = '90',
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

		# Take profit < 0
		request = POST(
			uid = TEST_UID,
			livetrade = 'UPDATE',
			livetrade_id = self.created_livetrade_id,
			take_profit = '-5',
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_update_invalid_livetrade_id(self):
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		request = POST(
			uid = TEST_UID,
			livetrade = 'UPDATE',
			livetrade_id = 'invalid_id',
			take_profit = '120',
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_update_invalid_user_id(self):
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		request = POST(
			uid = 'invalid_user',
			livetrade = 'UPDATE',
			livetrade_id = self.created_livetrade_id,
			take_profit = '120',
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_update(self):
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME,
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		request = POST(
			uid = TEST_UID,
			livetrade = 'UPDATE',
			livetrade_id = self.created_livetrade_id,
			take_profit = '150',
			stop_loss = '50',
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)

		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.assertEqual(result['take_profit'], 150)
		self.assertEqual(result['stop_loss'], 50)

	def test_unreserve(self):
		firebase_wallet = FirebaseWallet(TEST_UID)
		original_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_user_amount = original_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		original_bot_amount = original_wallet.get(FirebaseWallet.BOT_AMOUNT_STR, '0')

		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME,
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		request = POST(
			uid = TEST_UID,
			livetrade = 'UNRESERVE',
			livetrade_id = self.created_livetrade_id,
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)

		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)

		new_wallet = firebase_wallet.get_wallet('GBP')[0]
		new_user_amount = new_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		new_bot_amount = new_wallet.get(FirebaseWallet.BOT_AMOUNT_STR, '0')

		self.assertEqual(new_user_amount, original_user_amount)
		self.assertEqual(new_bot_amount, original_bot_amount)
		self.assertEqual(FirebaseLiveTrade().get(self.created_livetrade_id)['status'], 'COMPLETED')
		self.assertEqual(FirebaseOrderBook().get(self.created_order_id)['status'], 'CANCELLED')

		self.created_livetrade_id = None
		self.created_order_id = None

	def test_sell_not_convert(self):
		firebase_wallet = FirebaseWallet(TEST_UID)
		original_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_user_amount = original_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		original_bot_amount = original_wallet.get(FirebaseWallet.BOT_AMOUNT_STR, '0')

		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME,
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		request = POST(
			uid = TEST_UID,
			livetrade = 'SELL',
			livetrade_id = self.created_livetrade_id,
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)

		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)

		new_wallet = firebase_wallet.get_wallet('GBP')[0]
		new_user_amount = new_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		new_bot_amount = new_wallet.get(FirebaseWallet.BOT_AMOUNT_STR, '0')

		self.assertEqual(new_user_amount, original_user_amount)
		self.assertEqual(new_bot_amount, original_bot_amount)

		self.created_livetrade_id = None
		self.created_order_id = None

	def test_sell(self):
		firebase_wallet = FirebaseWallet(TEST_UID)
		original_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_gbp_user_amount = original_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		original_gbp_bot_amount = original_gbp_wallet.get(FirebaseWallet.BOT_AMOUNT_STR, '0')
		original_gbp_hold_amount = original_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		original_btc_wallet = firebase_wallet.get_wallet('BTC')
		if len(original_btc_wallet) > 0:
			original_btc_wallet = original_btc_wallet[0]
			original_btc_user_amount = original_btc_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
			original_btc_bot_amount = original_btc_wallet.get(FirebaseWallet.BOT_AMOUNT_STR, '0')
			original_btc_hold_amount = original_btc_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')
		else:
			original_btc_wallet = {}
			original_btc_user_amount = 0
			original_btc_bot_amount = 0
			original_btc_hold_amount = 0

		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME,
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		transaction = FirebaseOrderBook().complete_order(self.created_order_id)
		traded_to_btc = acc_calc(transaction['volume'], '*', transaction['price_str'])
		self.created_order_id = None

		request = POST(
			uid = TEST_UID,
			livetrade = 'SELL',
			livetrade_id = self.created_livetrade_id,
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)

		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_order_id = result['order']['order_id']

		new_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		new_gbp_user_amount = new_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		new_gbp_bot_amount = new_gbp_wallet.get(FirebaseWallet.BOT_AMOUNT_STR, '0')
		new_gbp_hold_amount = new_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		new_btc_wallet = firebase_wallet.get_wallet('BTC')[0]
		new_btc_user_amount = new_btc_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		new_btc_bot_amount = new_btc_wallet.get(FirebaseWallet.BOT_AMOUNT_STR, '0')
		new_btc_hold_amount = new_btc_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		self.assertTrue(acc_calc(new_gbp_user_amount, '==', acc_calc(original_gbp_user_amount, '-', 100)))
		self.assertTrue(acc_calc(new_gbp_bot_amount, '==', original_gbp_bot_amount))
		self.assertTrue(acc_calc(new_gbp_hold_amount, '==', original_gbp_hold_amount))
		self.assertTrue(acc_calc(new_btc_user_amount, '==', original_btc_user_amount))
		self.assertTrue(acc_calc(new_btc_bot_amount, '==', original_btc_bot_amount))
		self.assertTrue(acc_calc(new_btc_hold_amount, '==', acc_calc(original_btc_hold_amount, '+', traded_to_btc)))

		self.created_livetrade_id = None

	def test_invalid_type(self):
		request = POST(
			uid = TEST_UID,
			livetrade = 'INVALID TYPE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_livetrade_id = result['id']
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_not_enough_token(self):
		firebase_wallet = FirebaseWallet(TEST_UID)
		gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		user_amount = gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		invalid_amount = str(acc_calc(user_amount, '+', 1))

		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = invalid_amount,
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_livetrade_id = result['id']
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)


class TestManualTrade(TestCase):
	def setUp(self):
		self.created_livetrade_id = None
		self.created_order_id = None
		self.original_wallet = None

		firebase_wallet = FirebaseWallet(TEST_UID)
		original_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_btc_wallet = firebase_wallet.get_wallet('BTC')
		if len(original_btc_wallet) > 0:
			original_btc_wallet = original_btc_wallet[0]
		else:
			original_btc_wallet = {}

		self.original_wallet = {
			'GBP': (
				original_gbp_wallet.get(FirebaseWallet.USER_AMOUNT),
				original_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR),
				original_gbp_wallet.get(FirebaseWallet.BOT_AMOUNT),
				original_gbp_wallet.get(FirebaseWallet.BOT_AMOUNT_STR),
				original_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT),
				original_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR)
			),
			'BTC': (
				original_btc_wallet.get(FirebaseWallet.USER_AMOUNT),
				original_btc_wallet.get(FirebaseWallet.USER_AMOUNT_STR),
				original_btc_wallet.get(FirebaseWallet.BOT_AMOUNT),
				original_btc_wallet.get(FirebaseWallet.BOT_AMOUNT_STR),
				original_btc_wallet.get(FirebaseWallet.HOLD_AMOUNT),
				original_btc_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR)
			),
		}

	def tearDown(self):
		if self.created_livetrade_id is not None:
			FirebaseLiveTrade(TEST_UID).close(self.created_livetrade_id)
			self.created_order_id = None
		if self.created_order_id is not None:
			FirebaseOrderBook().cancel_order(self.created_order_id)
		if self.original_wallet is not None:
			for token in self.original_wallet:
				(user, user_str, bot, bot_str, hold, hold_str) = self.original_wallet[token]
				data = {
					FirebaseWallet.USER_AMOUNT: user,
					FirebaseWallet.USER_AMOUNT_STR: user_str,
					FirebaseWallet.BOT_AMOUNT: bot,
					FirebaseWallet.BOT_AMOUNT_STR: bot_str,
					FirebaseWallet.HOLD_AMOUNT: hold,
					FirebaseWallet.HOLD_AMOUNT_STR: hold_str
				}
				FirebaseWallet(TEST_UID)._edit(token, data)

	def test_invalid_type(self):
		request = POST(
			uid = TEST_UID,
			order = 'INVALID TYPE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			order_price = '0.05',
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_create_order(self):
		firebase_wallet = FirebaseWallet(TEST_UID)
		original_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_gbp_user_amount = original_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		original_gbp_hold_amount = original_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		request = POST(
			uid = TEST_UID,
			order = 'ORDER',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '500',
			order_price = '0.05',
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_order_id = result['order_id']

		self.assertEqual(result['uid'], TEST_UID)
		self.assertLess(datetime.strptime(result['created_time'], '%Y-%m-%dT%H:%M:%S.%fZ'), datetime.now())
		self.assertEqual(result['created_by'], 'USER')
		self.assertEqual(result['from_token'], 'GBP')
		self.assertEqual(result['to_token'], 'BTC')
		self.assertEqual(result['volume'], '500')
		self.assertEqual(result['price'], 0.05)
		self.assertEqual(result['price_str'], '0.05')
		self.assertEqual(result['status'], 'OPEN')

		new_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		new_gbp_user_amount = new_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		new_gbp_hold_amount = new_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		self.assertTrue(acc_calc(acc_calc(original_gbp_user_amount, '-', 500), '==', new_gbp_user_amount))
		self.assertTrue(acc_calc(acc_calc(original_gbp_hold_amount, '+', 500), '==', new_gbp_hold_amount))

	def test_create_order_invalid_amount(self):
		request = POST(
			uid = TEST_UID,
			order = 'ORDER',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '-50',
			order_price = '0.05',
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_create_order_invalid_price(self):
		request = POST(
			uid = TEST_UID,
			order = 'ORDER',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '50',
			order_price = '-0.05',
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_create_order_not_enough_token(self):
		firebase_wallet = FirebaseWallet(TEST_UID)
		gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		user_amount = gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		invalid_amount = str(acc_calc(user_amount, '+', 1))

		request = POST(
			uid = TEST_UID,
			order = 'ORDER',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = invalid_amount,
			order_price = '0.05',
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_order_id = result['order']['order_id']
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_complete_order(self):
		firebase_wallet = FirebaseWallet(TEST_UID)
		original_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_gbp_user_amount = original_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		original_gbp_hold_amount = original_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		original_btc_wallet = firebase_wallet.get_wallet('BTC')
		if len(original_btc_wallet) > 0:
			original_btc_wallet = original_btc_wallet[0]
			original_btc_user_amount = original_btc_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
			original_btc_hold_amount = original_btc_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')
		else:
			original_btc_wallet = {}
			original_btc_user_amount = 0
			original_btc_hold_amount = 0

		request = POST(
			uid = TEST_UID,
			order = 'ORDER',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '500',
			order_price = '0.05',
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_order_id = result['order_id']

		FirebaseOrderBook().complete_order(self.created_order_id)
		self.created_order_id = None

		new_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		new_gbp_user_amount = new_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		new_gbp_hold_amount = new_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		new_btc_wallet = firebase_wallet.get_wallet('BTC')[0]
		new_btc_user_amount = new_btc_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		new_btc_hold_amount = new_btc_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		self.assertTrue(acc_calc(acc_calc(original_gbp_user_amount, '-', 500), '==', new_gbp_user_amount))
		self.assertTrue(acc_calc(original_gbp_hold_amount, '==', new_gbp_hold_amount))
		self.assertTrue(acc_calc(acc_calc(original_btc_user_amount, '+', acc_calc(500, '*', 0.05)), '==', new_btc_user_amount))
		self.assertTrue(acc_calc(original_btc_hold_amount, '==', new_btc_hold_amount))

	def test_cancel_order(self):
		firebase_wallet = FirebaseWallet(TEST_UID)
		original_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_gbp_user_amount = original_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		original_gbp_hold_amount = original_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		request = POST(
			uid = TEST_UID,
			order = 'ORDER',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '500',
			order_price = '0.05',
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_order_id = result['order_id']

		request = POST(
			uid = TEST_UID,
			order = 'CANCEL',
			order_id = self.created_order_id,
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.assertEqual(result['status'], 'CANCELLED')
		self.created_order_id = None

		new_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		new_gbp_user_amount = new_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		new_gbp_hold_amount = new_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		self.assertTrue(acc_calc(original_gbp_user_amount, '==', new_gbp_user_amount))
		self.assertTrue(acc_calc(original_gbp_hold_amount, '==', new_gbp_hold_amount))

	def test_cancel_order_invalid_order_id(self):
		request = POST(
			uid = TEST_UID,
			order = 'ORDER',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '500',
			order_price = '0.05',
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_order_id = result['order_id']

		request = POST(
			uid = TEST_UID,
			order = 'CANCEL',
			order_id = 'INVALID ID',
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_order_id = None
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_cancel_order_invalid_user_id(self):
		request = POST(
			uid = TEST_UID,
			order = 'ORDER',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '500',
			order_price = '0.05',
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_order_id = result['order_id']

		request = POST(
			uid = 'INVALID USER',
			order = 'CANCEL',
			order_id = self.created_order_id,
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_order_id = None
		self.assertIsNone(result)
		self.assertEqual(status_code, 400)

	def test_cancel_order_invalid_bot(self):
		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME,
		)
		response = LiveTradeView().post(request)
		result, status_code = load_response(response)
		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		request = POST(
			uid = TEST_UID,
			order = 'CANCEL',
			order_id = self.created_order_id,
		)
		response = ManualTradeView().post(request)
		result, status_code = load_response(response)
		if result is not None:
			self.created_order_id = None
		self.assertIsNone(result)
		self.assertEqual(status_code, 401)


class TestTradeView(TestCase):
	def setUp(self):
		self.created_livetrade_id = None
		self.created_order_id = None
		self.original_wallet = None

		firebase_wallet = FirebaseWallet(TEST_UID)
		original_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_btc_wallet = firebase_wallet.get_wallet('BTC')
		if len(original_btc_wallet) > 0:
			original_btc_wallet = original_btc_wallet[0]
		else:
			original_btc_wallet = {}

		self.original_wallet = {
			'GBP': (
				original_gbp_wallet.get(FirebaseWallet.USER_AMOUNT),
				original_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR),
				original_gbp_wallet.get(FirebaseWallet.BOT_AMOUNT),
				original_gbp_wallet.get(FirebaseWallet.BOT_AMOUNT_STR),
				original_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT),
				original_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR)
			),
			'BTC': (
				original_btc_wallet.get(FirebaseWallet.USER_AMOUNT),
				original_btc_wallet.get(FirebaseWallet.USER_AMOUNT_STR),
				original_btc_wallet.get(FirebaseWallet.BOT_AMOUNT),
				original_btc_wallet.get(FirebaseWallet.BOT_AMOUNT_STR),
				original_btc_wallet.get(FirebaseWallet.HOLD_AMOUNT),
				original_btc_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR)
			),
		}

	def tearDown(self):
		if self.created_livetrade_id is not None:
			FirebaseLiveTrade(TEST_UID).close(self.created_livetrade_id)
			self.created_order_id = None
		if self.created_order_id is not None:
			FirebaseOrderBook().cancel_order(self.created_order_id)
		if self.original_wallet is not None:
			for token in self.original_wallet:
				(user, user_str, bot, bot_str, hold, hold_str) = self.original_wallet[token]
				data = {
					FirebaseWallet.USER_AMOUNT: user,
					FirebaseWallet.USER_AMOUNT_STR: user_str,
					FirebaseWallet.BOT_AMOUNT: bot,
					FirebaseWallet.BOT_AMOUNT_STR: bot_str,
					FirebaseWallet.HOLD_AMOUNT: hold,
					FirebaseWallet.HOLD_AMOUNT_STR: hold_str
				}
				FirebaseWallet(TEST_UID)._edit(token, data)

	def test_reserve(self):
		firebase_wallet = FirebaseWallet(TEST_UID)
		original_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_user_amount = original_wallet.get('amount_str', '0')
		original_bot_amount = original_wallet.get('krakenbot_amount_str', '0')

		request = POST(
			uid = TEST_UID,
			livetrade = 'RESERVE',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '100',
			take_profit = '110',
			stop_loss = '90',
			strategy = TEST_STRATEGY,
			timeframe = TEST_TIMEFRAME,
		)
		response = TradeView().post(request)
		result, status_code = load_response(response)

		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)

		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		self.assertEqual(result['uid'], TEST_UID)
		self.assertLess(datetime.strptime(result['start_time'], '%Y-%m-%dT%H:%M:%S.%fZ'), datetime.now())
		self.assertEqual(result['strategy'], TEST_STRATEGY)
		self.assertEqual(result['timeframe'], TEST_TIMEFRAME)
		self.assertEqual(result['cur_token'], 'GBP')
		self.assertEqual(result['fiat'], 'GBP')
		self.assertEqual(result['token_id'], 'BTC')
		self.assertEqual(result['initial_amount'], 100)
		self.assertEqual(result['initial_amount_str'], '100')
		self.assertEqual(result['amount'], 100)
		self.assertEqual(result['amount_str'], '100')
		self.assertEqual(result['is_active'], True)
		self.assertEqual(result['take_profit'], 110)
		self.assertEqual(result['stop_loss'], 90)
		self.assertEqual(result['status'], 'READY_TO_TRADE')
		self.assertEqual(result['order']['status'], 'OPEN')

		new_wallet = firebase_wallet.get_wallet('GBP')[0]
		new_user_amount = new_wallet.get('amount_str', '0')
		new_bot_amount = new_wallet.get('krakenbot_amount_str', '0')

		self.assertTrue(acc_calc(acc_calc(original_user_amount, '-', new_user_amount), '==', 100))
		self.assertTrue(acc_calc(acc_calc(new_bot_amount, '-', original_bot_amount), '==', 100))

	def test_create_order(self):
		firebase_wallet = FirebaseWallet(TEST_UID)
		original_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		original_gbp_user_amount = original_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		original_gbp_hold_amount = original_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		request = POST(
			uid = TEST_UID,
			order = 'ORDER',
			from_token = 'GBP',
			to_token = 'BTC',
			from_amount = '500',
			order_price = '0.05',
		)
		response = TradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_order_id = result['order_id']

		self.assertEqual(result['uid'], TEST_UID)
		self.assertLess(datetime.strptime(result['created_time'], '%Y-%m-%dT%H:%M:%S.%fZ'), datetime.now())
		self.assertEqual(result['created_by'], 'USER')
		self.assertEqual(result['from_token'], 'GBP')
		self.assertEqual(result['to_token'], 'BTC')
		self.assertEqual(result['volume'], '500')
		self.assertEqual(result['price'], 0.05)
		self.assertEqual(result['price_str'], '0.05')
		self.assertEqual(result['status'], 'OPEN')

		new_gbp_wallet = firebase_wallet.get_wallet('GBP')[0]
		new_gbp_user_amount = new_gbp_wallet.get(FirebaseWallet.USER_AMOUNT_STR, '0')
		new_gbp_hold_amount = new_gbp_wallet.get(FirebaseWallet.HOLD_AMOUNT_STR, '0')

		self.assertTrue(acc_calc(acc_calc(original_gbp_user_amount, '-', 500), '==', new_gbp_user_amount))
		self.assertTrue(acc_calc(acc_calc(original_gbp_hold_amount, '+', 500), '==', new_gbp_hold_amount))


class TestRecalibrate(TestCase):
	def tearDown(self):
		settings.DEBUG = True

	def test_calibrate_not_allowed(self):
		settings.DEBUG = False
		response = RecalibrateBotView().post()
		_, status_code = load_response(response)
		self.assertEqual(status_code, 404)
