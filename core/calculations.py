import math
from copy import deepcopy
from datetime import datetime

import numpy as np
import pandas as pd
import pytz

from core.technical_analysis import TechnicalAnalysis, TechnicalAnalysisTemplate

TA = TechnicalAnalysis()
TA_TEMPLATES = TechnicalAnalysisTemplate()

INTERVAL_MAP = {
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
	open_time = df['Open Time'].to_numpy()
	open = df['Open'].to_numpy()
	high = df['High'].to_numpy()
	low = df['Low'].to_numpy()
	close = df['Close'].to_numpy()
	volume = df['Volume'].to_numpy()

	diff = merge_interval - len(open) % merge_interval
	if diff != merge_interval:
		open_time = np.insert(open_time, len(open_time), [open_time[-1]] * diff)
		open = np.insert(open, len(open), [open[-1]] * diff)
		high = np.insert(high, len(high), [high[-1]] * diff)
		low = np.insert(low, len(low), [low[-1]] * diff)
		close = np.insert(close, len(close), [close[-1]] * diff)
		volume = np.insert(volume, len(volume), [0] * diff)

	open_time = open_time[::merge_interval]
	open = open[::merge_interval]
	high = high.reshape([-1, merge_interval]).max(axis=1)
	low = low.reshape([-1, merge_interval]).min(axis=1)
	close = close[merge_interval - 1 :: merge_interval]
	volume = volume.reshape([-1, merge_interval]).sum(axis=1)

	return pd.DataFrame(
		{
			'Open Time': open_time,
			'Open': open,
			'High': high,
			'Low': low,
			'Close': close,
			'Volume': volume,
		}
	)


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
			pass

		if len(TA.options[indicator_name]['limits']) == 0:
			continue

		for limit in TA.options[indicator_name]['limits']:
			if param_name != limit['variable']:
				continue

			if limit['operation'] != 'IN':
				if isinstance(value, str):
					raise ValueError(f'Invalid parameter values "{param_name}: {value}" for "{indicator_name}"!')

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

				case 'IN':
					if value not in limit_value:
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
	buy_signals: np.ndarray[np.int8],
	sell_signals: np.ndarray[np.int8],
	unit_types: tuple[str, str],
	stop_loss: float = None,
	take_profit: float = None,
	trade_limit: int = 300,
) -> list[float]:
	base_amount = capital
	sec_amount = 0

	try:
		len(buy_signals)
	except TypeError:
		buy_signals = np.array([buy_signals])

	try:
		len(sell_signals)
	except TypeError:
		sell_signals = np.array([sell_signals])

	if len(buy_signals) == 1 and len(sell_signals) == 1:
		buy_signals = buy_signals.repeat(len(close_data))
		sell_signals = sell_signals.repeat(len(close_data))
	elif len(buy_signals) == 1:
		buy_signals = buy_signals.repeat(len(close_data))
	elif len(sell_signals) == 1:
		sell_signals = sell_signals.repeat(len(close_data))

	holdings = [0] * min(len(buy_signals), len(sell_signals))
	units = [unit_types[0]] * len(holdings)
	trade_types = ['hold'] * len(holdings)
	results = [''] * len(holdings)
	trades = []

	bought = False
	last_price = None
	stopped = False
	stopped_by = None
	trade_count = 0

	for i in range(len(holdings)):
		if stopped:
			holdings[i] = holdings[i - 1] if i > 0 else capital
			units[i] = units[i - 1] if i > 0 else unit_types[0]
		elif np.isnan(close_data[i]) or close_data[i] is None:
			holdings[i] = holdings[i - 1] if i > 0 else capital
			units[i] = units[i - 1] if i > 0 else unit_types[0]
		elif bought and stop_loss is not None and sec_amount * close_data[i] <= stop_loss:
			old_amount = sec_amount
			base_amount = sec_amount * close_data[i]
			sec_amount = 0
			holdings[i] = base_amount

			trade_types[i] = 'sell'
			trade_count += 1
			bought = False
			stopped = True
			stopped_by = 'loss'

			trade_time = datetime.fromtimestamp(open_times[i] / 1000).astimezone(pytz.UTC)
			trades.append(
				{
					'timestamp': int(open_times[i]),
					'datetime': trade_time,
					'from_amount': float(old_amount),
					'from_token': unit_types[1],
					'to_amount': float(base_amount),
					'to_token': unit_types[0],
					'price': float(close_data[i]),
				}
			)
		elif bought and take_profit is not None and sec_amount * close_data[i] >= take_profit:
			old_amount = sec_amount
			base_amount = sec_amount * close_data[i]
			sec_amount = 0
			holdings[i] = base_amount

			trade_types[i] = 'sell'
			trade_count += 1
			bought = False
			stopped = True
			stopped_by = 'profit'

			trade_time = datetime.fromtimestamp(open_times[i] / 1000).astimezone(pytz.UTC)
			trades.append(
				{
					'timestamp': int(open_times[i]),
					'datetime': trade_time,
					'from_amount': float(old_amount),
					'from_token': unit_types[1],
					'to_amount': float(base_amount),
					'to_token': unit_types[0],
					'price': float(close_data[i]),
				}
			)
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
					'from_amount': float(old_amount),
					'from_token': unit_types[0],
					'to_amount': float(sec_amount),
					'to_token': unit_types[1],
					'price': float(close_data[i]),
				}
			)
		elif bought and sell_signals[i] != 0:
			old_amount = sec_amount
			base_amount = sec_amount * close_data[i]
			sec_amount = 0
			holdings[i] = base_amount

			trade_types[i] = 'sell'
			trade_count += 1
			bought = False

			trade_time = datetime.fromtimestamp(open_times[i] / 1000).astimezone(pytz.UTC)
			trades.append(
				{
					'timestamp': int(open_times[i]),
					'datetime': trade_time,
					'from_amount': float(old_amount),
					'from_token': unit_types[1],
					'to_amount': float(base_amount),
					'to_token': unit_types[0],
					'price': float(close_data[i]),
				}
			)
		else:
			holdings[i] = holdings[i - 1] if i > 0 else capital
			units[i] = units[i - 1] if i > 0 else unit_types[0]

		results[i] = f'{holdings[i]} {units[i]}'

		if not (np.isnan(close_data[i]) or close_data[i] is None):
			last_price = close_data[i]

		if trade_limit is not None and not stopped and trade_count >= trade_limit:
			stopped = True
			stopped_by = 'trade limit hit'

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
				'from_amount': float(sec_amount),
				'from_token': unit_types[1],
				'to_amount': float(base_amount),
				'to_token': unit_types[0],
				'price': float(last_price),
			}
		)

	return {
		'results': results,
		'trades': trades,
		'holdings': [float(holding) for holding in holdings],
		'units': units,
		'trade_types': trade_types,
		'stopped_by': stopped_by,
	}


def analyse_strategy(
	capital: float,
	close_prices: np.ndarray[np.float64],
	holdings: list[float],
	trade_types: list[str],
	trades: list,
):
	max_run_up = None
	run_ups = []  # Max Equity Run-Up: Maximum potential profit within trades
	max_drawdowns = []  # Max Equity Drawdowns: Largest peak-to-trough decline within trades
	max_drawdowns_perc = []  # Max Equity Drawdowns: Largest peak-to-trough decline within trades
	drawdowns = []
	drawdowns_perc = []
	buy_amounts = []

	profits = []
	buy_amount = None
	highest = None
	lowest = None
	total_bars = 0

	for i in range(len(trade_types)):
		if trade_types[i] == 'buy':
			buy_amount = holdings[i - 1] if i > 0 else capital
			highest = close_prices[i]
			lowest = close_prices[i]
		elif trade_types[i] == 'sell':
			total_bars += 1
			buy_amounts.append(buy_amount)
			this_profit = holdings[i] - buy_amount
			profits.append(this_profit)
			buy_amount = None

			run_ups.append(max_run_up)
			max_run_up = None
			max_drawdowns.append(float(np.min(drawdowns)) if len(drawdowns) > 0 else None)
			drawdowns = []
			max_drawdowns_perc.append(float(np.min(drawdowns_perc)) if len(drawdowns_perc) > 0 else None)
			drawdowns_perc = []
		elif buy_amount is not None:
			total_bars += 1
			amount_if_traded = holdings[i] * close_prices[i]
			profit_if_traded = amount_if_traded - buy_amount
			max_run_up = float(max(max_run_up if max_run_up is not None else -math.inf, profit_if_traded))
			if max_run_up < 0:
				max_run_up = None

			if close_prices[i] >= highest:
				if highest != lowest:
					drawdowns.append(lowest - highest)
					drawdowns_perc.append((lowest - highest) / highest)
				highest = close_prices[i]
				lowest = close_prices[i]
			else:
				lowest = min(lowest, close_prices[i])

	# Open P&L: Profit/Loss of remaining open trades
	open_profit = buy_amount * close_prices[-1] if buy_amount is not None else 0

	max_drawdown = None
	max_drawdown_perc = None
	valid_drawdowns = [drawdown for drawdown in max_drawdowns if drawdown is not None]
	valid_drawdowns_perc = [drawdown for drawdown in max_drawdowns_perc if drawdown is not None]
	if len(valid_drawdowns) > 0:
		max_drawdown = float(np.min(valid_drawdowns))
		max_drawdown_perc = float(np.min(valid_drawdowns_perc))

	max_run_up = None
	valid_run_ups = [run_up for run_up in run_ups if run_up is not None]
	if len(valid_run_ups) > 0:
		max_run_up = float(max(valid_run_ups))

	total_trades = len(profits)
	winning_trades = [profit for profit in profits if profit >= 0]
	losing_trades = [profit for profit in profits if profit < 0]
	winning_count = len(winning_trades)
	losing_count = len(losing_trades)
	total_closed_trades = len(profits)

	if total_closed_trades == 0:
		total_profit = 0
		profit_percent = None
		percent_profitable = None
		average_profit = None
		average_winning_trade = None
		average_losing_trade = None
		ratio_average_win_loss = None
		largest_winning_trade = None
		largest_losing_trade = None
		largest_winning_trade_percent = None
		largest_losing_trade_percent = None
	else:
		total_profit = float(np.sum(np.array(profits)))
		profit_percent = np.array(profits) / np.array(buy_amounts)
		percent_profitable = winning_count / total_closed_trades
		average_profit = float(np.average(profits))
		average_winning_trade = float(np.average(winning_trades)) if len(winning_trades) > 0 else None
		average_losing_trade = float(np.average(losing_trades)) if len(losing_trades) > 0 else None
		if average_winning_trade is None:
			ratio_average_win_loss = 0
		elif average_losing_trade is None:
			ratio_average_win_loss = None
		else:
			ratio_average_win_loss = average_winning_trade / average_losing_trade
		largest_winning_trade = float(max(winning_trades)) if len(winning_trades) > 0 else None
		largest_losing_trade = float(min(losing_trades)) if len(losing_trades) > 0 else None
		largest_winning_trade_percent = float(max(profit_percent)) if len(winning_trades) > 0 else None
		largest_losing_trade_percent = float(min(profit_percent)) if len(losing_trades) > 0 else None
		profit_percent = float(np.average(profit_percent))

	trade_reports = []
	cum_profit = 0
	for i in range(0, len(trades), 2):
		profit = float(profits[int(i / 2)])
		cum_profit += profit

		# i: Buy; i+1: Sell; Trade[0]: First buy
		trade_reports.append(
			{
				'buy_time': trades[i]['datetime'],
				'buy_timestamp': trades[i]['timestamp'],
				'sell_time': trades[i + 1]['datetime'],
				'sell_timestamp': trades[i + 1]['timestamp'],
				'profit': profit,
				'profit_percent': profit / trades[i]['from_amount'],
				'cumulative_profit': cum_profit,
				'cumulative_profit_percentage': cum_profit / trades[0]['from_amount'],
				'run_up': run_ups[int(i / 2)],
				'drawdown': max_drawdowns[int(i / 2)],
				'drawdown_percentage': max_drawdowns_perc[int(i / 2)],
				'starting_amount': trades[i]['from_amount'],
				'starting_price': trades[i]['price'],
				'final_amount': trades[i + 1]['to_amount'],
				'final_price': trades[i + 1]['price'],
			}
		)

	return {
		# Performance
		'open_profit': open_profit,
		'total_profit': total_profit,
		'max_equity_run_up': max_run_up,
		'max_drawdown': max_drawdown,
		'max_drawdown_percentage': max_drawdown_perc,
		# Trade analysis
		'total_trades': total_trades,
		'winning_count': winning_count,
		'losing_count': losing_count,
		'profit_percent': profit_percent,
		'percent_profitable': percent_profitable,
		'average_profit': average_profit,
		'average_winning_trade': average_winning_trade,
		'average_losing_trade': average_losing_trade,
		'ratio_average_win_loss': ratio_average_win_loss,
		'largest_winning_trade': largest_winning_trade,
		'largest_losing_trade': largest_losing_trade,
		'largest_winning_trade_percent': largest_winning_trade_percent,
		'largest_losing_trade_percent': largest_losing_trade_percent,
		'total_bars': total_bars,
		'trade_reports': trade_reports,
	}
