from time import perf_counter_ns
from pandas import DataFrame
import asyncio

from django.test import TestCase, tag

from Krakenbot import settings
from Krakenbot.models.firebase import FirebaseToken
from Krakenbot.MVP_Backtest import backtest as backtest_old
from Krakenbot.Realtime_Backtest import apply_backtest as apply_backtest_old, get_livetrade_result
from Krakenbot.backtest import AnalyseBacktest, ApplyBacktest
from Krakenbot.get_candles import main as get_candles
from Krakenbot.views import BackTestView, CalculateFluctuationsView


class TestAnalyseBacktest(TestCase):
	def test_backtest_analysis(self):
		firebase_token = FirebaseToken()
		tokens = firebase_token.filter(is_fiat=False, is_active=True)
		tokens = [token['token_id'] for token in tokens]

		results = BackTestView().backtest()
		self.assertEqual(len(results), len(tokens) * len(settings.TIMEFRAMES.keys()))

		result = results[0]
		self.assertIn('fiat', result)
		self.assertIn('token_id', result)
		self.assertIn('timeframe', result)
		self.assertIn('strategy', result)
		self.assertIn('profit', result)
		self.assertIn('profit_percent', result)
		self.assertIn('risk', result)
		self.assertIn('strategy_description', result)
		self.assertIn('updated_on', result)
		self.assertIn('analysis', result)
		self.assertIn('summary', result)
		self.assertIn('technical_analysis', result)

		results = { result['token_id'] for result in results }
		for token in tokens:
			self.assertIn(token, results)

	@tag('slow')
	def test_backtest_result_same(self):
		candles = get_candles()
		df_ids_old = {}
		df_ids_new = {}

		start_time = perf_counter_ns()
		for candle in candles:
			token_id = candle['token_id']
			fiat = candle['fiat']
			timeframe = candle['timeframe']
			best_strategy = backtest_old(candle['candles'], token_id, timeframe)
			backtest_id = f'{fiat}:{token_id} | {timeframe}'
			df_ids_old[backtest_id] = best_strategy
		old_duration = (perf_counter_ns() - start_time) / 1e9

		start_time = perf_counter_ns()
		for candle in candles:
			token_id = candle['token_id']
			fiat = candle['fiat']
			timeframe = candle['timeframe']
			best_strategy = AnalyseBacktest().analyse_backtest(candle['candles'], token_id, timeframe)
			backtest_id = f'{fiat}:{token_id} | {timeframe}'
			df_ids_new[backtest_id] = best_strategy
		new_duration = (perf_counter_ns() - start_time) / 1e9

		self.assertDictEqual(df_ids_old, df_ids_new)

		print(f'Old Performance: {old_duration:.3f}s')
		print(f'New Performance: {new_duration:.3f}s')


class TestApplyBacktest(TestCase):
	@classmethod
	def setUp(cls):
		cls.all_livetrade_tokens = ['BTC', 'ETH', 'SAND']
		cls.timeframe = '1d'
		cls.test_strategies = [
			'Aroon & CDL3INSIDE (General trend and momentum analysis, 1H)',
			'Stochastic10_3_80_20 & TRIMA (General trend and momentum analysis, 1H)',
			'Aroon & PLUS_DI (General trend and momentum analysis, 1H)',
			'WilliamsR & ATR (Volatility assessment with overbought/oversold conditions, 1D)',
			'RSI74 & Stochastic14_3_80_20 (Unknown Use Case, Unknown Timeframe)',
		]

		all_tokens = FirebaseToken().filter(is_fiat=False)
		cls.all_tokens = { token['id'] + settings.FIAT: token['id'] for token in all_tokens if token['id'] in cls.all_livetrade_tokens }

	def test_apply_backtest(self):
		results =  ApplyBacktest().run(list(self.all_tokens.keys()), settings.INTERVAL_MAP[self.timeframe])
		results = { self.all_tokens[pair]: value for (pair, value) in results.items() } # To replace pair with just token id, e.g. BTCGBP -> BTC

		for strategies in self.test_strategies:
			strategies = strategies.split(' (')[0] # Remove extra information
			[strategy_1, strategy_2] = strategies.split(' & ')

			for token in self.all_livetrade_tokens:
				decision_1 = ApplyBacktest.get_livetrade_result(results[token], strategy_1)
				decision_2 = ApplyBacktest.get_livetrade_result(results[token], strategy_2)

				self.assertIn(decision_1, [-1, 0, 1])
				self.assertIn(decision_2, [-1, 0, 1])

	def test_apply_backtest_result_same(self):
		start_time = perf_counter_ns()
		results_old =  asyncio.run(apply_backtest_old(list(self.all_tokens.keys()), [settings.INTERVAL_MAP[self.timeframe]]))
		old_duration = (perf_counter_ns() - start_time) / 1e9

		start_time = perf_counter_ns()
		results_new =  ApplyBacktest().run(list(self.all_tokens.keys()), settings.INTERVAL_MAP[self.timeframe])
		new_duration = (perf_counter_ns() - start_time) / 1e9

		results_old = { self.all_tokens[pair]: value for (pair, value) in results_old.items() } # To replace pair with just token id, e.g. BTCGBP -> BTC
		results_new = { self.all_tokens[pair]: value for (pair, value) in results_new.items() } # To replace pair with just token id, e.g. BTCGBP -> BTC

		for strategies in self.test_strategies[1:]: # Old backtest do not support CDL3INSIDE
			strategies = strategies.split(' (')[0] # Remove extra information
			[strategy_1, strategy_2] = strategies.split(' & ')

			for token in self.all_livetrade_tokens:
				decision_1_new = ApplyBacktest.get_livetrade_result(results_new[token], strategy_1)
				decision_2_new = ApplyBacktest.get_livetrade_result(results_new[token], strategy_2)

				decision_1_old = get_livetrade_result(results_old[token][str(settings.INTERVAL_MAP[self.timeframe])], strategy_1)
				decision_2_old = get_livetrade_result(results_old[token][str(settings.INTERVAL_MAP[self.timeframe])], strategy_2)

				self.assertEqual(decision_1_new, decision_1_old)
				self.assertEqual(decision_2_new, decision_2_old)

		print(f'Old Performance: {old_duration:.3f}s')
		print(f'New Performance: {new_duration:.3f}s')


class TestFluctuations(TestCase):
	def test_calculate_fluctuations(self):
		calculation = CalculateFluctuationsView()
		candles = calculation.get_candles()
		for pair in candles:
			timestamps = candles[pair]['Unix_Timestamp'].values
			self.assertEqual(timestamps[1] - timestamps[0], 60 * 60)

		fluctuations = calculation.calculate_fluctuations(candles)
		for pair in fluctuations:
			self.assertLessEqual(fluctuations[pair]['low_mean'], 1)
			self.assertGreaterEqual(fluctuations[pair]['high_mean'], 1)

	def test_calculate_accuracy(self):
		test_data = {
			'Open': [0.3588, 0.3587, 0.3592, 0.3614, 0.3598, 0.3598, 0.3576, 0.3557, 0.3589, 0.3593, 0.3625, 0.36, 0.3628, 0.3612, 0.3622, 0.3626, 0.3638, 0.3586, 0.3603, 0.3606, 0.3586, 0.3587, 0.3588, 0.3566],
			'Close': [0.3589, 0.3593, 0.3614, 0.3597, 0.3598, 0.3574, 0.3559, 0.359, 0.3593, 0.362, 0.3599, 0.3629, 0.3612, 0.3622, 0.3626, 0.3638, 0.3587, 0.3602, 0.3606, 0.3588, 0.3589, 0.3589, 0.3568, 0.3585],
			'High': [0.3597, 0.3621, 0.362, 0.3625, 0.3604, 0.3598, 0.3576, 0.3593, 0.3604, 0.3645, 0.3645, 0.3659, 0.3638, 0.363, 0.3628, 0.3658, 0.3649, 0.3613, 0.3609, 0.361, 0.3594, 0.3611, 0.3588, 0.3585],
			'Low': [0.3564, 0.3586, 0.3582, 0.3596, 0.3581, 0.3558, 0.3551, 0.3547, 0.3583, 0.3586, 0.3596, 0.3597, 0.3612, 0.3591, 0.3607, 0.3625, 0.3572, 0.3582, 0.3583, 0.3575, 0.3566, 0.3586, 0.3552, 0.3552],
		}
		expected_fluctuations = {
			'high_mean': 1.005040467,
			'high_std_dev': 0.004323452,
			'low_mean': 0.99497117,
			'low_std_dev': 0.004068439,
			'close_mean': 1.000039252,
			'close_std_dev': 0.005520749,
		}

		test_data = { '1INCHUSD': DataFrame.from_dict(test_data) }
		fluctuations = CalculateFluctuationsView().calculate_fluctuations(test_data)['1INCHUSD']

		self.assertAlmostEqual(fluctuations['high_mean'], expected_fluctuations['high_mean'], delta=0.00000001)
		self.assertAlmostEqual(fluctuations['high_std_dev'], expected_fluctuations['high_std_dev'], delta=0.00000001)
		self.assertAlmostEqual(fluctuations['low_mean'], expected_fluctuations['low_mean'], delta=0.00000001)
		self.assertAlmostEqual(fluctuations['low_std_dev'], expected_fluctuations['low_std_dev'], delta=0.00000001)
		self.assertAlmostEqual(fluctuations['close_mean'], expected_fluctuations['close_mean'], delta=0.00000001)
		self.assertAlmostEqual(fluctuations['close_std_dev'], expected_fluctuations['close_std_dev'], delta=0.00000001)
