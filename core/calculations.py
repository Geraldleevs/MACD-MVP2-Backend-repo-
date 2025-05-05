from copy import deepcopy
from datetime import datetime

import numpy as np
import pandas as pd
import pytz

from core.technical_analysis import TechnicalAnalysis, TechnicalAnalysisTemplate

TA = TechnicalAnalysis()
TA_TEMPLATES = TechnicalAnalysisTemplate()

INTERVAL_MAP = {
	'1min': 1,
	'5min': 5,
	'15min': 15,
	'30min': 30,
	'1h': 60,
	'2h': 120,
	'4h': 240,
	'6h': 360,
	'12h': 720,
	'1d': 1440,
}
BACKTEST_PARAMS = ['Open', 'High', 'Low', 'Close', 'Volume']
OPERATORS = ['>', '>=', '<', '<=', '==', '!=', '=', '+', '-', '*', '/', '^', 'and', 'or', '(', ')']
MATH_FUNCS = ['max', 'min', 'abs']
TIMEFRAMES = [60, 120, 240, 360, 720, 1440]


def combine_ohlc(df: pd.DataFrame, merge_interval: int):
	open = df['Open'].to_numpy()
	high = df['High'].to_numpy()
	low = df['Low'].to_numpy()
	close = df['Close'].to_numpy()

	diff = merge_interval - len(open) % merge_interval
	if diff != merge_interval:
		open = np.insert(open, len(open), [open[-1]] * diff)
		high = np.insert(high, len(high), [high[-1]] * diff)
		low = np.insert(low, len(low), [low[-1]] * diff)
		close = np.insert(close, len(close), [close[-1]] * diff)

	open = open[::merge_interval]
	high = high.reshape([-1, merge_interval]).max(axis=1)
	low = low.reshape([-1, merge_interval]).min(axis=1)
	close = close[merge_interval - 1 :: merge_interval]

	return pd.DataFrame({'Open': open, 'High': high, 'Low': low, 'Close': close})


def validate_indicator(indicator: dict):
	if not isinstance(indicator, dict):
		raise ValueError('Invalid indicator settings!')

	try:
		indicator_name = indicator['indicator_name']
	except KeyError:
		raise ValueError('Missing "indicator_name" in indicator settings!')

	if indicator_name not in TA.options:
		raise ValueError(f'Invalid indicator name "{indicator_name}"!')

	for param_name in indicator.get('params', []):
		if param_name not in TA.options[indicator_name]['params']:
			raise ValueError(f'Invalid indicator parameters "{param_name}" in "{indicator_name}"!')

		value = indicator['params'][param_name]
		try:
			value = float(value)
		except ValueError:
			raise ValueError(f'Invalid parameter values "{param_name}: {value}" for "{indicator_name}"!')

		if len(TA.options[indicator_name]['limits']) == 0:
			continue

		for limit in TA.options[indicator_name]['limits']:
			if param_name != limit['variable']:
				continue

			limit_value = limit['value']
			is_invalid = False
			match limit['operation']:
				case '>':
					if value <= limit_value:
						is_invalid = True

				case '<':
					if value >= limit_value:
						is_invalid = True

				case '>=':
					if value < limit_value:
						is_invalid = True

				case '<=':
					if value > limit_value:
						is_invalid = True

				case '==':
					if value != limit_value:
						is_invalid = True

				case '!=':
					if value == limit_value:
						is_invalid = True

			if is_invalid:
				raise ValueError(
					f'Invalid parameter value "{param_name}: {value}"! (Expected {limit["operation"]} {limit_value})'
				)


def validate_indicators(indicators: list):
	if not isinstance(indicators, list):
		indicators = [indicators]
	for indicator in indicators:
		validate_indicator(indicator)


def validate_strategy(strategy: list):
	if not isinstance(strategy, list):
		raise ValueError('Invalid strategy settings, expected an array!')

	for exp in strategy:
		if not isinstance(exp, dict):
			raise ValueError('"type" and "value" is missing from strategy!')

		if 'type' not in exp:
			raise ValueError('"type" is missing from strategy!')

		if 'value' not in exp:
			raise ValueError('"value" is missing from strategy!')

		match exp['type']:
			case 'operator':
				if exp['value'].lower() not in OPERATORS:
					raise ValueError(f'Unknown operator "{exp["value"]}"!')

			case 'value':
				try:
					if not (isinstance(exp['value'], int) or isinstance(exp['value'], float)):
						exp['value'] = float(exp['value'])
				except (ValueError, TypeError):
					raise ValueError(f'Invalid numeric value "{exp["value"]}"!')

			case 'indicator':
				if 'timeframe' not in exp:
					raise ValueError('Missing timeframe for indicator settings!')

				if exp['timeframe'] not in INTERVAL_MAP:
					raise ValueError(f'Invalid timeframe "{exp["timeframe"]}"!')

				validate_indicator(exp['value'])

			case 'template':
				if exp['value'] not in TA_TEMPLATES.templates:
					raise ValueError(f'Unknown template "{exp["value"]}"!')

				if 'timeframe' not in exp:
					raise ValueError('Missing timeframe for template!')

				if exp['timeframe'] not in INTERVAL_MAP:
					raise ValueError(f'Invalid timeframe "{exp["timeframe"]}"!')

			case 'math_func':
				if not isinstance(exp['value'], dict):
					raise ValueError('Invalid math function!')

				if 'type' not in exp['value']:
					raise ValueError('"type" is missing from math function!')

				if 'value' not in exp['value']:
					raise ValueError('"value" is missing from math function!')

				if not isinstance(exp['value']['value'], list):
					raise ValueError('Invalid math function, expected an array of expressions!')

				if exp['value']['type'].lower() not in MATH_FUNCS:
					raise ValueError(f'Unknown math function "{exp["value"]["type"]}"!')

				validate_strategy(exp['value']['value'])

			case 'ohlc':
				if exp['value'].title() not in BACKTEST_PARAMS:
					raise ValueError(f'Unknown OHLC value "{exp["value"]}"!')

			case _:
				raise ValueError(f'Unknown expression type "{exp["type"]}"!')

	bracket = 0
	prev_is_op = True
	for exp in strategy:
		if exp['type'] == 'operator':
			if exp['value'] != '(' and prev_is_op is True:
				raise ValueError('Invalid expression, continuous operators encountered!')

			if exp['value'] == '(':
				prev_is_op = True
				bracket += 1
			elif exp['value'] == ')':
				prev_is_op = False
				if bracket < 1:
					raise ValueError('Invalid expression, extra closing parenthesis!')
				bracket -= 1
			else:
				prev_is_op = True

		else:
			if prev_is_op is False:
				raise ValueError('Invalid expression, continuous value/expression encountered!')
			prev_is_op = False

	if prev_is_op is True:
		raise ValueError('Invalid expression, trailing operator encountered!')


def evaluate_values(df: dict[int, pd.DataFrame], strategy: list, is_buy: bool, default_timeframe='1h', nested=False):
	if nested is False:
		values = deepcopy(strategy)
	else:
		values = strategy

	template_checker = 1 if is_buy else -1
	if isinstance(df, dict):
		data = df
	elif isinstance(df, pd.DataFrame):
		data = {default_timeframe: df}

	max_length = len(data[default_timeframe]['Close'])
	for exp in values:
		if exp['type'] == 'indicator':
			indicator = exp['value']
			indicator_name = indicator['indicator_name']
			params = indicator.get('params', {})
			timeframe = exp['timeframe']

			if timeframe not in data:
				data[timeframe] = combine_ohlc(data[default_timeframe], int(INTERVAL_MAP[timeframe] / TIMEFRAMES[0]))

			result = np.array(getattr(TA, indicator_name)(data[timeframe], **params))
			result = np.nan_to_num(result)

			if timeframe != TIMEFRAMES[0]:
				result = result.repeat(int(INTERVAL_MAP[timeframe] / TIMEFRAMES[0]))
				result = result[:max_length]

			exp['value'] = result

		elif exp['type'] == 'template':
			timeframe = exp['timeframe']
			if timeframe not in data:
				data[timeframe] = combine_ohlc(data[default_timeframe], int(INTERVAL_MAP[timeframe] / TIMEFRAMES[0]))

			result = TA_TEMPLATES.templates[exp['value']]['function'](data[timeframe])
			result = np.where(result == template_checker, 1, 0)

			if timeframe != TIMEFRAMES[0]:
				result = result.repeat(int(INTERVAL_MAP[timeframe] / TIMEFRAMES[0]))
				result = result[:max_length]

			exp['value'] = result

		elif exp['type'] == 'ohlc':
			exp['value'] = data[default_timeframe][exp['value'].title()].to_numpy()

		elif exp['type'] == 'math_func':
			evaluate_values(data, exp['value']['value'], is_buy, default_timeframe, True)

	return values


def evaluate_expression(value_1: np.ndarray | float | int, op: str, value_2: np.ndarray | float | int):
	match op.lower():
		case '+':
			return value_1 + value_2

		case '-':
			return value_1 - value_2

		case '*':
			return value_1 * value_2

		case '/':
			return value_1 / value_2

		case '^' | '**':
			return value_1**value_2

		case '=' | '==':
			return value_1 == value_2

		case '!=':
			return value_1 != value_2

		case '>':
			return value_1 > value_2

		case '>=':
			return value_1 >= value_2

		case '<':
			return value_1 < value_2

		case '<=':
			return value_1 <= value_2

		case 'and':
			if isinstance(value_1, bool) and isinstance(value_2, bool):
				return value_1 and value_2

			if not isinstance(value_1, np.ndarray):
				value_1 = np.ndarray(value_1)
			if not isinstance(value_2, np.ndarray):
				value_2 = np.ndarray(value_2)
			return value_1 & value_2

		case 'or':
			if isinstance(value_1, bool) and isinstance(value_2, bool):
				return value_1 or value_2

			if not isinstance(value_1, np.ndarray):
				value_1 = np.ndarray(value_1)
			if not isinstance(value_2, np.ndarray):
				value_2 = np.ndarray(value_2)
			return value_1 | value_2


def evaluate_math_func(func: str, value: np.ndarray | float | int):
	match func:
		case 'max':
			if isinstance(value, np.ndarray) or isinstance(value, list):
				return max(value)
			return value

		case 'min':
			if isinstance(value, np.ndarray) or isinstance(value, list):
				return min(value)
			return value

		case 'abs':
			if isinstance(value, list):
				value = np.array(value)
			return abs(value)


def arrange_expressions(expressions: list):
	open_bracket = {'type': 'operator', 'value': '('}
	close_bracket = {'type': 'operator', 'value': ')'}
	arranged_expressions = []
	op_stack = []
	extra_brackets = []
	bracket = 0
	for exp in expressions:
		if exp['type'] == 'operator':
			if exp['value'] == '(':
				bracket += 1
				op_stack.append('(')

			elif exp['value'] == ')':
				bracket -= 1
				op_count = 0
				while len(extra_brackets) > 0:
					if op_stack.pop() == '(':
						break
					op_count += 1
				if op_count > 1:
					op_count -= 1

				for i in range(op_count):
					extra_brackets.pop()
					arranged_expressions.append(close_bracket)

			elif exp['value'] in ['*', '/']:
				if len(op_stack) == 0:
					op_stack.append('*')
				elif op_stack[-1] == '*':
					pass
				elif op_stack[-1] == '^':
					if len(extra_brackets) > 0:
						op_stack.pop()
						extra_brackets.pop()
						arranged_expressions.append(close_bracket)
					op_stack.append('*')
				elif op_stack[-1] != '(':
					op_stack.append('*')
					arranged_expressions.append(arranged_expressions[-1])
					arranged_expressions[-2] = open_bracket
					extra_brackets.append(')')
				else:
					op_stack.append('*')

			elif exp['value'] in ['^', '**']:
				if len(op_stack) == 0:
					op_stack.append('^')
				elif op_stack[-1] == '^':
					pass
				elif op_stack[-1] != '(':
					op_stack.append('^')
					arranged_expressions.append(arranged_expressions[-1])
					arranged_expressions[-2] = open_bracket
					extra_brackets.append(')')
				else:
					op_stack.append('^')

			else:
				if len(op_stack) == 0:
					op_stack.append('+')
				elif op_stack[-1] == '+':
					pass
				elif op_stack[-1] != '(':
					if len(extra_brackets) > 0:
						op_stack.pop()
						extra_brackets.pop()
						arranged_expressions.append(close_bracket)
					op_stack.append('+')
				else:
					op_stack.append('+')

		arranged_expressions.append(exp)

	while len(extra_brackets) > 0:
		extra_brackets.pop()
		arranged_expressions.append(close_bracket)

	if bracket > 0:
		arranged_expressions.extend([close_bracket] * bracket)

	return arranged_expressions


def evaluate_expressions(expressions: list):
	arranged_expressions = arrange_expressions(expressions)
	result_stack = []
	operation_stack = []
	result = None
	operation = None
	for exp in arranged_expressions:
		if exp['type'] == 'operator':
			if exp['value'] == '(':
				if result is None:
					result_stack.append(0)
					operation_stack.append('+')
				else:
					result_stack.append(result)
					operation_stack.append(operation)
				result = None
				operation = None
				continue
			elif exp['value'] == ')':
				temp_result = result_stack.pop()
				operation = operation_stack.pop()
				result = evaluate_expression(temp_result, operation, result)
				operation = None
			else:
				operation = exp['value']
		elif exp['type'] == 'math_func':
			value = evaluate_expressions(exp['value']['value'])
			value = evaluate_math_func(exp['value']['type'], value)
			result = evaluate_expression(result, operation, value)
		else:
			value = exp['value']
			if operation is None:
				result = value
			else:
				result = evaluate_expression(result, operation, value)
			operation = None

	while len(result_stack) > 0:
		if len(operation_stack) > 0:
			operation = operation_stack.pop()
		else:
			operation = '+'

		if result is None:
			result = 0

		result = evaluate_expression(result_stack.pop(), operation, result)

	return result


def calculate_amount(
	capital: float,
	open_times: np.ndarray[np.int64],
	close_data: np.ndarray[np.float64],
	buy_signals: list[np.int8],
	sell_signals: list[np.int8],
	unit_types: tuple[str, str],
) -> list[float]:
	base_amount = capital
	sec_amount = 0

	holdings = [0] * min(len(buy_signals), len(sell_signals))
	units = [unit_types[0]] * len(holdings)
	trade_types = ['hold'] * len(holdings)
	results = [''] * len(holdings)
	trades = []

	bought = False
	last_price = None

	for i in range(len(holdings)):
		if np.isnan(close_data[i]) or close_data[i] is None:
			holdings[i] = holdings[i - 1] if i > 0 else capital
			units[i] = units[i - 1] if i > 0 else unit_types[0]

		elif not bought and buy_signals[i] != 0:
			old_amount = base_amount
			sec_amount = base_amount / close_data[i]
			base_amount = 0
			holdings[i] = sec_amount
			units[i] = unit_types[1]

			trade_types[i] = 'buy'
			bought = True

			trade_time = datetime.fromtimestamp(open_times[i] / 1000).astimezone(pytz.UTC)
			trades.append(
				{
					'timestamp': int(open_times[i]),
					'datetime': trade_time,
					'from_amount': old_amount,
					'from_token': unit_types[0],
					'to_amount': sec_amount,
					'to_token': unit_types[1],
				}
			)
		elif bought and sell_signals[i] != 0:
			old_amount = sec_amount
			base_amount = sec_amount * close_data[i]
			sec_amount = 0
			holdings[i] = base_amount

			trade_types[i] = 'sell'
			bought = False

			trade_time = datetime.fromtimestamp(open_times[i] / 1000).astimezone(pytz.UTC)
			trades.append(
				{
					'timestamp': int(open_times[i]),
					'datetime': trade_time,
					'from_amount': old_amount,
					'from_token': unit_types[1],
					'to_amount': base_amount,
					'to_token': unit_types[0],
				}
			)
		else:
			holdings[i] = holdings[i - 1] if i > 0 else capital
			units[i] = units[i - 1] if i > 0 else unit_types[0]

		results[i] = f'{holdings[i]} {units[i]}'

		if not (np.isnan(close_data[i]) or close_data[i] is None):
			last_price = close_data[i]

	# Final value if still holding coins
	base_amount += sec_amount * last_price
	holdings[-1] = base_amount

	if units[-1] != unit_types[0]:
		units[-1] = unit_types[0]
		results[-1] = f'{holdings[-1]} {units[-1]}'

		trade_types[-1] = 'sell'

		trade_time = datetime.fromtimestamp(open_times[-1] / 1000).astimezone(pytz.UTC)
		trades.append(
			{
				'timestamp': int(open_times[-1]),
				'datetime': trade_time,
				'from_amount': sec_amount,
				'from_token': unit_types[1],
				'to_amount': base_amount,
				'to_token': unit_types[0],
			}
		)

	return results, trades, holdings, units, trade_types
