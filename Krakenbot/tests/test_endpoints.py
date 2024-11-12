from datetime import datetime
import json

from django.test import TestCase
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer

from Krakenbot.models.firebase import FirebaseLiveTrade, FirebaseOrderBook, FirebaseToken, FirebaseWallet
from Krakenbot.utils import acc_calc
from Krakenbot.views import LiveTradeView, ManualTradeView, MarketView, TradeView


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
		response = TradeView().post(request)
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
		response = TradeView().post(request)
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
		response = TradeView().post(request)
		result, status_code = load_response(response)
		self.created_livetrade_id = result['id']
		self.created_order_id = result['order']['order_id']

		request = POST(
			uid = TEST_UID,
			livetrade = 'UNRESERVE',
			livetrade_id = self.created_livetrade_id,
		)
		response = TradeView().post(request)
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
		response = TradeView().post(request)
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
		response = TradeView().post(request)
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
		response = TradeView().post(request)
		result, status_code = load_response(response)
		self.assertIsNotNone(result)
		self.assertEqual(status_code, 200)
		self.created_order_id = result['order_id']

		request = POST(
			uid = TEST_UID,
			order = 'CANCEL',
			order_id = self.created_order_id,
		)
		response = TradeView().post(request)
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
