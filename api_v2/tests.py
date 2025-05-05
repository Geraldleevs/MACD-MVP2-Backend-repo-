import inspect
import json
from datetime import datetime
from functools import partial

import numpy as np
import pandas as pd
import pytz
from django.conf import settings
from django.test import SimpleTestCase

from core import old_mvp_backtest
from core.calculations import (
	arrange_expressions,
	calculate_amount,
	combine_ohlc,
	evaluate_expression,
	evaluate_expressions,
	evaluate_math_func,
	evaluate_values,
	validate_indicator,
	validate_indicators,
	validate_strategy,
)
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


class TestCalculation(SimpleTestCase):
	@classmethod
	def setUpClass(cls):
		df = pd.read_csv(ORACLE_DIR / 'BTCUSDT.csv')
		df = df.iloc[:, 1:5]
		df.columns = ['Open', 'High', 'Low', 'Close']
		cls.ohlc_data = df
		cls.TA = TechnicalAnalysis()
		cls.TA_templates = TechnicalAnalysisTemplate(cls.TA)

	def test_combine_ohlc_2(self):
		interval = 2
		df = combine_ohlc(self.ohlc_data, interval)
		for i in range(0, len(df)):
			first_index = i * interval
			last_index = min((i + 1) * interval - 1, len(self.ohlc_data) - 1)
			range_last = last_index + 1

			self.assertEqual(self.ohlc_data['Open'][first_index], df['Open'][i])
			self.assertEqual(max(self.ohlc_data['High'][first_index:range_last]), df['High'][i])
			self.assertEqual(min(self.ohlc_data['Low'][first_index:range_last]), df['Low'][i])
			self.assertEqual(self.ohlc_data['Close'][last_index], df['Close'][i])

	def test_combine_ohlc_4(self):
		interval = 4
		df = combine_ohlc(self.ohlc_data, interval)
		for i in range(0, len(df)):
			first_index = i * interval
			last_index = min((i + 1) * interval - 1, len(self.ohlc_data) - 1)
			range_last = last_index + 1

			self.assertEqual(self.ohlc_data['Open'][first_index], df['Open'][i])
			self.assertEqual(max(self.ohlc_data['High'][first_index:range_last]), df['High'][i])
			self.assertEqual(min(self.ohlc_data['Low'][first_index:range_last]), df['Low'][i])
			self.assertEqual(self.ohlc_data['Close'][last_index], df['Close'][i])

	def test_combine_ohlc_6(self):
		interval = 6
		df = combine_ohlc(self.ohlc_data, interval)
		for i in range(0, len(df)):
			first_index = i * interval
			last_index = min((i + 1) * interval - 1, len(self.ohlc_data) - 1)
			range_last = last_index + 1

			self.assertEqual(self.ohlc_data['Open'][first_index], df['Open'][i])
			self.assertEqual(max(self.ohlc_data['High'][first_index:range_last]), df['High'][i])
			self.assertEqual(min(self.ohlc_data['Low'][first_index:range_last]), df['Low'][i])
			self.assertEqual(self.ohlc_data['Close'][last_index], df['Close'][i])

	def test_combine_ohlc_12(self):
		interval = 12
		df = combine_ohlc(self.ohlc_data, interval)
		for i in range(0, len(df)):
			first_index = i * interval
			last_index = min((i + 1) * interval - 1, len(self.ohlc_data) - 1)
			range_last = last_index + 1

			self.assertEqual(self.ohlc_data['Open'][first_index], df['Open'][i])
			self.assertEqual(max(self.ohlc_data['High'][first_index:range_last]), df['High'][i])
			self.assertEqual(min(self.ohlc_data['Low'][first_index:range_last]), df['Low'][i])
			self.assertEqual(self.ohlc_data['Close'][last_index], df['Close'][i])

	def test_combine_ohlc_24(self):
		interval = 24
		df = combine_ohlc(self.ohlc_data, interval)
		for i in range(0, len(df)):
			first_index = i * interval
			last_index = min((i + 1) * interval - 1, len(self.ohlc_data) - 1)
			range_last = last_index + 1

			self.assertEqual(self.ohlc_data['Open'][first_index], df['Open'][i])
			self.assertEqual(max(self.ohlc_data['High'][first_index:range_last]), df['High'][i])
			self.assertEqual(min(self.ohlc_data['Low'][first_index:range_last]), df['Low'][i])
			self.assertEqual(self.ohlc_data['Close'][last_index], df['Close'][i])

	def test_math_max(self):
		self.assertEqual(evaluate_math_func('max', 5), 5)
		self.assertEqual(evaluate_math_func('max', 5.0), 5.0)
		self.assertEqual(evaluate_math_func('max', [1, 2, 3, 4, 5]), 5)
		self.assertEqual(evaluate_math_func('max', np.array([1, 2, 3, 4, 5])), 5)

	def test_math_min(self):
		self.assertEqual(evaluate_math_func('min', 5), 5)
		self.assertEqual(evaluate_math_func('min', 5.0), 5.0)
		self.assertEqual(evaluate_math_func('min', [1, 2, 3, 4, 5]), 1)
		self.assertEqual(evaluate_math_func('min', np.array([1, 2, 3, 4, 5])), 1)

	def test_math_abs(self):
		self.assertEqual(evaluate_math_func('abs', 5), 5)
		self.assertEqual(evaluate_math_func('abs', 5.0), 5.0)
		self.assertEqual(evaluate_math_func('abs', -5), 5)
		self.assertEqual(evaluate_math_func('abs', -5.0), 5.0)

		self.assertTrue(
			np.array_equal(
				evaluate_math_func('abs', [1, 2, 3, 4, 5]),
				np.array([1, 2, 3, 4, 5]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_math_func('abs', [1, -2, 3, -4, 5]),
				np.array([1, 2, 3, 4, 5]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_math_func('abs', np.array([1, 2, 3, 4, 5])),
				np.array([1, 2, 3, 4, 5]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_math_func('abs', np.array([1, -2, 3, -4, 5])),
				np.array([1, 2, 3, 4, 5]),
			)
		)

	def test_arithmetic(self):
		self.assertEqual(evaluate_expression(1, '+', 2), 3)
		self.assertEqual(evaluate_expression(1, '-', 2), -1)
		self.assertEqual(evaluate_expression(1, '*', 2), 2)
		self.assertEqual(evaluate_expression(1, '/', 2), 0.5)
		self.assertEqual(evaluate_expression(2, '^', 2), 4)
		self.assertEqual(evaluate_expression(4, '**', 2), 16)

		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '+', 5),
				np.array([6, 7, 8, 9, 10]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '-', 5),
				np.array([-4, -3, -2, -1, 0]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '*', 5),
				np.array([5, 10, 15, 20, 25]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '/', 5),
				np.array([0.2, 0.4, 0.6, 0.8, 1]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '^', 5),
				np.array([1, 32, 243, 1024, 3125]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '**', 5),
				np.array([1, 32, 243, 1024, 3125]),
			)
		)

		self.assertTrue(
			np.array_equal(
				evaluate_expression(5, '+', np.array([1, 2, 3, 4, 5])),
				np.array([6, 7, 8, 9, 10]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(5, '-', np.array([1, 2, 3, 4, 5])),
				np.array([4, 3, 2, 1, 0]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(5, '*', np.array([1, 2, 3, 4, 5])),
				np.array([5, 10, 15, 20, 25]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(5, '/', np.array([1, 2, 3, 4, 5])),
				np.array([5, 2.5, 5 / 3, 1.25, 1]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(5, '^', np.array([1, 2, 3, 4, 5])),
				np.array([5, 25, 125, 625, 3125]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(5, '**', np.array([1, 2, 3, 4, 5])),
				np.array([5, 25, 125, 625, 3125]),
			)
		)

		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '+', np.array([1, 2, 3, 4, 5])),
				np.array([2, 4, 6, 8, 10]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '-', np.array([1, 2, 3, 4, 5])),
				np.array([0, 0, 0, 0, 0]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '*', np.array([1, 2, 3, 4, 5])),
				np.array([1, 4, 9, 16, 25]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '/', np.array([1, 2, 3, 4, 5])),
				np.array([1, 1, 1, 1, 1]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '^', np.array([1, 2, 3, 4, 5])),
				np.array([1, 4, 27, 256, 3125]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '**', np.array([1, 2, 3, 4, 5])),
				np.array([1, 4, 27, 256, 3125]),
			)
		)

	def test_logical(self):
		self.assertEqual(evaluate_expression(5, '=', 5), True)
		self.assertEqual(evaluate_expression(5, '==', 5), True)
		self.assertEqual(evaluate_expression(5, '!=', 5), False)

		self.assertEqual(evaluate_expression(5, '>', 5), False)
		self.assertEqual(evaluate_expression(5, '>', 4), True)

		self.assertEqual(evaluate_expression(5, '>=', 5), True)
		self.assertEqual(evaluate_expression(5, '>=', 6), False)

		self.assertEqual(evaluate_expression(5, '<', 5), False)
		self.assertEqual(evaluate_expression(5, '<', 6), True)

		self.assertEqual(evaluate_expression(5, '<=', 5), True)
		self.assertEqual(evaluate_expression(5, '<=', 4), False)

		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '=', 1),
				np.array([1, 0, 0, 0, 0]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '==', 1),
				np.array([1, 0, 0, 0, 0]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '!=', 1),
				np.array([0, 1, 1, 1, 1]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '>', 2),
				np.array([0, 0, 1, 1, 1]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '>=', 2),
				np.array([0, 1, 1, 1, 1]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '<', 2),
				np.array([1, 0, 0, 0, 0]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(np.array([1, 2, 3, 4, 5]), '<=', 2),
				np.array([1, 1, 0, 0, 0]),
			)
		)

		self.assertTrue(
			np.array_equal(
				evaluate_expression(
					np.array([1, 2, 3, 4, 5]),
					'=',
					np.array([1, 2, 3, 4, 5]),
				),
				np.array([1, 1, 1, 1, 1]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(
					np.array([1, 2, 3, 4, 5]),
					'==',
					np.array([5, 4, 3, 2, 1]),
				),
				np.array([0, 0, 1, 0, 0]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(
					np.array([1, 2, 3, 4, 5]),
					'!=',
					np.array([5, 4, 3, 2, 1]),
				),
				np.array([1, 1, 0, 1, 1]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(
					np.array([1, 2, 3, 4, 5]),
					'>=',
					np.array([1, 2, 3, 4, 5]),
				),
				np.array([1, 1, 1, 1, 1]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(
					np.array([1, 2, 3, 4, 5]),
					'>',
					np.array([0, 2, 4, 6, 8]),
				),
				np.array([1, 0, 0, 0, 0]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(
					np.array([1, 2, 3, 4, 5]),
					'<',
					np.array([0, 2, 4, 6, 8]),
				),
				np.array([0, 0, 1, 1, 1]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(
					np.array([1, 2, 3, 4, 5]),
					'<=',
					np.array([0, 2, 4, 6, 8]),
				),
				np.array([0, 1, 1, 1, 1]),
			)
		)

		self.assertTrue(
			np.array_equal(
				evaluate_expression(
					np.array([1, 1, 0, 1, 1]),
					'and',
					np.array([0, 0, 1, 1, 1]),
				),
				np.array([0, 0, 0, 1, 1]),
			)
		)
		self.assertTrue(
			np.array_equal(
				evaluate_expression(
					np.array([1, 1, 0, 1, 1]),
					'or',
					np.array([0, 0, 1, 1, 1]),
				),
				np.array([1, 1, 1, 1, 1]),
			)
		)


class TestValidation(SimpleTestCase):
	def test_validate_indicator_valid(self):
		indicator = {'indicator_name': 'macd', 'params': {'fastperiod': 2}}
		validate_indicator(indicator)

	def test_validate_indicator_list_valid(self):
		indicators = [
			{'indicator_name': 'macd', 'params': {'fastperiod': 2}},
			{'indicator_name': 'willr', 'params': {'timeperiod': 2}},
			{'indicator_name': 'wma'},
		]
		validate_indicators(indicators)

	def test_validate_indicator_invalid(self):
		try:
			indicator = 'macd'
			validate_indicator(indicator)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid indicator settings!')

		try:
			indicator = {'params': {'timeperiod': 2}}
			validate_indicator(indicator)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Missing "indicator_name" in indicator settings!')

		try:
			indicator = {'indicator_name': 'invalid'}
			validate_indicator(indicator)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid indicator name "invalid"!')

		try:
			indicator = {'indicator_name': 'willr', 'params': {'invalid': 1}}
			validate_indicator(indicator)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid indicator parameters "invalid" in "willr"!')

		try:
			indicator = {'indicator_name': 'willr', 'params': {'timeperiod': 'abc'}}
			validate_indicator(indicator)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid parameter values "timeperiod: abc" for "willr"!')

		try:
			indicator = {'indicator_name': 'willr', 'params': {'timeperiod': 1}}
			validate_indicator(indicator)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid parameter value "timeperiod: 1.0"! (Expected >= 2.0)')

	def test_validate_strategy_valid(self):
		strategy = [
			{'type': 'template', 'value': 'macd', 'timeframe': '1h'},
			{'type': 'operator', 'value': 'or'},
			{'type': 'indicator', 'value': {'indicator_name': 'willr', 'params': {'timeperiod': 2}}, 'timeframe': '1h'},
			{'type': 'operator', 'value': '<'},
			{'type': 'operator', 'value': '('},
			{'type': 'value', 'value': '70'},
			{'type': 'operator', 'value': '+'},
			{
				'type': 'math_func',
				'value': {
					'type': 'max',
					'value': [
						{'type': 'ohlc', 'value': 'Close'},
						{'type': 'operator', 'value': '+'},
						{'type': 'value', 'value': '30'},
					],
				},
			},
			{'type': 'operator', 'value': ')'},
		]
		validate_strategy(strategy)

		strategy = [
			{'type': 'template', 'value': 'macd', 'timeframe': '1h'},
			{'type': 'operator', 'value': 'or'},
			{'type': 'indicator', 'value': {'indicator_name': 'willr', 'params': {'timeperiod': 2}}, 'timeframe': '1h'},
			{'type': 'operator', 'value': '<'},
			{'type': 'operator', 'value': '('},
			{'type': 'value', 'value': '70'},
			{'type': 'operator', 'value': '+'},
			{
				'type': 'math_func',
				'value': {
					'type': 'max',
					'value': [
						{'type': 'ohlc', 'value': 'Close'},
						{'type': 'operator', 'value': '+'},
						{'type': 'value', 'value': '30'},
					],
				},
			},
		]
		validate_strategy(strategy)

	def test_validate_strategy_invalid(self):
		strategy = {'type': 'template', 'value': 'macd'}
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid strategy settings, expected an array!')

		strategy = [5, 5]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), '"type" and "value" is missing from strategy!')

		strategy = [{'value': 'template'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), '"type" is missing from strategy!')

		strategy = [{'type': 'template'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), '"value" is missing from strategy!')

		strategy = [{'type': 'invalid', 'value': 'macd'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Unknown expression type "invalid"!')

		strategy = [{'type': 'template', 'value': 'invalid'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Unknown template "invalid"!')

		strategy = [{'type': 'template', 'value': 'macd'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Missing timeframe for template!')

		strategy = [{'type': 'template', 'value': 'macd', 'timeframe': 60}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid timeframe "60"!')

		strategy = [{'type': 'value', 'value': [60]}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid numeric value "[60]"!')

		strategy = [{'type': 'value', 'value': '60ab'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid numeric value "60ab"!')

		strategy = [{'type': 'operator', 'value': '&'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Unknown operator "&"!')

		strategy = [{'type': 'ohlc', 'value': 'invalid'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Unknown OHLC value "invalid"!')

		strategy = [{'type': 'indicator', 'value': 'invalid'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Missing timeframe for indicator settings!')

		strategy = [{'type': 'indicator', 'timeframe': 60, 'value': 'invalid'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid timeframe "60"!')

		strategy = [{'type': 'indicator', 'timeframe': '1h', 'value': 'invalid'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid indicator settings!')

		strategy = [{'type': 'indicator', 'timeframe': '1h', 'value': {}}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Missing "indicator_name" in indicator settings!')

		strategy = [{'type': 'math_func', 'value': 'max'}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid math function!')

		strategy = [{'type': 'math_func', 'value': {'value': 'max'}}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), '"type" is missing from math function!')

		strategy = [{'type': 'math_func', 'value': {'type': 'max'}}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), '"value" is missing from math function!')

		strategy = [{'type': 'math_func', 'value': {'type': 'max', 'value': 60}}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid math function, expected an array of expressions!')

		strategy = [{'type': 'math_func', 'value': {'type': 'invalid', 'value': [60]}}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Unknown math function "invalid"!')

		strategy = [{'type': 'math_func', 'value': {'type': 'max', 'value': [60]}}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), '"type" and "value" is missing from strategy!')

		strategy = [{'type': 'math_func', 'value': {'type': 'max', 'value': [{'type': 'value', 'value': 'a'}]}}]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid numeric value "a"!')

		strategy = [
			{'type': 'operator', 'value': '('},
			{'type': 'value', 'value': 60},
			{'type': 'operator', 'value': ')'},
			{'type': 'operator', 'value': ')'},
		]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid expression, extra closing parenthesis!')

		strategy = [
			{'type': 'value', 'value': 60},
			{'type': 'operator', 'value': ')'},
		]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid expression, extra closing parenthesis!')

		strategy = [
			{'type': 'value', 'value': 60},
			{'type': 'operator', 'value': '+'},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 70},
		]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid expression, continuous operators encountered!')

		strategy = [
			{'type': 'value', 'value': 60},
			{'type': 'operator', 'value': '+'},
			{'type': 'operator', 'value': '('},
			{'type': 'operator', 'value': '-'},
			{'type': 'value', 'value': 70},
		]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid expression, continuous operators encountered!')

		strategy = [
			{'type': 'value', 'value': 60},
			{'type': 'operator', 'value': '+'},
			{'type': 'operator', 'value': '('},
			{'type': 'value', 'value': 70},
			{'type': 'value', 'value': 90},
		]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid expression, continuous value/expression encountered!')

		strategy = [
			{'type': 'value', 'value': 60},
			{'type': 'operator', 'value': '+'},
			{'type': 'operator', 'value': '('},
			{'type': 'value', 'value': 70},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 70},
			{'type': 'operator', 'value': ')'},
			{'type': 'value', 'value': 90},
		]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid expression, continuous value/expression encountered!')

		strategy = [
			{'type': 'value', 'value': 60},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 90},
			{'type': 'operator', 'value': '+'},
		]
		try:
			validate_strategy(strategy)
			self.assertTrue(False)
		except ValueError as e:
			self.assertEqual(str(e), 'Invalid expression, trailing operator encountered!')


class TestEvaluation(SimpleTestCase):
	@classmethod
	def setUpClass(cls):
		df = pd.read_csv(ORACLE_DIR / 'BTCUSDT.csv')
		df = df.iloc[:, 0:6]
		df.columns = ['open_time', 'Open', 'High', 'Low', 'Close', 'Volume']
		cls.ohlc_data = df
		cls.TA = TechnicalAnalysis()
		cls.TA_templates = TechnicalAnalysisTemplate(cls.TA)
		cls.MAX_LENGTH = len(df['Open'])

	def test_evaluate_values(self):
		"""60 + Close - Open * High / Low > Macd or (Macd Template * Max(Close))"""
		strategy = [
			{'type': 'value', 'value': 60},
			{'type': 'operator', 'value': '+'},
			{'type': 'ohlc', 'value': 'close'},
			{'type': 'operator', 'value': '-'},
			{'type': 'ohlc', 'value': 'open'},
			{'type': 'operator', 'value': '*'},
			{'type': 'ohlc', 'value': 'high'},
			{'type': 'operator', 'value': '/'},
			{'type': 'ohlc', 'value': 'low'},
			{'type': 'operator', 'value': '>'},
			{'type': 'indicator', 'timeframe': '1h', 'value': {'indicator_name': 'macd', 'params': {'fastperiod': 2}}},
			{'type': 'operator', 'value': 'or'},
			{'type': 'operator', 'value': '('},
			{'type': 'template', 'timeframe': '4h', 'value': 'macd'},
			{'type': 'operator', 'value': '*'},
			{'type': 'math_func', 'value': {'type': 'max', 'value': [{'type': 'ohlc', 'value': 'close'}]}},
			{'type': 'operator', 'value': ')'},
		]
		values = evaluate_values({'1h': self.ohlc_data}, strategy, True)
		self.assertEqual(values[0]['value'], 60)
		self.assertEqual(values[1]['value'], '+')
		self.assertTrue(np.array_equal(values[2]['value'], self.ohlc_data['Close']))
		self.assertEqual(values[3]['value'], '-')
		self.assertTrue(np.array_equal(values[4]['value'], self.ohlc_data['Open']))
		self.assertEqual(values[5]['value'], '*')
		self.assertTrue(np.array_equal(values[6]['value'], self.ohlc_data['High']))
		self.assertEqual(values[7]['value'], '/')
		self.assertTrue(np.array_equal(values[8]['value'], self.ohlc_data['Low']))
		self.assertEqual(values[9]['value'], '>')
		self.assertTrue(
			np.array_equal(
				values[10]['value'],
				np.nan_to_num(self.TA.macd(self.ohlc_data, fastperiod=2)),
			)
		)
		self.assertEqual(values[11]['value'], 'or')
		self.assertEqual(values[12]['value'], '(')
		self.assertTrue(
			np.array_equal(
				values[13]['value'],
				np.where(self.TA_templates.macd(combine_ohlc(self.ohlc_data, 4)) == 1, 1, 0).repeat(4)[
					: self.MAX_LENGTH
				],
			),
		)
		self.assertEqual(values[14]['value'], '*')
		self.assertTrue(np.array_equal(values[15]['value']['value'][0]['value'], self.ohlc_data['Close']))
		self.assertEqual(values[16]['value'], ')')

		values = evaluate_values({'1h': self.ohlc_data}, strategy, False)
		self.assertEqual(values[0]['value'], 60)
		self.assertEqual(values[1]['value'], '+')
		self.assertTrue(np.array_equal(values[2]['value'], self.ohlc_data['Close']))
		self.assertEqual(values[3]['value'], '-')
		self.assertTrue(np.array_equal(values[4]['value'], self.ohlc_data['Open']))
		self.assertEqual(values[5]['value'], '*')
		self.assertTrue(np.array_equal(values[6]['value'], self.ohlc_data['High']))
		self.assertEqual(values[7]['value'], '/')
		self.assertTrue(np.array_equal(values[8]['value'], self.ohlc_data['Low']))
		self.assertEqual(values[9]['value'], '>')
		self.assertTrue(
			np.array_equal(
				values[10]['value'],
				np.nan_to_num(self.TA.macd(self.ohlc_data, fastperiod=2)),
			)
		)
		self.assertEqual(values[11]['value'], 'or')
		self.assertEqual(values[12]['value'], '(')
		self.assertTrue(
			np.array_equal(
				values[13]['value'],
				np.where(self.TA_templates.macd(combine_ohlc(self.ohlc_data, 4)) == -1, 1, 0).repeat(4)[
					: self.MAX_LENGTH
				],
			),
		)
		self.assertEqual(values[14]['value'], '*')
		self.assertTrue(np.array_equal(values[15]['value']['value'][0]['value'], self.ohlc_data['Close']))
		self.assertEqual(values[16]['value'], ')')

	def test_arrange_expressions(self):
		def merge_function(exps: list):
			return ''.join([str(exp['value']) for exp in exps])

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0+0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '-'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0-0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0*0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '/'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0/0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '^'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0^0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0**0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '>'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0>0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '>='},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0>=0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '<'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0<0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '<='},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0<=0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': 'and'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0and0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': 'or'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0or0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0+(0*0)')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0*0+0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'operator', 'value': '('},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': ')'},
			{'type': 'operator', 'value': '/'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '-'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0+(0*(0+(0*0))/0)-0+(0*0)')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '^'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0*0+(0*(0**0^0)*0)+0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '^'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0**0+(0*(0**0^0)*0)+0')

		expressions = [
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '^'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 0},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 0},
		]
		arranged = merge_function(arrange_expressions(expressions))
		self.assertEqual(arranged, '0**0*0*(0**0^0)*0+0')

	def test_evaluate_expressions_basic(self):
		expressions = [
			{'type': 'value', 'value': 50},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 70},
		]
		result = evaluate_expressions(expressions)
		self.assertEqual(result, 120)

		expressions = [
			{'type': 'value', 'value': 50},
			{'type': 'operator', 'value': '-'},
			{'type': 'value', 'value': 70},
		]
		result = evaluate_expressions(expressions)
		self.assertEqual(result, -20)

		expressions = [
			{'type': 'value', 'value': 50},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 70},
		]
		result = evaluate_expressions(expressions)
		self.assertEqual(result, 3500)

		expressions = [
			{'type': 'value', 'value': 5},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 4},
		]
		result = evaluate_expressions(expressions)
		self.assertEqual(result, 625)

		expressions = [
			{'type': 'value', 'value': 5},
			{'type': 'operator', 'value': '^'},
			{'type': 'value', 'value': 4},
		]
		result = evaluate_expressions(expressions)
		self.assertEqual(result, 625)

		expressions = [
			{'type': 'value', 'value': 5},
			{'type': 'operator', 'value': '/'},
			{'type': 'value', 'value': 4},
		]
		result = evaluate_expressions(expressions)
		self.assertEqual(result, 1.25)

		expressions = [
			{'type': 'value', 'value': 5},
			{'type': 'operator', 'value': '>'},
			{'type': 'value', 'value': 4},
		]
		result = evaluate_expressions(expressions)
		self.assertTrue(result)

		expressions = [
			{'type': 'value', 'value': 5},
			{'type': 'operator', 'value': '>='},
			{'type': 'value', 'value': 5},
		]
		result = evaluate_expressions(expressions)
		self.assertTrue(result)

		expressions = [
			{'type': 'value', 'value': 5},
			{'type': 'operator', 'value': '<'},
			{'type': 'value', 'value': 5},
		]
		result = evaluate_expressions(expressions)
		self.assertFalse(result)

		expressions = [
			{'type': 'value', 'value': 5},
			{'type': 'operator', 'value': '<='},
			{'type': 'value', 'value': 5},
		]
		result = evaluate_expressions(expressions)
		self.assertTrue(result)

		expressions = [
			{'type': 'value', 'value': 5},
			{'type': 'operator', 'value': '='},
			{'type': 'value', 'value': 5},
		]
		result = evaluate_expressions(expressions)
		self.assertTrue(result)

		expressions = [
			{'type': 'value', 'value': 5},
			{'type': 'operator', 'value': '=='},
			{'type': 'value', 'value': 5},
		]
		result = evaluate_expressions(expressions)
		self.assertTrue(result)

		expressions = [
			{'type': 'value', 'value': 5},
			{'type': 'operator', 'value': '!='},
			{'type': 'value', 'value': 5},
		]
		result = evaluate_expressions(expressions)
		self.assertFalse(result)

		expressions = [
			{'type': 'value', 'value': True},
			{'type': 'operator', 'value': 'And'},
			{'type': 'value', 'value': False},
		]
		result = evaluate_expressions(expressions)
		self.assertFalse(result)

		expressions = [
			{'type': 'value', 'value': True},
			{'type': 'operator', 'value': 'or'},
			{'type': 'value', 'value': False},
		]
		result = evaluate_expressions(expressions)
		self.assertTrue(result)

	def test_evaluate_expressions_complex(self):
		expressions = [
			{'type': 'value', 'value': 1},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 2},
			{'type': 'operator', 'value': '*'},
			{'type': 'operator', 'value': '('},
			{'type': 'value', 'value': 3},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 4},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 5},
			{'type': 'operator', 'value': ')'},
			{'type': 'operator', 'value': '/'},
			{'type': 'value', 'value': 6},
			{'type': 'operator', 'value': '-'},
			{'type': 'value', 'value': 7},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 8},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 9},
		]
		result = evaluate_expressions(expressions)
		self.assertEqual(result, 1 + (2 * (3 + (4 * 5)) / 6) - 7 + (8 * 9))

		expressions = [
			{'type': 'value', 'value': 1},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 2},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 3},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 4},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 2},
			{'type': 'operator', 'value': '^'},
			{'type': 'value', 'value': 2},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 7},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 8},
		]
		result = evaluate_expressions(expressions)
		self.assertEqual(result, 1 * 2 + (3 * (4**2**2) * 7) + 8)

		expressions = [
			{'type': 'value', 'value': 1},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 2},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 3},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 4},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 2},
			{'type': 'operator', 'value': '^'},
			{'type': 'value', 'value': 2},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 7},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 8},
		]
		result = evaluate_expressions(expressions)
		self.assertEqual(result, 1**2 + (3 * (4**2**2) * 7) + 8)

		expressions = [
			{'type': 'value', 'value': 1},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 2},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 3},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 4},
			{'type': 'operator', 'value': '**'},
			{'type': 'value', 'value': 2},
			{'type': 'operator', 'value': '^'},
			{'type': 'value', 'value': 2},
			{'type': 'operator', 'value': '*'},
			{'type': 'value', 'value': 7},
			{'type': 'operator', 'value': '+'},
			{'type': 'value', 'value': 8},
		]
		result = evaluate_expressions(expressions)
		self.assertEqual(result, 1**2 * 3 * (4**2**2) * 7 + 8)

	def test_evaluate_expressions_values(self):
		expressions = [
			{'type': 'value', 'value': 60},
			{'type': 'operator', 'value': '+'},
			{'type': 'ohlc', 'value': self.ohlc_data['Close'].to_numpy()},
			{'type': 'operator', 'value': '-'},
			{'type': 'ohlc', 'value': self.ohlc_data['Open'].to_numpy()},
			{'type': 'operator', 'value': '*'},
			{'type': 'ohlc', 'value': self.ohlc_data['High'].to_numpy()},
			{'type': 'operator', 'value': '/'},
			{'type': 'ohlc', 'value': self.ohlc_data['Low'].to_numpy()},
			{'type': 'operator', 'value': '>'},
			{'type': 'operator', 'value': '('},
			{'type': 'indicator', 'value': np.nan_to_num(self.TA.macd(self.ohlc_data, fastperiod=2))},
			{'type': 'operator', 'value': '*'},
			{
				'type': 'math_func',
				'value': {
					'type': 'max',
					'value': [
						{'type': 'ohlc', 'value': self.ohlc_data['Close'].to_numpy()},
						{'type': 'operator', 'value': '+'},
						{'type': 'value', 'value': 30},
					],
				},
			},
			{'type': 'operator', 'value': ')'},
			{'type': 'operator', 'value': 'or'},
			{
				'type': 'template',
				'value': np.where(self.TA_templates.macd(combine_ohlc(self.ohlc_data, 4)) == 1, 1, 0).repeat(4)[
					: len(self.ohlc_data['Close'])
				],
			},
		]
		result = evaluate_expressions(expressions)

		# 60 + Close - Open * High / Low > (Indicator * max(Close + 30)) or MACD
		compare_result = 60 + self.ohlc_data['Close'].to_numpy()
		tmp_compare = self.ohlc_data['Open'].to_numpy() * self.ohlc_data['High'].to_numpy()
		tmp_compare = tmp_compare / self.ohlc_data['Low'].to_numpy()
		compare_result = compare_result - tmp_compare
		tmp_compare = np.nan_to_num(self.TA.macd(self.ohlc_data, fastperiod=2))
		tmp_compare = tmp_compare * max(self.ohlc_data['Close'] + 30)
		compare_result = compare_result > tmp_compare
		tmp_compare = np.where(self.TA_templates.macd(combine_ohlc(self.ohlc_data, 4)) == 1, 1, 0).repeat(4)[
			: len(self.ohlc_data['Close'])
		]
		compare_result = compare_result | tmp_compare
		self.assertTrue(np.array_equal(result, compare_result))

	def test_evaluate_expressions_full(self):
		strategy = [
			{'type': 'value', 'value': 60},
			{'type': 'operator', 'value': '+'},
			{'type': 'ohlc', 'value': 'close'},
			{'type': 'operator', 'value': '-'},
			{'type': 'ohlc', 'value': 'open'},
			{'type': 'operator', 'value': '*'},
			{'type': 'ohlc', 'value': 'high'},
			{'type': 'operator', 'value': '/'},
			{'type': 'ohlc', 'value': 'low'},
			{'type': 'operator', 'value': '>'},
			{'type': 'operator', 'value': '('},
			{'type': 'indicator', 'timeframe': '1h', 'value': {'indicator_name': 'macd', 'params': {'fastperiod': 2}}},
			{'type': 'operator', 'value': '*'},
			{
				'type': 'math_func',
				'value': {
					'type': 'max',
					'value': [
						{'type': 'ohlc', 'value': 'close'},
						{'type': 'operator', 'value': '+'},
						{'type': 'value', 'value': 30},
					],
				},
			},
			{'type': 'operator', 'value': ')'},
			{'type': 'operator', 'value': 'or'},
			{'type': 'template', 'timeframe': '4h', 'value': 'macd'},
		]
		expressions = evaluate_values({'1h': self.ohlc_data}, strategy, True)
		result = evaluate_expressions(expressions)

		# 60 + Close - Open * High / Low > (Indicator * max(Close + 30)) or MACD
		compare_result = 60 + self.ohlc_data['Close'].to_numpy()
		tmp_compare = self.ohlc_data['Open'].to_numpy() * self.ohlc_data['High'].to_numpy()
		tmp_compare = tmp_compare / self.ohlc_data['Low'].to_numpy()
		compare_result = compare_result - tmp_compare
		tmp_compare = np.nan_to_num(self.TA.macd(self.ohlc_data, fastperiod=2))
		tmp_compare = tmp_compare * max(self.ohlc_data['Close'] + 30)
		compare_result = compare_result > tmp_compare
		tmp_compare = np.where(self.TA_templates.macd(combine_ohlc(self.ohlc_data, 4)) == 1, 1, 0).repeat(4)[
			: len(self.ohlc_data['Close'])
		]
		compare_result = compare_result | tmp_compare
		self.assertTrue(np.array_equal(result, compare_result))

	def test_calculate_amount(self):
		capital = 10000
		open_times = self.ohlc_data['open_time'].to_numpy()
		close_data = self.ohlc_data['Close'].to_numpy()
		buy_signals = np.array(([1] * 3) + ([0] * (self.MAX_LENGTH - 6)) + ([1] * 3))
		sell_signals = np.array(([0] * 10) + ([1] * 10) + ([0] * (self.MAX_LENGTH - 20)))
		unit_types = ['GBP', 'BTC']
		results, trades, holdings, units, trade_types = calculate_amount(
			capital, open_times, close_data, buy_signals, sell_signals, unit_types
		)

		self.assertEqual(results[-1], '9936.70337099946 GBP')

		self.assertListEqual(
			trades,
			[
				{
					'timestamp': 1690848000000,
					'datetime': datetime(2023, 8, 1, 0, 0, tzinfo=pytz.UTC),
					'from_amount': 10000,
					'from_token': 'GBP',
					'to_amount': np.float64(0.3468007629616785),
					'to_token': 'BTC',
				},
				{
					'timestamp': 1690992000000,
					'datetime': datetime(2023, 8, 2, 16, 0, tzinfo=pytz.UTC),
					'from_amount': np.float64(0.3468007629616785),
					'from_token': 'BTC',
					'to_amount': np.float64(10109.783249523149),
					'to_token': 'GBP',
				},
				{
					'timestamp': 1723032000000,
					'datetime': datetime(2024, 8, 7, 12, 0, tzinfo=pytz.UTC),
					'from_amount': np.float64(10109.783249523149),
					'from_token': 'GBP',
					'to_amount': np.float64(0.18022770948173436),
					'to_token': 'BTC',
				},
				{
					'timestamp': 1723060800000,
					'datetime': datetime(2024, 8, 7, 20, 0, tzinfo=pytz.UTC),
					'from_amount': np.float64(0.18022770948173436),
					'from_token': 'BTC',
					'to_amount': np.float64(9936.70337099946),
					'to_token': 'GBP',
				},
			],
		)

		self.assertEqual(holdings[-2], 0.18022770948173436)
		self.assertEqual(holdings[-1], 9936.70337099946)
		self.assertEqual(units[-2], 'BTC')
		self.assertEqual(units[-1], 'GBP')

		self.assertEqual(trade_types[0], 'buy')
		self.assertEqual(trade_types[10], 'sell')
		self.assertEqual(trade_types[-3], 'buy')
		self.assertEqual(trade_types[-1], 'sell')
		for i in range(self.MAX_LENGTH):
			if i in [0, 10, self.MAX_LENGTH - 3, self.MAX_LENGTH - 1]:
				continue
			self.assertEqual(trade_types[i], 'hold')
