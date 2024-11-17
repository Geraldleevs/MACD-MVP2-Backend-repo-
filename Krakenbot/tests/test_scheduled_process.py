from django.test import TestCase, tag

from Krakenbot import settings
from Krakenbot.models.firebase import FirebaseToken
from Krakenbot.MVP_Backtest import backtest as backtest_old
from Krakenbot.backtest import backtest as backtest_new
from Krakenbot.get_candles import main as get_candles
from Krakenbot.views import BackTestView


class TestBacktest(TestCase):
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

		results = {result['token_id'] for result in results}
		for token in tokens:
			self.assertIn(token, results)

	@tag('slow')
	def test_backtest_result_same(self):
		candles = get_candles()
		df_ids_old = {}
		df_ids_new = {}

		for candle in candles:
			token_id = candle['token_id']
			fiat = candle['fiat']
			timeframe = candle['timeframe']
			best_strategy = backtest_old(candle['candles'], token_id, timeframe)
			backtest_id = f'{fiat}:{token_id} | {timeframe}'
			df_ids_old[backtest_id] = best_strategy

		for candle in candles:
			token_id = candle['token_id']
			fiat = candle['fiat']
			timeframe = candle['timeframe']
			best_strategy = backtest_new(candle['candles'], token_id, timeframe)
			backtest_id = f'{fiat}:{token_id} | {timeframe}'
			df_ids_new[backtest_id] = best_strategy

		self.assertDictEqual(df_ids_old, df_ids_new)
