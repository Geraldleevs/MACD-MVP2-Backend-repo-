import asyncio
import calendar
import json
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import aiohttp
import firebase_admin.auth
import numpy as np
import pandas as pd
import requests
from aiohttp import ClientSession
from django.conf import settings
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, inline_serializer
from firebase_admin.auth import InvalidIdTokenError
from google.cloud.firestore_v1.batch import WriteBatch
from google.cloud.firestore_v1.client import Client
from google.cloud.firestore_v1.collection import CollectionReference
from google.cloud.firestore_v1.document import DocumentReference
from rest_framework.authentication import get_authorization_header
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BooleanField, CharField, FloatField, IntegerField, ListField
from rest_framework.views import APIView

from api_v2.firebase import FirebaseCandle, FirebaseOrderBook, Platform
from core.calculations import (
	analyse_strategy,
	calculate,
	calculate_amount,
	combine_ohlc,
	evaluate_expressions,
	evaluate_values,
	validate_indicators,
	validate_strategy,
)
from core.exceptions import NotEnoughTokenException
from core.technical_analysis import TechnicalAnalysis, TechnicalAnalysisTemplate
from machd.utils import clean_kraken_pair, log, log_error, log_warning

TA: TechnicalAnalysis = settings.TA
TA_TEMPLATES: TechnicalAnalysisTemplate = settings.TA_TEMPLATES
DEFAULT_TIMEFRAME: str = settings.DEFAULT_TIMEFRAME
DEFAULT_PLATFORM: str = settings.DEFAULT_PLATFORM
INTERVAL_MAP: dict[str, int] = settings.INTERVAL_MAP
DB_BATCH: WriteBatch = settings.DB_BATCH
FIREBASE: Client = settings.FIREBASE
BASE_DIR: Path = settings.BASE_DIR


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


def authenticate_scheduler_oicd():
	def decorator(view_func):
		def wrapper(self, request: Request, *args, **kwargs):
			if settings.DEBUG is True or settings.SKIP_AUTH is True:
				return view_func(self, request, *args, **kwargs)

			try:
				token = get_authorization_header(request).decode('utf-8').split(' ')

				if len(token) < 2:
					return Response({'error': 'Unauthorised'}, status=403)

				auth = requests.get(settings.GOOGLE_AUTH_URL, params={'id_token': token[1]}).json()

				if (
					'error' in auth.keys()
					or auth['iss'] != settings.GOOGLE_AUTH_EMAIL
					or auth['email'] != settings.GCLOUD_EMAIL
					or auth['aud'] != settings.SERVER_API_URL
				):
					return Response({'error': 'Unauthorised'}, status=403)

			except Exception:
				return Response({'error': 'Unauthorised'}, status=403)

			return view_func(self, request, *args, **kwargs)

		return wrapper

	return decorator


def error_logger():
	def decorator(view_func):
		def wrapper(self, request: Request, *args, **kwargs):
			try:
				return view_func(self, request, *args, **kwargs)
			except Exception:
				log_error({'query': request.query_params, 'data': request.data, 'error': traceback.format_exc()})
				raise

		return wrapper

	return decorator


def validate_symbol_timeframe(
	symbol: str,
	timeframe: str,
	start_time: int = None,
	end_time: int = None,
):
	if symbol is None or symbol == '':
		raise ValueError('Missing "symbol"!')

	if timeframe is None or timeframe == '':
		raise ValueError('Missing "timeframe"!')

	PAIRS = [pair['token_id'] for pair in FirebaseCandle().fetch_pairs()]

	if symbol not in PAIRS:
		raise ValueError(f'Invalid symbol "{symbol}"!')

	if timeframe not in settings.INTERVAL_MAP:
		raise ValueError(f'Invalid timeframe "{timeframe}"!')

	try:
		if start_time is not None:
			start_time = int(start_time)
	except ValueError:
		raise ValueError(f'Invalid start time "{start_time}"!')

	try:
		if end_time is not None:
			end_time = int(end_time)
	except ValueError:
		raise ValueError(f'Invalid end time "{end_time}"!')


@lru_cache(maxsize=8)
def fetch_kline(symbol: str, timeframe: str, start_time: int = None, end_time: int = None):
	firebase = FirebaseCandle(symbol, timeframe, DEFAULT_PLATFORM)

	if start_time is not None:
		try:
			start_time = datetime.fromtimestamp(int(start_time) / 1000)
		except ValueError:
			raise ValueError(f'Invalid start time "{start_time}"')

	if end_time is not None:
		try:
			end_time = datetime.fromtimestamp(int(end_time) / 1000)
		except ValueError:
			raise ValueError(f'Invalid end time "{end_time}"')

	data = firebase.fetch(start_time, end_time)
	return data


# Check Login Status
class CheckLoginStatus(APIView):
	@authenticate_jwt(force_auth=True)
	@error_logger()
	def get(self, request: Request):
		return Response({'login_status': 'You are logged in!'})

	@authenticate_jwt(force_auth=True)
	@error_logger()
	def post(self, request: Request):
		return Response({'login_status': 'You are logged in!'})


# Get Options, Templates, Symbols and OHLC Data
class TechnicalIndicators(APIView):
	@error_logger()
	def get(self, request: Request):
		return Response({'technical_indicators': settings.TA_OPTIONS})


class BacktestTemplates(APIView):
	@error_logger()
	def get(self, request: Request):
		return Response({'backtest_templates': settings.TA_TEMPLATE_OPTIONS})


class BacktestSymbols(APIView):
	@error_logger()
	def get(self, request: Request):
		PAIRS = {}
		for token in FirebaseCandle().fetch_pairs():
			symbol = token['token_id']
			from_token = token['from_token']
			to_token = token['to_token']

			firebase = FirebaseCandle(symbol, DEFAULT_TIMEFRAME, DEFAULT_PLATFORM)
			start_time = None
			end_time = None

			first = firebase.fetch_first()
			if len(first) > 0:
				start_time = first[0]['Open Time']
			else:
				continue

			last = firebase.fetch_last()
			if len(last) > 0:
				end_time = last[-1]['Open Time']

			PAIRS[symbol] = {'FROM_TOKEN': from_token, 'TO_TOKEN': to_token}
			PAIRS[symbol][DEFAULT_TIMEFRAME] = {'START_TIME': start_time, 'END_TIME': end_time}

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
	@error_logger()
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
	@error_logger()
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
	@error_logger()
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
	@error_logger()
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
					'trade_limit': 100,
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
					'date': '2025-04-20T19:00:00.000000Z',
					'symbol': 'BTCGBP',
					'from_token': 'BTC',
					'to_token': 'GBP',
					'trade_using': 'GBP',
					'start_time': 1672531200000,
					'end_time': 1704063600000,
					'take_profit': 10100,
					'stop_loss': 9900,
					'trade_limit': 100,
					'capital': 10000,
					'final_amount': '10148.289777869611 GBP',
					'profit': 148.2897778696115,
					'trade_events': [
						{
							'timestamp': 1673301600000,
							'datetime': '2023-01-09T22:00:00Z',
							'from_amount': 10000,
							'from_token': 'GBP',
							'to_amount': 0.7076244410651445,
							'to_token': 'BTC',
							'price': 14131.79,
						},
						{
							'timestamp': 1673373600000,
							'datetime': '2023-01-10T18:00:00Z',
							'from_amount': 0.7076244410651445,
							'from_token': 'BTC',
							'to_amount': 10148.289777869611,
							'to_token': 'GBP',
							'price': 14341.35,
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
					'stopped_by': 'profit',
					'performance_report': {
						'open_profit': 0,
						'total_profit': 148.2897778696115,
						'max_equity_run_up': 94.5598540595347,
						'max_drawdown': -28.420000000000073,
						'max_drawdown_percentage': -0.0020064755078670555,
						'total_trades': 1,
						'winning_count': 1,
						'losing_count': 0,
						'profit_percent': 0.01482897778696115,
						'percent_profitable': 1,
						'average_profit': 148.2897778696115,
						'average_winning_trade': 148.2897778696115,
						'average_losing_trade': None,
						'ratio_average_win_loss': None,
						'largest_winning_trade': 148.2897778696115,
						'largest_losing_trade': None,
						'largest_winning_trade_percent': 0.01482897778696115,
						'largest_losing_trade_percent': None,
						'total_bars': 20,
						'trade_reports': [
							{
								'buy_time': '2023-01-09T22:00:00Z',
								'buy_timestamp': 1673301600000,
								'sell_time': '2023-01-10T18:00:00Z',
								'sell_timestamp': 1673373600000,
								'profit': 148.2897778696115,
								'profit_percent': 0.01482897778696115,
								'cumulative_profit': 148.2897778696115,
								'cumulative_profit_percentage': 0.01482897778696115,
								'run_up': 94.5598540595347,
								'drawdown': -28.420000000000073,
								'drawdown_percentage': -0.0020064755078670555,
								'starting_amount': 10000,
								'starting_price': 14131.79,
								'final_amount': 10148.289777869611,
								'final_price': 14341.35,
							}
						],
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
				'trade_limit': IntegerField(default=100),
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
	@error_logger()
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
		trade_limit = request.data.get('trade_limit')
		backtest_date = timezone.now()

		if uid is None or uid == '':
			user_exists = False
		else:
			collection = FIREBASE.collection('User')
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

		if trade_limit is not None:
			try:
				trade_limit = int(trade_limit)
			except ValueError:
				return Response({'error': f'Invalid trade limit {trade_limit}!'}, 400)
			if trade_limit <= 0:
				return Response({'error': f'Invalid trade limit {trade_limit}! (Expected > 0)'}, 400)
			elif trade_limit > 300:
				return Response({'error': f'Invalid trade limit {trade_limit}! (Expected <= 300)'}, 400)

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

		token = FirebaseCandle().fetch_pair(symbol)
		to_token = token['to_token']
		from_token = token['from_token']

		results = calculate_amount(
			capital=capital_amount,
			open_times=df['Open Time'].to_numpy(),
			close_data=df['Close'].to_numpy(),
			buy_signals=buy_results,
			sell_signals=sell_results,
			unit_types=[to_token, from_token],
			stop_loss=stop_loss,
			take_profit=take_profit,
			trade_limit=trade_limit if trade_limit is not None else 100,  # Default 100 trades
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
			'from_token': from_token,
			'to_token': to_token,
			'trade_using': to_token,
			'start_time': start_time,
			'end_time': end_time,
			'take_profit': take_profit,
			'stop_loss': stop_loss,
			'trade_limit': trade_limit,
			'capital': capital_amount,
			'final_amount': trade_results[-1],
			'profit': holdings[-1] - capital_amount,
			'trade_events': trade_events,
			'buy_count': buy_count,
			'sell_count': sell_count,
			'buy_strategy': buy_strategy,
			'sell_strategy': sell_strategy,
			'stopped_by': stopped_by,
			'performance_report': analyse_strategy(
				capital_amount,
				df['Close'].to_numpy(),
				holdings,
				trade_types,
				trade_events,
			),
		}

		if user_exists:
			subcollection: CollectionReference = user_doc.collection('backtest_history')
			doc_ref: DocumentReference = subcollection.document()
			doc_ref.set(data)

		data['ohlc_data'] = data if return_ohlc is True else []
		data['backtest_id'] = doc_ref.id if user_exists else None

		return Response(data)


# Live Tradings
class TradeView(APIView):
	@extend_schema(
		request=inline_serializer(
			name='Trade Form',
			fields={
				'uid': CharField(default=''),
				'trade_type': CharField(default='ORDER|CANCEL'),
				'order_id': CharField(default=''),
				'from_token': CharField(default='GBP'),
				'to_token': IntegerField(default='BTC'),
				'from_amount': FloatField(default=100),
				'order_price': FloatField(default=10083),
			},
		),
	)
	@authenticate_jwt()
	@error_logger()
	def post(self, request: Request):
		uid = request.data.get('uid')
		trade_type = request.data.get('trade_type', '').upper()
		order_id = request.data.get('order_id', '')

		firebase = FirebaseOrderBook()
		if trade_type == 'CANCEL':
			if not firebase.has(order_id) or firebase.get(order_id).get('uid', None) != uid:
				return Response({'error': 'Order not found!'}, 400)
			result = firebase.cancel_order(order_id)
			return Response(result)

		if trade_type != 'ORDER':
			return Response({'error': 'Invalid trade type!'}, 400)

		from_token = request.data.get('from_token', '').upper()
		to_token = request.data.get('to_token', '').upper()
		from_amount = str(request.data.get('from_amount', ''))
		order_price = str(request.data.get('order_price', '0'))

		try:
			validate_field = 'from_amount'
			if calculate(from_amount, '<=', 0):
				raise ValueError
			validate_field = 'order_price'
			if calculate(order_price, '<=', 0):
				raise ValueError
		except ValueError:
			return Response({'error': f'Invalid {validate_field} "{order_price}"!'}, 400)

		try:
			result = firebase.create_order(uid, from_token, to_token, order_price, from_amount)
		except ValueError as e:
			return Response({'error': str(e)})
		except NotEnoughTokenException:
			return Response({'error': 'Not enough token!'})
		return Response(result)


class CheckOrders:
	def check(self):
		order_book = FirebaseOrderBook()
		orders = order_book.filter(status='OPEN')
		token_pair_price = {}
		for order in orders:
			order_id = order['id']
			price = order['price']
			from_token = order['from_token']
			to_token = order['to_token']
			pair = f'{from_token}{to_token}'
			reverse_pair = f'{to_token}{from_token}'
			if pair not in token_pair_price:
				token_pair_price[pair] = {'data': [], 'reverse': reverse_pair}
			token_pair_price[pair]['data'].append((price, order_id))

		success_pairs = asyncio.run(self.__check_orders_success(token_pair_price))
		self.__trade(success_pairs)
		return Response(status=200)

	async def __check_orders_success(self, order_prices):
		last_minute = timezone.now() - timedelta(minutes=2)
		since = int(last_minute.timestamp())
		prices = {}
		async with aiohttp.ClientSession() as session:
			tasks = [self.__fetch_kraken_ohlc(session, pair, since) for pair in order_prices]
			reverse_tasks = [
				self.__fetch_kraken_ohlc(session, order_prices[pair]['reverse'], since, pair) for pair in order_prices
			]
			results = await asyncio.gather(*tasks)
			reverse_results = await asyncio.gather(*reverse_tasks)
			results = {pair: (high, low) for pair, high, low in results if high is not None and low is not None}
			reverse_results = {
				pair: (calculate(1, '/', high), calculate(1, '/', low))
				for (pair, high, low) in reverse_results
				if high is not None and low is not None
			}
			prices = {**results, **reverse_results}

		success_pair = []
		for pair in order_prices:
			values = prices.get(pair)
			if values is None or values[0] is None or values[1] is None:
				log_error(f'Check Orders Failed due to token price not found! ({pair})')
				continue

			high, low = values

			for order_price, order_id in order_prices[pair]['data']:
				if calculate(order_price, '>=', low) and calculate(order_price, '<=', high):
					success_pair.append(order_id)

		return success_pair

	async def __fetch_kraken_ohlc(self, session: ClientSession, pair, since: int, reverse_pair_name=None):
		params = {'pair': pair, 'interval': 1, 'since': since}
		async with session.get(settings.KRAKEN_OHLC_API, params=params) as response:
			if response.status == 200:
				kraken_results = await response.json()
				if len(kraken_results['error']) > 0:
					return (pair, None, None) if reverse_pair_name is None else (reverse_pair_name, None, None)

				results = clean_kraken_pair(kraken_results)[pair]
				high = results[0][2]
				low = results[0][3]

				for result in results:
					high = max(high, result[2])
					low = min(low, result[3])

				return (pair, high, low) if reverse_pair_name is None else (reverse_pair_name, low, high)
			return (pair, None, None) if reverse_pair_name is None else (reverse_pair_name, None, None)

	def __trade(self, success_pairs):
		order_book = FirebaseOrderBook()
		trade_count = 0

		for success_pair in success_pairs:
			try:
				order_book.complete_order(success_pair)
				trade_count += 1
			except KeyError as e:
				order_details = order_book.get(success_pair)
				to_amount = calculate(order_details.get('volume', '0'), '*', order_details.get('price_str', '0'))
				log_warning(
					{
						'error': f'Order fails: Invalid key {str(e)}',
						'order_details': {
							'order_id': order_details.get('id'),
							'uid': order_details.get('uid'),
							'volume': order_details.get('volume'),
							'from_token': order_details.get('from_token'),
							'to_amount': str(to_amount),
							'to_token': order_details.get('to_token'),
						},
					}
				)
			except ValueError as e:
				order_details = order_book.get(success_pair)
				to_amount = calculate(order_details.get('volume', '0'), '*', order_details.get('price_str', '0'))
				log_warning(
					{
						'error': f'Order fails: {str(e)}',
						'order_details': {
							'order_id': order_details.get('id'),
							'uid': order_details.get('uid'),
							'volume': order_details.get('volume'),
							'from_token': order_details.get('from_token'),
							'to_amount': str(to_amount),
							'to_token': order_details.get('to_token'),
						},
					}
				)
			except NotEnoughTokenException:
				order_details = order_book.get(success_pair)
				to_amount = calculate(order_details.get('volume', '0'), '*', order_details.get('price_str', '0'))
				log_warning(
					{
						'error': 'Order fails: Not enough token!',
						'order_details': {
							'order_id': order_details.get('id'),
							'uid': order_details.get('uid'),
							'volume': order_details.get('volume'),
							'from_token': order_details.get('from_token'),
							'to_amount': str(to_amount),
							'to_token': order_details.get('to_token'),
						},
					}
				)

		log(f'Trade Success: {trade_count}')


class FetchCandle:
	UNIT_MS = settings.INTERVAL_MAP[DEFAULT_TIMEFRAME] * 60 * 1000
	BEGINNING = {
		Platform.BINANCE: datetime(year=2017, month=7, day=1),
	}

	def fetch(self):
		self.fetch_binance()

	def fetch_binance(self):
		pairs: dict[str, datetime] = {}
		for token in FirebaseCandle().fetch_pairs():
			symbol = token['token_id']
			firebase = FirebaseCandle(symbol, DEFAULT_TIMEFRAME, Platform.BINANCE.value)
			end_time = None
			last = firebase.fetch_last()
			if len(last) > 0:
				end_time = last[-1]['Open Time']
				if end_time > FirebaseCandle.TIMESTAMP_MS_THRES:
					end_time = end_time / 1000
				end_time = datetime.fromtimestamp(end_time)

			pairs[symbol] = end_time

		response = urllib.request.urlopen('https://api.binance.com/api/v3/exchangeInfo').read()
		all_symbols = list(map(lambda symbol: symbol['symbol'], json.loads(response)['symbols']))
		filtered_symbols = list(filter(lambda x: x in pairs, all_symbols))

		now = datetime.now()
		for symbol in filtered_symbols:
			start_time = pairs[symbol]
			has_start = True if start_time is not None else False
			if start_time is None:
				start_time = self.BEGINNING[Platform.BINANCE]
			start_time = datetime(start_time.year, start_time.month, 1)

			concat_dfs = []
			while start_time < now:
				path = f'data/spot/monthly/klines/{symbol}/{DEFAULT_TIMEFRAME}'
				filename = f'{symbol.upper()}-{DEFAULT_TIMEFRAME}-{start_time.year}-{start_time.month:02d}.zip'
				write_path = BASE_DIR / 'binance_public_data' / path / filename
				if write_path.exists():
					write_path.unlink()
				parent_path = BASE_DIR / 'binance_public_data' / path
				parent_path.mkdir(parents=True, exist_ok=True)

				download_url = f'https://data.binance.vision/{path}/{filename}'
				try:
					dl_file = urllib.request.urlopen(download_url)
					length = dl_file.getheader('content-length')
					if length:
						length = int(length)
						blocksize = max(4096, length // 100)

					with open(write_path, 'wb') as out_file:
						dl_progress = 0
						while True:
							buf = dl_file.read(blocksize)
							if not buf:
								break
							dl_progress += len(buf)
							out_file.write(buf)

					df = pd.read_csv(write_path, compression='zip', header=None)
					df = df.iloc[:, 0:6]
					df.columns = ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume']
					if df.iloc[0, 0] > FirebaseCandle.TIMESTAMP_NS_THRES:
						df['Open Time'] = df['Open Time'] / 1000
					elif df.iloc[0, 0] < FirebaseCandle.TIMESTAMP_MS_THRES:
						df['Open Time'] = df['Open Time'] * 1000

					df_start_time = datetime.fromtimestamp(df.iloc[0, 0] / 1000)
					num_days = calendar.monthrange(df_start_time.year, df_start_time.month)[1]
					df_start_time = datetime(year=df_start_time.year, month=df_start_time.month, day=1)
					df_end_time = df_start_time + timedelta(days=num_days)
					start_timestamp = int(df_start_time.timestamp() * 1000)
					end_timestamp = int(df_end_time.timestamp() * 1000)
					all_time = list(range(start_timestamp, end_timestamp, self.UNIT_MS))
					full_df = pd.DataFrame({'Open Time': all_time})
					full_df = full_df.merge(df, how='left', on='Open Time')
					full_df = full_df.replace(np.nan, None)
					concat_dfs.append(full_df)
				except urllib.error.HTTPError:
					log_warning(f'Failed to download {download_url}!')

				start_time = start_time + timedelta(days=31)
				start_time = datetime(start_time.year, start_time.month, 1)

			if all([df is None for df in concat_dfs]):
				continue

			df = pd.concat(concat_dfs).reset_index(drop=True)
			if has_start:
				first_valid = 0
			else:
				first_valid = df['Open'].first_valid_index()
			last_valid = df['Open'].last_valid_index()
			df = df.iloc[first_valid : last_valid + 1, :]

			if len(df) == 0:
				continue

			rows_per_day = round(60 * 24 / settings.INTERVAL_MAP[DEFAULT_TIMEFRAME])
			max_upload_limit = FirebaseCandle.MAX_UPLOAD_LIMIT - (FirebaseCandle.MAX_UPLOAD_LIMIT % rows_per_day)
			for _, group in df.groupby(np.arange(len(df)) // max_upload_limit):
				FirebaseCandle(symbol, DEFAULT_TIMEFRAME, Platform.BINANCE.value).save_ohlc(group)
				log(f'Updated {symbol} Binance data!')


class ScheduleView(APIView):
	@authenticate_scheduler_oicd()
	@error_logger()
	def post(self, request: Request):
		now = timezone.now()
		monthly = now.day == 5

		error = []
		completed_task = []

		def check_order_fn():
			CheckOrders().check()

		completed_task, error = self.schedule_run(check_order_fn, 'Check Orders', completed_task, error)

		def fetch_candles_fn():
			FetchCandle().fetch()

		if monthly:
			completed_task, error = self.schedule_run(fetch_candles_fn, 'Fetch Candles', completed_task, error)

		log(f'Completed Task: [{", ".join(completed_task)}]')

		if len(error) > 0:
			log_error('\n'.join(error))
			return Response(status=500)

		return Response(status=200)

	def schedule_run(self, function, title, completed_task: list[str], error: list[str], retry=False):
		try:
			function()
			completed_task.append(title)
		except Exception as e:
			error.append(f'Error {title}: {str(e)}')
			if retry:
				completed_task, error = self.schedule_run(function, title, completed_task, error)

		return completed_task, error
