import inspect
import json
from functools import partial

import numpy as np
import pandas as pd
from django.conf import settings
from django.test import SimpleTestCase

from core import old_mvp_backtest
from core.technical_analysis import TechnicalAnalysis, TechnicalAnalysisTemplate

CORE_DIR = settings.BASE_DIR / 'core'
ORACLE_DIR = CORE_DIR / 'oracles'


class TestTechnicalAnalysis(SimpleTestCase):
	@classmethod
	def setUpClass(cls):
		df = pd.read_csv(ORACLE_DIR / 'BTCUSDT.csv')
		df = df.iloc[:, 1:6]
		df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
		cls.ohlc_data = df
		cls.TA = TechnicalAnalysis()
		cls.TA_templates = TechnicalAnalysisTemplate(cls.TA)

	def test_indicator_options(self):
		options = self.TA.options
		for ta in options:
			self.assertIsNotNone(getattr(self.TA, ta))
			self.assertIsNotNone(options[ta].get('name'))

		with open(ORACLE_DIR / 'technical_analysis' / 'indicators.txt') as file:
			text = file.read()
		self.assertEqual(text, json.dumps(options, indent=2))

	def test_technical_templates(self):
		templates = self.TA_templates.templates
		for ta in templates:
			self.assertIsNotNone(templates[ta]['description'])
			self.assertIsNotNone(templates[ta]['function'])
			self.assertTrue(callable(templates[ta]['function']))

		templates = {
			template: {
				'description': templates[template]['description'],
				'function': inspect.getsource(templates[template]['function'].func)
				if isinstance(templates[template]['function'], partial)
				else inspect.getsource(templates[template]['function']),
			}
			for template in templates
		}

		with open(ORACLE_DIR / 'technical_analysis' / 'templates.txt') as file:
			text = file.read()
		self.assertEqual(text, json.dumps(templates, indent=2))

	def test_compare_technical_analysis(self):
		TAs = {
			'macd': {'old': old_mvp_backtest.use_macd},
			'sma': {'old': old_mvp_backtest.use_sma},
			'ema': {'old': old_mvp_backtest.use_ema},
			'adx': {'old': old_mvp_backtest.use_adx},
			'aroon': {'old': old_mvp_backtest.use_aroon},
			'rsi_70_30': {'old': lambda df: old_mvp_backtest.use_rsi(df, 70, 30)},
			'rsi_71_31': {'old': lambda df: old_mvp_backtest.use_rsi(df, 71, 31)},
			'rsi_72_32': {'old': lambda df: old_mvp_backtest.use_rsi(df, 72, 32)},
			'rsi_73_33': {'old': lambda df: old_mvp_backtest.use_rsi(df, 73, 33)},
			'rsi_74_34': {'old': lambda df: old_mvp_backtest.use_rsi(df, 74, 34)},
			'rsi_75_35': {'old': lambda df: old_mvp_backtest.use_rsi(df, 75, 35)},
			'stoch_14_3_80_20': {'old': lambda df: old_mvp_backtest.use_stochastic(df, 14, 3, 80, 20)},
			'stoch_14_3_85_15': {'old': lambda df: old_mvp_backtest.use_stochastic(df, 14, 3, 85, 15)},
			'stoch_10_3_80_20': {'old': lambda df: old_mvp_backtest.use_stochastic(df, 10, 3, 80, 20)},
			'stoch_10_3_85_15': {'old': lambda df: old_mvp_backtest.use_stochastic(df, 10, 3, 85, 15)},
			'stoch_21_5_80_20': {'old': lambda df: old_mvp_backtest.use_stochastic(df, 21, 5, 80, 20)},
			'stoch_21_5_85_15': {'old': lambda df: old_mvp_backtest.use_stochastic(df, 21, 5, 85, 15)},
			'cci': {'old': old_mvp_backtest.use_cci},
			'willr': {'old': old_mvp_backtest.use_williams_r},
			'mom': {'old': old_mvp_backtest.use_momentum},
			'bbands': {'old': old_mvp_backtest.use_bbands},
			'atr': {'old': old_mvp_backtest.use_atr},
			'donchian': {'old': old_mvp_backtest.use_donchian_channel},
			'obv': {'old': old_mvp_backtest.use_obv},
			'mfi': {'old': old_mvp_backtest.use_mfi},
			'ad': {'old': old_mvp_backtest.use_ad},
			'ichimoku': {'old': old_mvp_backtest.use_ichimoku},
			'aroonosc': {'old': old_mvp_backtest.use_aroonosc},
			'dema': {'old': old_mvp_backtest.use_dema},
			'tema': {'old': old_mvp_backtest.use_tema},
			'cdl2crows': {'old': old_mvp_backtest.use_cdl2crows},
			'cdl3blackcrows': {'old': old_mvp_backtest.use_cdl3blackcrows},
			'cdl3inside': {'old': old_mvp_backtest.use_cdl3inside},
			'adxr': {'old': old_mvp_backtest.use_adxr},
			'apo': {'old': old_mvp_backtest.use_apo},
			'bop': {'old': old_mvp_backtest.use_bop},
			'cmo': {'old': old_mvp_backtest.use_cmo},
			'dx': {'old': old_mvp_backtest.use_dx},
			'macdext': {'old': old_mvp_backtest.use_macdext},
			'macdfix': {'old': old_mvp_backtest.use_macdfix},
			'minus_di': {'old': old_mvp_backtest.use_minus_di},
			'minus_dm': {'old': old_mvp_backtest.use_minus_dm},
			'plus_di': {'old': old_mvp_backtest.use_plus_di},
			'plus_dm': {'old': old_mvp_backtest.use_plus_dm},
			'ppo': {'old': old_mvp_backtest.use_ppo},
			'roc': {'old': old_mvp_backtest.use_roc},
			'rocp': {'old': old_mvp_backtest.use_rocp},
			'rocr': {'old': old_mvp_backtest.use_rocr},
			'rocr100': {'old': old_mvp_backtest.use_rocr100},
			'stochf': {'old': old_mvp_backtest.use_stochf},
			'stochrsi': {'old': old_mvp_backtest.use_stochrsi},
			'trix': {'old': old_mvp_backtest.use_trix},
			'ultosc': {'old': old_mvp_backtest.use_ultosc},
			'ht_trendline': {'old': old_mvp_backtest.use_ht_trendline},
			'kama': {'old': old_mvp_backtest.use_kama},
			'ma': {'old': old_mvp_backtest.use_ma},
			'mama': {'old': old_mvp_backtest.use_mama},
			'mavp': {'old': old_mvp_backtest.use_mavp},
			'midpoint': {'old': old_mvp_backtest.use_midpoint},
			'midprice': {'old': old_mvp_backtest.use_midprice},
			'psar': {'old': old_mvp_backtest.use_sar},
			'sarext': {'old': old_mvp_backtest.use_sarext},
			't3': {'old': old_mvp_backtest.use_t3},
			'trima': {'old': old_mvp_backtest.use_trima},
			'wma': {'old': old_mvp_backtest.use_wma},
		}

		for ta in TAs:
			old_fn = TAs[ta]['old']
			new_fn = self.TA_templates.templates[ta]['function']
			self.assertTrue(np.array_equal(old_fn(self.ohlc_data), new_fn(self.ohlc_data)))

	def test_technical_analysis(self):
		templates = self.TA_templates.templates
		df = {}
		for ta in templates:
			df[ta] = templates[ta]['function'](self.ohlc_data)
		df = pd.DataFrame(df)
		ref_df = pd.read_csv(ORACLE_DIR / 'technical_analysis' / 'analysis_result.csv')
		self.assertTrue(np.array_equal(df.columns, ref_df.columns))
		for col in df.columns:
			self.assertTrue(np.array_equal(df[col], ref_df[col]))

	def test_technical_indicators(self):
		options = self.TA.options
		df = {}
		for ta in options:
			df[ta] = getattr(self.TA, ta)(self.ohlc_data)
		df = pd.DataFrame(df)
		ref_df = pd.read_csv(ORACLE_DIR / 'technical_analysis' / 'indicators_result.csv')
		self.assertTrue(np.array_equal(df.columns, ref_df.columns))
		for col in df.columns:
			self.assertTrue(np.all(np.isclose(df[col], ref_df[col], rtol=0, atol=1e-10, equal_nan=True)))

	def test_technical_indicators_with_args(self):
		def correct_value(params, limits):
			for param in params:
				for limit in limits:
					if param == limit['variable']:
						match limit['operation']:
							case '>':
								if params[param] <= limit['value']:
									params[param] = limit['value'] + 0.01

							case '<':
								if params[param] >= limit['value']:
									params[param] = limit['value'] - 0.01

							case '>=':
								if params[param] < limit['value']:
									params[param] = limit['value']

							case '<=':
								if params[param] > limit['value']:
									params[param] = limit['value']

							case '==':
								if params[param] != limit['value']:
									params[param] = limit['value']

							case '!=':
								if params[param] == limit['value']:
									params[param] = limit['value'] - 0.01

			return params

		options = self.TA.options
		df = {}
		for ta in options:
			base_params = {**options[ta]['params']}
			limits = options[ta]['limits']

			minus_5 = {param: base_params[param] - 5 for param in base_params}
			minus_5 = correct_value(minus_5, limits)
			df[f'{ta}-5'] = getattr(self.TA, ta)(self.ohlc_data, **minus_5)

			plus_5 = {param: base_params[param] + 5 for param in base_params}
			plus_5 = correct_value(plus_5, limits)
			df[f'{ta}+5'] = getattr(self.TA, ta)(self.ohlc_data, **plus_5)
		df = pd.DataFrame(df)
		ref_df = pd.read_csv(ORACLE_DIR / 'technical_analysis' / 'indicators_result_with_args.csv')
		self.assertTrue(np.array_equal(df.columns, ref_df.columns))
		for col in df.columns:
			self.assertTrue(np.all(np.isclose(df[col], ref_df[col], rtol=0, atol=1e-10, equal_nan=True)))
