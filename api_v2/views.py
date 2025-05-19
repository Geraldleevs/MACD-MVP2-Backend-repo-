from functools import lru_cache

import firebase_admin.auth
import numpy as np
import pandas as pd
from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, inline_serializer
from firebase_admin.auth import InvalidIdTokenError
from google.cloud.firestore_v1.collection import CollectionReference
from google.cloud.firestore_v1.document import DocumentReference
from rest_framework.authentication import get_authorization_header
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BooleanField, CharField, FloatField, IntegerField, ListField
from rest_framework.views import APIView

from api_v2.models import KLine
from core.calculations import (
	analyse_strategy,
	calculate_amount,
	combine_ohlc,
	evaluate_expressions,
	evaluate_values,
	validate_indicators,
	validate_strategy,
)
from core.technical_analysis import TechnicalAnalysis, TechnicalAnalysisTemplate

TA: TechnicalAnalysis = settings.TA
TA_TEMPLATES: TechnicalAnalysisTemplate = settings.TA_TEMPLATES
DEFAULT_TIMEFRAME = '1h'


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
	PAIRS: dict[str, dict[str, int]] = {}
	cursor = connection.cursor()
	cursor.execute("""
		SELECT
			MIN(symbol),
			MIN(timeframe),
			MIN(from_token),
			MIN(to_token),
			MIN(open_time),
			MAX(open_time)
		FROM api_v2_kline
		GROUP BY symbol, timeframe;
	""")
	for symbol, timeframe, from_token, to_token, start_time, end_time in cursor.fetchall():
		if symbol not in PAIRS:
			PAIRS[symbol] = {'FROM_TOKEN': from_token, 'TO_TOKEN': to_token}
		PAIRS[symbol][timeframe] = {'START_TIME': start_time, 'END_TIME': end_time}
except OperationalError:
	print('KLine Table not Found! Have you run `python manage.py migrate`?')
finally:
	cursor.close()


def validate_symbol_timeframe(
	symbol: str,
	timeframe: str,
	start_time: int = None,
	end_time: int = None,
	fetch_only=False,
):
	if symbol is None or symbol == '':
		raise ValueError('Missing "symbol"!')

	if timeframe is None or timeframe == '':
		raise ValueError('Missing "timeframe"!')

	if symbol not in PAIRS:
		raise ValueError(f'Invalid symbol "{symbol}"!')

	if fetch_only:
		if timeframe not in PAIRS[symbol]:
			raise ValueError(f'Invalid timeframe "{timeframe}"!')
	elif timeframe not in settings.INTERVAL_MAP:
		raise ValueError(f'Invalid timeframe "{timeframe}"!')

	try:
		if start_time is not None:
			start_time = int(start_time)
	except ValueError:
		raise ValueError(f'Invalid start time "{start_time}"!')

	if start_time is not None and start_time < PAIRS[symbol][DEFAULT_TIMEFRAME]['START_TIME']:
		raise ValueError(
			f'Invalid start time "{start_time}"! (Expected >= {PAIRS[symbol][DEFAULT_TIMEFRAME]["START_TIME"]})'
		)

	try:
		if end_time is not None:
			end_time = int(end_time)
	except ValueError:
		raise ValueError(f'Invalid end time "{end_time}"!')

	if end_time is not None and end_time > PAIRS[symbol][DEFAULT_TIMEFRAME]['END_TIME'] + 1000 * 60 * 60 * 12:
		raise ValueError(f'Invalid end time "{end_time}"! (Expected <= {PAIRS[symbol][DEFAULT_TIMEFRAME]["END_TIME"]})')


@lru_cache(maxsize=8)
def fetch_kline(symbol: str, timeframe: str, start_time: int = None, end_time: int = None):
	data = KLine.objects.filter(symbol=symbol, timeframe=timeframe)

	if start_time is not None:
		try:
			data = data.filter(open_time__gte=int(start_time))
		except ValueError:
			raise ValueError(f'Invalid start time "{start_time}"')

	if end_time is not None:
		try:
			data = data.filter(open_time__lte=int(end_time))
		except ValueError:
			raise ValueError(f'Invalid end time "{end_time}"')

	data = [
		{
			'Open Time': row.open_time,
			'Open': row.open,
			'High': row.high,
			'Low': row.low,
			'Close': row.close,
			'Volume': row.volume,
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


# Get Options, Templates, Symbols and OHLC Data
class TechnicalIndicators(APIView):
	def get(self, request: Request):
		return Response({'technical_indicators': settings.TA_OPTIONS})


class BacktestTemplates(APIView):
	def get(self, request: Request):
		return Response({'backtest_templates': settings.TA_TEMPLATE_OPTIONS})


class BacktestSymbols(APIView):
	def get(self, request: Request):
		return Response(
			{
				'trading_pairs': {
					pair: {
						'FROM_TOKEN': PAIRS[pair]['FROM_TOKEN'],
						'TO_TOKEN': PAIRS[pair]['TO_TOKEN'],
						DEFAULT_TIMEFRAME: PAIRS[pair][DEFAULT_TIMEFRAME],
					}
					for pair in PAIRS
				},
				'timeframes': settings.INTERVAL_MAP.keys(),
			}
		)


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

		try:
			validate_symbol_timeframe(symbol, timeframe, start_time, end_time)
			data = fetch_kline(symbol=symbol, timeframe=DEFAULT_TIMEFRAME, start_time=start_time, end_time=end_time)
			if timeframe == DEFAULT_TIMEFRAME:
				return Response({'ohlc_data': data})

			df = pd.DataFrame(data)
			df = combine_ohlc(df, int(settings.INTERVAL_MAP[timeframe] / settings.INTERVAL_MAP[DEFAULT_TIMEFRAME]))
			df = df.replace(np.nan, None)
			data = df.to_dict('records')
			return Response({'ohlc_data': data})
		except ValueError as e:
			return Response({'error': str(e)}, 400)


# Technical Analysis
class RunIndicators(APIView):
	@extend_schema(description='Get details of the endpoint')
	def get(self, request: Request):
		return Response(
			{
				'example_request': {
					'uid': '',
					'symbol': 'BTCGBP',
					'timeframe': '1d',
					'return_ohlc': False,
					'start_time': 1672531200000,
					'end_time': 1703980800000,
					'indicator_settings': [{'indicator_name': 'macd', 'params': {'fastperiod': 2, 'source': 'Open'}}],
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
				'end_time': IntegerField(default=1703980800000),
				'indicator_settings': ListField(default=[{'indicator_name': 'macd', 'params': {'fastperiod': 2}}]),
			},
		),
	)
	@authenticate_jwt()
	def post(self, request: Request):
		symbol = request.data.get('symbol', '').strip().upper()
		timeframe = request.data.get('timeframe', '').strip().lower()
		indicator_settings = request.data.get('indicator_settings')
		return_ohlc = request.data.get('return_ohlc', 'true')
		return_ohlc = return_ohlc != 'false' and return_ohlc is not False
		start_time = request.data.get('start_time')
		end_time = request.data.get('end_time')

		try:
			validate_symbol_timeframe(symbol, timeframe, start_time, end_time)
			validate_indicators(indicator_settings)
			data = fetch_kline(
				symbol=symbol,
				timeframe=DEFAULT_TIMEFRAME,
				start_time=start_time,
				end_time=end_time,
			)
		except ValueError as e:
			return Response({'error': str(e)}, 400)

		if len(data) == 0:
			return Response({'error': 'There is no OHLC data in the specified period'}, 400)

		expressions = [
			{'type': 'indicator', 'timeframe': timeframe, 'name': setting['indicator_name'], 'value': setting}
			for setting in indicator_settings
		]

		df = pd.DataFrame(data)
		values = evaluate_values({DEFAULT_TIMEFRAME: df}, expressions, True, DEFAULT_TIMEFRAME)
		results = {value['name']: value['value'] for value in values}

		return Response({'ohlc_data': data if return_ohlc is True else [], 'indicators': results})


class RunBacktest(APIView):
	@extend_schema(description='Get details of the endpoint')
	def get(self, request: Request):
		return Response(
			{
				'example_request': {
					'uid': '',
					'symbol': 'BTCGBP',
					'return_ohlc': False,
					'start_time': 1672531200000,
					'end_time': 1704063600000,
					'capital_amount': 10000,
					'stop_loss': 9900,
					'take_profit': 10100,
					'buy_strategy': [
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
						{
							'type': 'indicator',
							'timeframe': '1h',
							'value': {'indicator_name': 'macd', 'params': {'fastperiod': 2, 'source': 'Open'}},
						},
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
					],
					'sell_strategy': [
						{'type': 'value', 'value': 60},
						{'type': 'operator', 'value': '+'},
						{'type': 'ohlc', 'value': 'close'},
						{'type': 'operator', 'value': '-'},
						{'type': 'ohlc', 'value': 'open'},
						{'type': 'operator', 'value': '*'},
						{'type': 'ohlc', 'value': 'high'},
						{'type': 'operator', 'value': '/'},
						{'type': 'ohlc', 'value': 'low'},
						{'type': 'operator', 'value': '<'},
						{'type': 'operator', 'value': '('},
						{
							'type': 'indicator',
							'timeframe': '1h',
							'value': {'indicator_name': 'macd', 'params': {'fastperiod': 2}},
						},
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
						{'type': 'operator', 'value': 'and'},
						{'type': 'template', 'timeframe': '4h', 'value': 'macd'},
					],
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
					'backtest_id': '8Wk8CjDbatrKmjlHM9nd',
					'date': '2025-04-20T19:00:00Z',
					'symbol': 'BTCGBP',
					'start_time': 1672531200000,
					'end_time': 1704063600000,
					'capital': 10000,
					'final_amount': '47818.72952006868 GBP',
					'profit': 37818.72952006868,
					'trade_events': [
						{
							'timestamp': 1592679600000,
							'datetime': '2020-06-20T19:00:00Z',
							'from_amount': 10000,
							'from_token': 'GBP',
							'to_amount': 1.3287871097020063,
							'to_token': 'BTC',
						},
						{
							'timestamp': 1704063600000,
							'datetime': '2023-12-31T23:00:00Z',
							'from_amount': 1.3287871097020063,
							'from_token': 'BTC',
							'to_amount': 47818.72952006868,
							'to_token': 'GBP',
						},
					],
					'buy_count': 1,
					'sell_count': 1,
					'buy_strategy': [
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
						{
							'type': 'indicator',
							'timeframe': '1h',
							'value': {'indicator_name': 'macd', 'params': {'fastperiod': 2, 'source': 'Open'}},
						},
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
						{'type': 'operator', 'value': 'and'},
						{'type': 'template', 'timeframe': '4h', 'value': 'macd'},
					],
					'sell_strategy': [
						{'type': 'value', 'value': 60},
						{'type': 'operator', 'value': '+'},
						{'type': 'ohlc', 'value': 'close'},
						{'type': 'operator', 'value': '-'},
						{'type': 'ohlc', 'value': 'open'},
						{'type': 'operator', 'value': '*'},
						{'type': 'ohlc', 'value': 'high'},
						{'type': 'operator', 'value': '/'},
						{'type': 'ohlc', 'value': 'low'},
						{'type': 'operator', 'value': '<'},
						{'type': 'operator', 'value': '('},
						{
							'type': 'indicator',
							'timeframe': '1h',
							'value': {'indicator_name': 'macd', 'params': {'fastperiod': 2}},
						},
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
						{'type': 'operator', 'value': 'and'},
						{'type': 'template', 'timeframe': '4h', 'value': 'macd'},
					],
					'stopped_by': None,
					'performance_report': {
						'open_profit': 0,
						'total_profit': -186.85826,
						'max_equity_run_up': 302.059996,
						'max_drawdown': -0.002595,
						'total_trades': 6,
						'winning_count': 1,
						'losing_count': 2,
						'profit_percent': -0.006192,
						'percent_profitable': 0.3333,
						'average_profit': -62.28608,
						'average_winning_trade': 109.7832,
						'average_losing_trade': -148.32075,
						'ratio_average_win_loss': -0.7401745,
						'largest_winning_trade': 109.7832,
						'largest_losing_trade': -170.9276,
						'largest_winning_trade_percent': 0.010978,
						'largest_losing_trade_percent': -0.01712003,
						'total_bars': 20,
					},
				},
			}
		)

	@extend_schema(
		request=inline_serializer(
			name='Backtest Form',
			fields={
				'uid': CharField(default=''),
				'symbol': CharField(default='BTCGBP'),
				'return_ohlc': BooleanField(default=False),
				'start_time': IntegerField(default=1672531200000),
				'end_time': IntegerField(default=1704063600000),
				'capital_amount': FloatField(default=10000),
				'take_profit': FloatField(default=10100),
				'stop_loss': FloatField(default=9900),
				'buy_strategy': ListField(
					default=[
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
						{
							'type': 'indicator',
							'timeframe': '1h',
							'value': {'indicator_name': 'macd', 'params': {'fastperiod': 2, 'source': 'Open'}},
						},
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
						{'type': 'operator', 'value': 'and'},
						{'type': 'template', 'timeframe': '4h', 'value': 'macd'},
					]
				),
				'sell_strategy': ListField(
					default=[
						{'type': 'value', 'value': 60},
						{'type': 'operator', 'value': '+'},
						{'type': 'ohlc', 'value': 'close'},
						{'type': 'operator', 'value': '-'},
						{'type': 'ohlc', 'value': 'open'},
						{'type': 'operator', 'value': '*'},
						{'type': 'ohlc', 'value': 'high'},
						{'type': 'operator', 'value': '/'},
						{'type': 'ohlc', 'value': 'low'},
						{'type': 'operator', 'value': '<'},
						{'type': 'operator', 'value': '('},
						{
							'type': 'indicator',
							'timeframe': '1h',
							'value': {'indicator_name': 'macd', 'params': {'fastperiod': 2}},
						},
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
						{'type': 'operator', 'value': 'and'},
						{'type': 'template', 'timeframe': '4h', 'value': 'macd'},
					]
				),
			},
		),
	)
	@authenticate_jwt()
	def post(self, request: Request):
		uid = request.data.get('uid')
		symbol = request.data.get('symbol', '').strip().upper()
		buy_strategy = request.data.get('buy_strategy')
		sell_strategy = request.data.get('sell_strategy')
		return_ohlc = request.data.get('return_ohlc', 'true')
		return_ohlc = return_ohlc != 'false' and return_ohlc is not False
		start_time = request.data.get('start_time')
		end_time = request.data.get('end_time')
		capital_amount = request.data.get('capital_amount')
		take_profit = request.data.get('take_profit')
		stop_loss = request.data.get('stop_loss')
		backtest_date = timezone.now()

		if uid is None or uid == '':
			user_exists = False
		else:
			collection: CollectionReference = settings.FIREBASE.collection('User')
			user_doc: DocumentReference = collection.document(uid)
			user_exists = user_doc.get().exists

		try:
			if capital_amount is None:
				capital_amount = 10000
			else:
				capital_amount = float(capital_amount)
		except ValueError:
			return Response({'error': f'Invalid capital amount "{capital_amount}"!'}, 400)

		if capital_amount <= 0:
			return Response({'error': f'Invalid capital amount {capital_amount}! (Expected > 0)'}, 400)

		if capital_amount > 1e7:
			return Response({'error': 'Capital amount too big! (Expected < 1,000,000)'}, 400)

		if take_profit is not None:
			try:
				take_profit = float(take_profit)
			except ValueError:
				return Response({'error': f'Invalid take profit amount {take_profit}!'}, 400)
			if take_profit <= capital_amount:
				return Response(
					{'error': f'Invalid take profit amount {take_profit}! (Expected > {capital_amount})'}, 400
				)

		if stop_loss is not None:
			try:
				stop_loss = float(stop_loss)
			except ValueError:
				return Response({'error': f'Invalid stop loss amount {stop_loss}!'}, 400)
			if stop_loss >= capital_amount:
				return Response({'error': f'Invalid stop loss amount {stop_loss}! (Expected < {capital_amount})'}, 400)

		try:
			validate_symbol_timeframe(symbol, DEFAULT_TIMEFRAME)
			validate_strategy(buy_strategy)
			validate_strategy(sell_strategy)
			data = fetch_kline(
				symbol=symbol,
				timeframe=DEFAULT_TIMEFRAME,
				start_time=start_time,
				end_time=end_time,
			)
		except ValueError as e:
			return Response({'error': str(e)}, 400)

		if len(data) == 0:
			return Response({'error': 'There is no OHLC data in the specified period'}, 400)

		df = pd.DataFrame(data)
		expressions = evaluate_values({DEFAULT_TIMEFRAME: df}, buy_strategy, True, DEFAULT_TIMEFRAME)
		buy_results = evaluate_expressions(expressions)
		expressions = evaluate_values({DEFAULT_TIMEFRAME: df}, sell_strategy, False, DEFAULT_TIMEFRAME)
		sell_results = evaluate_expressions(expressions)

		results = calculate_amount(
			capital=capital_amount,
			open_times=df['Open Time'].to_numpy(),
			close_data=df['Close'].to_numpy(),
			buy_signals=buy_results,
			sell_signals=sell_results,
			unit_types=[PAIRS[symbol]['TO_TOKEN'], PAIRS[symbol]['FROM_TOKEN']],
			stop_loss=stop_loss,
			take_profit=take_profit,
		)

		trade_results = results['results']
		trade_events = results['trades']
		holdings = results['holdings']
		trade_types = results['trade_types']
		stopped_by = results['stopped_by']

		trade_counts = np.array(trade_types)
		buy_count = int((trade_counts == 'buy').sum())
		sell_count = int((trade_counts == 'sell').sum())

		data = {
			'date': backtest_date,
			'symbol': symbol,
			'start_time': start_time,
			'end_time': end_time,
			'capital': capital_amount,
			'final_amount': trade_results[-1],
			'profit': holdings[-1] - capital_amount,
			'trade_events': trade_events,
			'buy_count': buy_count,
			'sell_count': sell_count,
			'buy_strategy': buy_strategy,
			'sell_strategy': sell_strategy,
			'stopped_by': stopped_by,
			'performance_report': analyse_strategy(capital_amount, df['Close'].to_numpy(), holdings, trade_types),
		}

		if user_exists:
			subcollection: CollectionReference = user_doc.collection('backtest_history')
			doc_ref: DocumentReference = subcollection.document()
			doc_ref.set(data)

		data['ohlc_data'] = data if return_ohlc is True else []
		data['backtest_id'] = doc_ref.id if user_exists else None

		return Response(data)
