import json
from functools import lru_cache

import firebase_admin.auth
import numpy as np
import pandas as pd
from django.conf import settings
from django.db.utils import OperationalError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, inline_serializer
from firebase_admin.auth import InvalidIdTokenError
from rest_framework.authentication import get_authorization_header
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BooleanField, CharField, IntegerField, ListField
from rest_framework.views import APIView

from api_v2.models import KLine
from core.technical_analysis import TechnicalAnalysis, TechnicalAnalysisTemplate

TA: TechnicalAnalysis = settings.TA
TA_TEMPLATES: TechnicalAnalysisTemplate = settings.TA_TEMPLATES


def authenticate_jwt(force_auth=False):
	def decorator(view_func):
		def wrapper(self, request: Request, *args, **kwargs):
			if force_auth is False and (settings.DEBUG is True or settings.SKIP_AUTH is True):
				return view_func(self, request, *args, **kwargs)

			uid = None
			if request.method == 'POST':
				uid = request.data.get('uid')
			else:
				uid = request.query_params.get('uid')

			try:
				if uid is None:
					raise ValueError

				jwt_token = get_authorization_header(request).decode('utf-8').split(' ')[1]
				if uid != firebase_admin.auth.verify_id_token(jwt_token)['uid']:
					raise ValueError

				return view_func(self, request, *args, **kwargs)
			except (InvalidIdTokenError, IndexError, ValueError):
				return Response({'error': 'Unauthorised'}, status=403)

		return wrapper

	return decorator


try:
	START_TIME = KLine.objects.order_by('open_time').first().open_time
	END_TIME = KLine.objects.order_by('open_time').last().open_time
	SYMBOLS = [kline['symbol'] for kline in KLine.objects.values('symbol').distinct()]
	TIMEFRAMES = [kline['timeframe'] for kline in KLine.objects.values('timeframe').distinct()]
	YEARS = [kline['year'] for kline in KLine.objects.values('year').distinct()]
	MONTHS = [kline['month'] for kline in KLine.objects.values('month').distinct()]
except OperationalError:
	print('KLine Table not Found! Have you run `python manage.py migrate`?')

BACKTEST_PARAMS = ['Open', 'High', 'Low', 'Close', 'Volume']
OPERATORS = ['>', '>=', '<', '<=', '==', '!=']


def validate_symbol_timeframe(symbol: str, timeframe: str):
	if symbol is None or symbol == '':
		return 'Missing "symbol"!'

	if timeframe is None or timeframe == '':
		return 'Missing "timeframe"!'

	if symbol not in SYMBOLS:
		return f'Invalid symbol "{symbol}"!'

	if timeframe not in TIMEFRAMES:
		return f'Invalid timeframe "{timeframe}"!'

	return None


@lru_cache(maxsize=8)
def fetch_kline(
	symbol: str,
	timeframe: str,
	year: int = None,
	month: int = None,
	start_time: int = None,
	end_time: int = None,
):
	data = KLine.objects.filter(symbol=symbol, timeframe=timeframe)

	if year is not None:
		try:
			data = data.filter(year=int(year))
		except ValueError:
			return f'Invalid year "{year}"'

	if month is not None:
		try:
			if isinstance(month, tuple):
				data = data.filter(month__in=[int(mon) for mon in month])
			else:
				data = data.filter(month=int(month))
		except ValueError:
			return f'Invalid month "{month}"'

	if start_time is not None:
		try:
			data = data.filter(open_time__gte=int(start_time))
		except ValueError:
			return f'Invalid year "{year}"'

	if end_time is not None:
		try:
			data = data.filter(open_time__lte=int(end_time))
		except ValueError:
			return f'Invalid end time "{end_time}"'

	data = [
		{
			'Open Time': row.open_time,
			'Open': row.open,
			'High': row.high,
			'Low': row.low,
			'Close': row.close,
		}
		for row in data.order_by('open_time')
	]

	return data


# Check Login Status
class CheckLoginStatus(APIView):
	@authenticate_jwt(force_auth=True)
	def get(self, request: Request):
		return Response({'login_status': 'You are logged in!'})

	@authenticate_jwt(force_auth=True)
	def post(self, request: Request):
		return Response({'login_status': 'You are logged in!'})


# Get Options, Templates, Symbols and Timeframes
class TechnicalIndicators(APIView):
	def get(self, request: Request):
		return Response({'technical_indicators': settings.TA_OPTIONS})


class BacktestTemplates(APIView):
	def get(self, request: Request):
		return Response({'backtest_templates': settings.TA_TEMPLATE_OPTIONS})


class BacktestSymbols(APIView):
	def get(self, request: Request):
		return Response({'symbols': SYMBOLS})


class BacktestTimeframes(APIView):
	def get(self, request: Request):
		return Response({'timeframes': TIMEFRAMES})


class OhlcDataTime(APIView):
	def get(self, request: Request):
		return Response({'start_time': START_TIME, 'end_time': END_TIME, 'years': YEARS})


class OhlcData(APIView):
	@extend_schema(
		responses={200},
		parameters=[
			OpenApiParameter('uid', OpenApiTypes.STR),
			OpenApiParameter('symbol', OpenApiTypes.STR),
			OpenApiParameter('timeframe', OpenApiTypes.STR),
			OpenApiParameter('start_time', OpenApiTypes.INT),
			OpenApiParameter('end_time', OpenApiTypes.INT),
		],
		examples=[
			OpenApiExample(
				'Example',
				{
					'ohlc_data': [
						{
							'Open Time': 1672531200000,
							'Open': 13678.76,
							'High': 13744.3,
							'Low': 13637.79,
							'Close': 13738.2,
						},
						{
							'Open Time': 1672617600000,
							'Open': 13740.69,
							'High': 13929.09,
							'Low': 13684.06,
							'Close': 13818.17,
						},
					]
				},
			)
		],
	)
	@authenticate_jwt()
	def get(self, request: Request):
		symbol = request.query_params.get('symbol', '').strip().upper()
		timeframe = request.query_params.get('timeframe', '').strip().lower()
		start_time = request.query_params.get('start_time')
		end_time = request.query_params.get('end_time')

		invalid_symbol = validate_symbol_timeframe(symbol, timeframe)
		if invalid_symbol is not None:
			return Response({'error': invalid_symbol}, 400)

		try:
			if start_time is not None:
				start_time = int(start_time)
		except ValueError:
			return Response({'error': 'Invalid start time'}, 400)

		try:
			if end_time is not None:
				end_time = int(end_time)
		except ValueError:
			return Response({'error': 'Invalid end time'}, 400)

		data = fetch_kline(symbol=symbol, timeframe=timeframe, start_time=start_time, end_time=end_time)
		return Response({'ohlc_data': data})


# Technical Analysis
def validate_indicator_settings(indicator_settings: list):
	if not isinstance(indicator_settings, list):
		return 'Invalid indicator settings, expected a list of indicator settings!'

	for indicator in indicator_settings:
		try:
			indicator_name = indicator['indicator_name']
		except KeyError:
			return 'Invalid indicator settings, expected "indicator_name"!'

		if indicator_name not in TA.options:
			return f'Invalid indicator name "{indicator_name}"!'

		for param_name in indicator.get('params', []):
			if param_name not in TA.options[indicator_name]['params']:
				return f'Invalid indicator parameters "{param_name}" in "{indicator_name}"!'

			value = indicator['params'][param_name]
			try:
				value = float(value)
			except ValueError:
				return f'Invalid parameter values "{param_name}: {value}" for "{indicator_name}"'

			if len(TA.options[indicator_name]['limits']) == 0:
				continue

			for limit in TA.options[indicator_name]['limits']:
				if param_name != limit['variable']:
					continue

				limit_value = limit['value']
				match limit['operation']:
					case '>':
						if value <= limit_value:
							return f'Invalid parameter value "{param_name}: {value}" (Expected > {limit_value})'

					case '<':
						if value >= limit_value:
							return f'Invalid parameter value "{param_name}: {value}" (Expected < {limit_value})'

					case '>=':
						if value < limit_value:
							return f'Invalid parameter value "{param_name}: {value}" (Expected >= {limit_value})'

					case '<=':
						if value > limit_value:
							return f'Invalid parameter value "{param_name}: {value}" (Expected <= {limit_value})'

					case '==':
						if value != limit_value:
							return f'Invalid parameter value "{param_name}: {value}" (Expected == {limit_value})'

					case '!=':
						if value == limit_value:
							return f'Invalid parameter value "{param_name}: {value}" (Expected != {limit_value})'

	return None


def validate_backtest_strategy(strategies: list, name: str):
	for strategy in strategies:
		if isinstance(strategy, str):
			if strategy.lower() not in ['and', 'or']:
				return f'Unknown strategy {strategy}'
			continue

		if 'template' in strategy:
			template = strategy['template']
			if strategy['template'] not in TA_TEMPLATES.templates:
				return f'Invalid template "{template}" in "{name}"!'
			if 'param_1' in strategy and 'param_2' in strategy and 'op' in strategy:
				return f'Please specify either "template" or params/indicators but not both ("{name}")!'
			continue

		if 'param_1' not in strategy:
			return f'"param_1" is missing in "{name}"!'
		if 'param_2' not in strategy:
			return f'"param_2" is missing in "{name}"!'
		if 'op' not in strategy:
			return f'"op" is missing in "{name}"!'

		param_1 = strategy['param_1']
		param_2 = strategy['param_2']
		op = strategy['op']

		if op not in OPERATORS:
			return f'Invalid operator "{op}" in "{name}", expected {"|".join(OPERATORS)}!'

		if isinstance(param_1, str):
			if param_1 not in BACKTEST_PARAMS:
				return f'Invalid param "{param_1}" in "{name}"!'
		elif isinstance(param_1, dict):
			invalid_param = validate_indicator_settings([param_1])
			if invalid_param is not None:
				return invalid_param.replace('!', f'({name})!')
		else:
			return f'Invalid "param_1", expected indicator settings object or {"|".join(BACKTEST_PARAMS)}'

		if isinstance(param_2, str):
			if param_2 not in BACKTEST_PARAMS:
				return f'Invalid param "{param_2}" in "{name}"!'
		elif isinstance(param_2, dict):
			invalid_param = validate_indicator_settings([param_2])
			if invalid_param is not None:
				return invalid_param.replace('!', f'({name})!')
		else:
			return f'Invalid "param_2", expected indicator settings object or {"|".join(BACKTEST_PARAMS)}'

	return None


def validate_list_settings(settings: str, name: str):
	if settings is None:
		return f'Missing "{name}"!'

	if isinstance(settings, str):
		try:
			settings = settings.removeprefix('"').removesuffix('"')
			settings = json.loads(settings)
			return settings
		except Exception:
			return f'Invalid {name}, expected a list!'

	if not isinstance(settings, list):
		return f'Invalid {name}, expected a list!'

	return settings


def get_indicator_full_name(settings: str | dict):
	if isinstance(settings, dict):
		indicator_name = settings['indicator_name']
		params = settings.get('params', {})
		full_name = indicator_name + '_'.join([f'{key}_{value}' for key, value in sorted(params.items())])
		return full_name
	else:
		return settings


class RunIndicators(APIView):
	@extend_schema(description='Get details of the endpoint')
	def get(self, request: Request):
		return Response(
			{
				'example_request': {
					'return_ohlc': 'false # Setting false will return empty array for "ohlc_data"',
					'symbol': 'BTCGBP',
					'timeframe': '1d',
					'year': 2024,
					'month': 1,
					'start_time': 1672531200000,
					'end_time': 1722531200000,
					'indicator_settings': [{'indicator_name': 'macd', 'params': {'fastperiod': 2}}],
				},
				'example_response': {
					'ohlc_data': [
						{
							'Open Time': 1672531200000,
							'Open': 13678.76,
							'High': 13678.76,
							'Low': 13650.0,
							'Close': 13669.49,
						}
					],
					'indicators': {
						'macd': [-45.0943, -34.7605, 4.2966, -8.0860, -22.8330, -30.8021, -56.4162, -43.2721]
					},
				},
			}
		)

	@extend_schema(
		request=inline_serializer(
			name='Indicator Form',
			fields={
				'uid': CharField(default=''),
				'symbol': CharField(default='BTCGBP'),
				'timeframe': CharField(default='1d'),
				'return_ohlc': BooleanField(default=False),
				'start_time': IntegerField(default=1672531200000),
				'end_time': IntegerField(default=1704063600000),
				'year': IntegerField(default=2023),
				'month': ListField(default=[1, 2, 3]),
				'indicator_settings': ListField(default=[{'indicator_name': 'macd', 'params': {'fastperiod': 2}}]),
			},
		),
	)
	@authenticate_jwt()
	def post(self, request: Request):
		symbol = request.data.get('symbol', '').strip().upper()
		timeframe = request.data.get('timeframe', '').strip().lower()
		indicator_settings = request.data.get('indicator_settings')
		return_ohlc = request.data.get('return_ohlc', 'true') != 'false'
		start_time = request.data.get('start_time')
		end_time = request.data.get('end_time')
		year = request.data.get('year')
		month = request.data.get('month')

		if isinstance(month, list):
			month = tuple(sorted(month))

		invalid_symbol = validate_symbol_timeframe(symbol, timeframe)
		if invalid_symbol is not None:
			return Response({'error': invalid_symbol}, 400)

		indicator_settings = validate_list_settings(indicator_settings, 'indicator_settings')
		if isinstance(indicator_settings, str):
			return Response({'error': indicator_settings}, 400)

		invalid_indicator_settings = validate_indicator_settings(indicator_settings)
		if invalid_indicator_settings is not None:
			return Response({'error': invalid_indicator_settings}, 400)

		data = fetch_kline(
			symbol=symbol,
			timeframe=timeframe,
			start_time=start_time,
			end_time=end_time,
			year=year,
			month=month,
		)
		if len(data) == 0:
			return Response({'error': 'There is no OHLC data in the specified period'}, 400)

		df = pd.DataFrame(data)
		results = {}
		for indicator in indicator_settings:
			indicator_name = indicator['indicator_name']
			params = indicator.get('params', {})
			result = np.array(getattr(TA, indicator_name)(df, **params))
			result = np.nan_to_num(result)
			results[indicator_name] = result.tolist()

		return Response({'ohlc_data': data if return_ohlc is True else [], 'indicators': results})


class RunBacktest(APIView):
	@extend_schema(description='Get details of the endpoint')
	def get(self, request: Request):
		return Response(
			{
				'example_request': {
					'return_ohlc': 'false # Setting false will return empty array for "ohlc_data"',
					'symbol': 'BTCGBP',
					'timeframe': '1h',
					'year': 2024,
					'month': [1, 2],
					'start_time': 1672531200000,
					'end_time': 1722531200000,
					'buy_strategy': [
						{'template': 'macd'},
						'or',
						{
							'param_1': 'Close',
							'op': '>',
							'param_2': {'indicator_name': 'macd', 'params': {'fastperiod': 2}},
						},
						{'param_1': {'indicator_name': 'adx'}, 'op': '>', 'param_2': {'indicator_name': 'ema'}},
					],
					'sell_strategy': [
						{'template': 'macd'},
						'and',
						{
							'param_1': 'Close',
							'op': '<=',
							'param_2': {'indicator_name': 'macd', 'params': {'fastperiod': 2}},
						},
						{'param_1': {'indicator_name': 'adx'}, 'op': '<=', 'param_2': {'indicator_name': 'ema'}},
					],
					'documentation': 'Strategies are executed in sequence, not considering and/or precedence, strategies that are not join with and/or are assumed joined with and clause',
				},
				'example_response': {
					'ohlc_data': [
						{
							'Open Time': 1672531200000,
							'Open': 13678.76,
							'High': 13678.76,
							'Low': 13650.0,
							'Close': 13669.49,
						}
					],
					'buy_results': [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1],
					'sell_results': [-1, -1, -1, 0, 0, -1, -1, -1, 0, -1, -1, -1, -1],
				},
			}
		)

	def apply_backtest(
		self,
		df: pd.DataFrame,
		indicators_results: dict[str, np.ndarray],
		strategies: list,
		is_buy: bool,
	):
		is_and = True
		results = None
		template_checker = 1 if is_buy else -1

		for strategy in strategies:
			if isinstance(strategy, str):
				if strategy.lower() == 'or':
					is_and = False
				continue

			if 'template' in strategy:
				result = TA_TEMPLATES.templates[strategy['template']]['function'](df)
				result = np.where(result == template_checker, 1, 0)
			else:
				param_1 = get_indicator_full_name(strategy['param_1'])
				param_2 = get_indicator_full_name(strategy['param_1'])
				op = strategy['op']
				match op:
					case '>':
						result = indicators_results[param_1] > indicators_results[param_2]
					case '>=':
						result = indicators_results[param_1] >= indicators_results[param_2]
					case '<':
						result = indicators_results[param_1] < indicators_results[param_2]
					case '<=':
						result = indicators_results[param_1] <= indicators_results[param_2]
					case '==':
						result = indicators_results[param_1] == indicators_results[param_2]
					case '!=':
						result = indicators_results[param_1] != indicators_results[param_2]

			if results is None:
				results = result
			elif is_and is True:
				results = results & result
			else:
				results = results | result

			is_and = True

		return np.where(results == 1, template_checker, 0)

	@extend_schema(
		request=inline_serializer(
			name='Backtest Form',
			fields={
				'uid': CharField(default=''),
				'symbol': CharField(default='BTCGBP'),
				'timeframe': CharField(default='1d'),
				'return_ohlc': BooleanField(default=False),
				'start_time': IntegerField(default=1672531200000),
				'end_time': IntegerField(default=1704063600000),
				'year': IntegerField(default=2023),
				'month': ListField(default=[1, 2, 3]),
				'buy_strategy': ListField(
					default=[
						{'template': 'macd'},
						'or',
						{
							'param_1': 'Close',
							'op': '>',
							'param_2': {'indicator_name': 'macd', 'params': {'fastperiod': 2}},
						},
						{'param_1': {'indicator_name': 'adx'}, 'op': '>', 'param_2': {'indicator_name': 'ema'}},
					]
				),
				'sell_strategy': ListField(
					default=[
						{'template': 'macd'},
						'and',
						{
							'param_1': 'Close',
							'op': '<=',
							'param_2': {'indicator_name': 'macd', 'params': {'fastperiod': 2}},
						},
						{'param_1': {'indicator_name': 'adx'}, 'op': '<=', 'param_2': {'indicator_name': 'ema'}},
					]
				),
			},
		),
	)
	@authenticate_jwt()
	def post(self, request: Request):
		symbol = request.data.get('symbol', '').strip().upper()
		timeframe = request.data.get('timeframe', '').strip().lower()
		buy_strategy = request.data.get('buy_strategy')
		sell_strategy = request.data.get('sell_strategy')
		return_ohlc = request.data.get('return_ohlc', 'true') != 'false'
		start_time = request.data.get('start_time')
		end_time = request.data.get('end_time')
		year = request.data.get('year')
		month = request.data.get('month')

		if isinstance(month, list):
			month = tuple(sorted(month))

		invalid_symbol = validate_symbol_timeframe(symbol, timeframe)
		if invalid_symbol is not None:
			return Response({'error': invalid_symbol}, 400)

		buy_strategy = validate_list_settings(buy_strategy, 'buy_strategy')
		if isinstance(buy_strategy, str):
			return Response({'error': buy_strategy}, 400)

		sell_strategy = validate_list_settings(sell_strategy, 'sell_strategy')
		if isinstance(sell_strategy, str):
			return Response({'error': sell_strategy}, 400)

		invalid_strategy = validate_backtest_strategy(buy_strategy, 'buy_strategy')
		if invalid_strategy is not None:
			return Response({'error': invalid_strategy}, 400)

		invalid_strategy = validate_backtest_strategy(sell_strategy, 'sell_strategy')
		if invalid_strategy is not None:
			return Response({'error': invalid_strategy}, 400)

		data = fetch_kline(
			symbol=symbol,
			timeframe=timeframe,
			start_time=start_time,
			end_time=end_time,
			year=year,
			month=month,
		)
		if len(data) == 0:
			return Response({'error': 'There is no OHLC data in the specified period'}, 400)

		df = pd.DataFrame(data)
		indicators_results = {
			'Open': df['Open'].to_numpy(),
			'High': df['High'].to_numpy(),
			'Low': df['Low'].to_numpy(),
			'Close': df['Close'].to_numpy(),
		}

		for strategy in [*buy_strategy, *sell_strategy]:
			if 'template' in strategy or isinstance(strategy, str):
				continue

			for param in [strategy['param_1'], strategy['param_2']]:
				if isinstance(param, dict):
					indicator_name = param['indicator_name']
					params = param.get('params', {})
					full_name = indicator_name + '_'.join([f'{key}_{value}' for key, value in sorted(params.items())])

					if full_name not in indicators_results:
						indicators_results[full_name] = np.array(getattr(TA, indicator_name)(df, **params))

		buy_results = self.apply_backtest(df, indicators_results, buy_strategy, is_buy=True).tolist()
		sell_results = self.apply_backtest(df, indicators_results, sell_strategy, is_buy=False).tolist()

		return Response(
			{
				'ohlc_data': data if return_ohlc is True else [],
				'buy_results': buy_results,
				'sell_results': sell_results,
			}
		)
