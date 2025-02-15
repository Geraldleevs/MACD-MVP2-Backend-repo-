from datetime import datetime, timedelta
from functools import reduce
from itertools import combinations
from random import normalvariate
from typing import List, Literal
import asyncio
import aiohttp
from django.http import JsonResponse
import requests
import numpy as np
import pandas as pd
from decimal import Decimal

from google.cloud.firestore_v1.base_query import FieldFilter
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from Krakenbot import settings
from Krakenbot.exceptions import BadRequestException, DatabaseIncorrectDataException, NoUserSelectedException, NotAuthorisedException, ServerErrorException, NotEnoughTokenException
from Krakenbot.models.firebase import FirebaseAnalysis, FirebaseCandle, FirebaseLiveTrade, FirebaseNews, FirebaseOrderBook, FirebaseRecommendation, FirebaseToken, FirebaseUsers, FirebaseWallet, NewsField
from Krakenbot.backtest import AnalyseBacktest, ApplyBacktest, indicator_names
from Krakenbot.update_candles import main as update_candles
from Krakenbot.utils import acc_calc, authenticate_scheduler_oicd, authenticate_user_jwt, check_take_profit_stop_loss, clean_kraken_pair, log, log_error, log_warning, usd_to_gbp


class FavouriteTokens(APIView):
	def get(self, request: Request):
		uid = authenticate_user_jwt(request)
		user = settings.firebase.collection('User').document(uid).get()
		results = user.to_dict().get('favourite_tokens')
		return JsonResponse({ 'results': results })

	def post(self, request: Request):
		uid = authenticate_user_jwt(request)
		favourite_token = request.data.get('favourite_tokens')
		print(favourite_token)
		user = settings.firebase.collection('User').document(uid)
		existing = set(user.get().to_dict().get('favourite_tokens'))
		if favourite_token in existing:
			existing.remove(favourite_token)
		else:
			existing.add(favourite_token)
		user.set({ 'favourite_tokens': list(existing) }, True)
		return JsonResponse({ 'status': 'success' })


class MarketList(APIView):
	def get(self, request: Request):
		all_tokens = [token.to_dict() for token in settings.firebase.collection('Token').stream()]
		token_map = {token['token_id']: token for token in all_tokens}

		direct_convert = [token.to_dict() for token in settings.firebase.collection('TokenPair').where(filter=FieldFilter('from_token_id', '==', settings.FIAT)).stream()]
		reverse_convert = [token.to_dict() for token in settings.firebase.collection('TokenPair').where(filter=FieldFilter('to_token_id', '==', settings.FIAT)).stream()]

		full_results = []
		for token in direct_convert:
			results = requests.get('https://api.kraken.com/0/public/OHLC', { 'pair': token['kraken_pair'], 'interval': 1 }).json()['result'][token['kraken_pair']]
			results = [{
				'timestamp': result[0],
				'open': acc_calc(1, '/', result[1] if float(result[1]) != 0 else 1),
				'high': acc_calc(1, '/', result[2] if float(result[2]) != 0 else 1),
				'low': acc_calc(1, '/', result[3] if float(result[3]) != 0 else 1),
				'close': acc_calc(1, '/', result[4] if float(result[4]) != 0 else 1),
				'vwap': acc_calc(1, '/', result[5] if float(result[5]) != 0 else 1),
				'volume': acc_calc(1, '/', result[6] if float(result[6]) != 0 else 1),
				'count': result[7],
			} for result in results[:24]]
			full_results.append({ 'token':token['to_token_id'], 'data': results })

		for token in reverse_convert:
			results = requests.get('https://api.kraken.com/0/public/OHLC', { 'pair': token['kraken_pair'], 'interval': 1 }).json()['result'][token['kraken_pair']]
			results = [{
				'timestamp': result[0],
				'open': Decimal(result[1]),
				'high': Decimal(result[2]),
				'low': Decimal(result[3]),
				'close': Decimal(result[4]),
				'vwap': Decimal(result[5]),
				'volume': Decimal(result[6]),
				'count': result[7],
			} for result in results[:24]]
			full_results.append({ 'token':token['from_token_id'], 'data': results })

		results = []
		for result in full_results:
			data = result['data']
			token = result['token']

			final = round(data[0]['close'], 2)
			first = round(data[-1]['close'], 2)
			volume = reduce(lambda x, y: acc_calc(x, '+', acc_calc(y['volume'], '*', y['close'])), data, 0)

			results.append({
				'icon_url': token_map[token]['icon'],
				'symbol': token,
				'base_asset': settings.FIAT,
				'price': float(round(data[0]['close'], 2)),
				'chart_data': [float(round(row['close'], 2)) for row in data[::-1]],
				'change24h': float(acc_calc(acc_calc(final, '-', first), '/', 1 if first == 0 else first)),
				'volume': float(round(volume, 2)),
			})

		return JsonResponse({ 'results': results })


class MarketPairs(APIView):
	def get(self, request: Request):
		pairs = [pair.to_dict() for pair in settings.firebase.collection('TokenPair').stream()]
		data = []
		for pair in pairs:
			if pair['from_token_id'] == 'BTC' and pair['to_token_id'] == settings.FIAT:
				default_pair = { 'pair': pair['trading_view_pair'], 'from': pair['from_token_id'], 'to': pair['to_token_id'] }
			data.append({ 'pair': pair['trading_view_pair'], 'from': pair['from_token_id'], 'to': pair['to_token_id'] })
		return JsonResponse({ 'results': { 'data': data, 'default_pair': default_pair }})


class UserActivities(APIView):
	def get(self, request: Request):
		uid = authenticate_user_jwt(request)
		all_tokens = [token.to_dict() for token in settings.firebase.collection('Token').stream()]
		token_map = {token['token_id']: token['fiat'] for token in all_tokens}

		if settings.firebase.collection('User').document(uid).collection('transaction').count().get()[0][0].value < 1:
			return JsonResponse({ 'results': [] })

		transactions = [transaction.to_dict() for transaction in settings.firebase.collection('User').document(uid).collection('transaction').stream()]

		results = []
		for transaction in transactions:
			results.append({
				'id': transaction['id'],
				'type': 'purchase' if token_map[transaction['from_token_id']] else 'sale',
				'timestamp': transaction['time'],
				'from_token': transaction['from_token_id'],
				'from_amount': float(transaction['from_amount']),
				'to_token': transaction['to_token_id'],
				'to_amount': float(transaction['to_amount']),
				'price': acc_calc(1, '/', transaction['conversion_rate'], 2),
			})

		return JsonResponse({ 'results': results })


class UserAssets(APIView):
	def get(self, request: Request):
		uid = authenticate_user_jwt(request)
		all_tokens = [token.to_dict() for token in settings.firebase.collection('Token').stream()]
		token_map = {token['token_id']: token for token in all_tokens}
		wallets = [wallet.to_dict() for wallet in settings.firebase.collection('User').document(uid).collection('wallet').stream()]
		wallet_map = {wallet['token_id']: wallet for wallet in wallets}
		all_tokens = [token['token_id'] for token in wallets]

		direct_convert = [token.to_dict() for token in settings.firebase.collection('TokenPair').where(filter=FieldFilter('from_token_id', '==', settings.FIAT)).stream()]
		direct_convert = [token for token in direct_convert if token['to_token_id'] in all_tokens]
		reverse_convert = [token.to_dict() for token in settings.firebase.collection('TokenPair').where(filter=FieldFilter('to_token_id', '==', settings.FIAT)).stream()]
		reverse_convert = [token for token in reverse_convert if token['from_token_id'] in all_tokens]

		full_results = []
		for token in direct_convert:
			results = requests.get('https://api.kraken.com/0/public/OHLC', { 'pair': token['kraken_pair'], 'interval': 1 }).json()['result'][token['kraken_pair']]
			results = [{
				'timestamp': result[0],
				'open': acc_calc(1, '/', result[1] if float(result[1]) != 0 else 1),
				'high': acc_calc(1, '/', result[2] if float(result[2]) != 0 else 1),
				'low': acc_calc(1, '/', result[3] if float(result[3]) != 0 else 1),
				'close': acc_calc(1, '/', result[4] if float(result[4]) != 0 else 1),
				'vwap': acc_calc(1, '/', result[5] if float(result[5]) != 0 else 1),
				'volume': acc_calc(1, '/', result[6] if float(result[6]) != 0 else 1),
				'count': result[7],
			} for result in results[:24]]
			full_results.append({ 'token':token['to_token_id'], 'data': results })

		for token in reverse_convert:
			results = requests.get('https://api.kraken.com/0/public/OHLC', { 'pair': token['kraken_pair'], 'interval': 1 }).json()['result'][token['kraken_pair']]
			results = [{
				'timestamp': result[0],
				'open': Decimal(result[1]),
				'high': Decimal(result[2]),
				'low': Decimal(result[3]),
				'close': Decimal(result[4]),
				'vwap': Decimal(result[5]),
				'volume': Decimal(result[6]),
				'count': result[7],
			} for result in results[:24]]
			full_results.append({ 'token':token['from_token_id'], 'data': results })

		accum_value = 0
		results = []
		for result in full_results:
			data = result['data']
			token = result['token']

			final = round(data[0]['close'], 2)
			first = round(data[-1]['close'], 2)
			amount = wallet_map.get(token, {}).get('amount', 0)
			price = round(data[0]['close'], 2)
			value = acc_calc(amount, '*', price)
			accum_value = acc_calc(accum_value, '+', value)

			results.append({
				'icon_url': token_map[token]['icon'],
				'token_id': token,
				'token': token_map[token]['token_name'],
				'allocation': 0,
				'price': float(price),
				'change': float(acc_calc(acc_calc(final, '-', first), '/', 1 if first == 0 else first)),
				'balance': float(amount),
				'value': float(value),
			})

		if settings.FIAT in wallet_map:
			amount = wallet_map.get(token, {}).get('amount', 0)
			accum_value = acc_calc(accum_value, '+', amount)
			results.append({
				'icon_url': token_map[settings.FIAT]['icon'],
				'token_id': settings.FIAT,
				'token': token_map[settings.FIAT]['token_name'],
				'allocation': float(acc_calc(amount, '/', accum_value)),
				'price': 1,
				'change': 0,
				'balance': amount,
				'value': amount,
			})

		for result in results:
			result['allocation'] = float(acc_calc(result['value'], '/', accum_value))

		return JsonResponse({ 'results': results })


class UserDashboard(APIView):
	def get(self, request: Request):
		uid = authenticate_user_jwt(request)
		results = [dashboard.to_dict() for dashboard in settings.firebase.collection('User').document(uid).collection('dashboard').stream()]
		names = [result['name'] for result in results]
		if 'Default' in names:
			results.sort(key= lambda a: -1 if a == 'Default' else 0)
		else:
			results = [{ 'name': 'Default', 'charts': ['price', 'aggressor', 'trade', 'volatility', 'volume'] }, *results]
		return JsonResponse({ 'results': results })

	def post(self, request: Request):
		uid = authenticate_user_jwt(request)
		dashboard_name = request.data.get('dashboard_name')
		dashboard_charts = request.data.get('dashboard_charts')
		create = request.data.get('create')

		dashboard = settings.firebase.collection('User').document(uid).collection('dashboard').document(dashboard_name)

		if create and dashboard.get.exists:
			return JsonResponse({ 'error': 'Dashboard name is taken!' }, status = 400)

		dashboard.set({ 'name': dashboard_name, 'charts': dashboard_charts })
		return JsonResponse({ 'status': 'success' })


class UserPortfolio(APIView):
	def get(self, request: Request):
		uid = authenticate_user_jwt(request)
		start_time = datetime.now() - timedelta(days=30)
		results = [portfolio.to_dict() for portfolio in settings.firebase.collection('User').document(uid).collection('portfolio').where(filter=FieldFilter('time', '>=', start_time)).stream()]
		results = [{'time': result['time'], 'value': float(result['value'])} for result in results]
		return JsonResponse({ 'results': results })


class UserProfile(APIView):
	def get(self, request: Request):
		uid = authenticate_user_jwt(request)
		user = settings.firebase.collection('User').document(uid).get().to_dict()
		results = {
			'id': uid,
			'username': user['display_name'],
			'name': user['display_name'],
			'daily_xp': 0,
			'daily_xp_goal': 150,
			'total_xp': 87,
			'streak': 5,
			'achievements': 8,
			'total_achievements': 15,
			'active_days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
			'profile_image': user['image'],
			'profile_complete_percentage': 80,
		}
		return JsonResponse({ 'results': results })


class UserWalletValue(APIView):
	def get(self, request: Request):
		uid = authenticate_user_jwt(request)
		wallets = [wallet.to_dict() for wallet in settings.firebase.collection('User').document(uid).collection('wallet').stream()]
		wallet_map = {wallet['token_id']: wallet for wallet in wallets}
		all_tokens = [token['token_id'] for token in wallets]

		direct_convert = [token.to_dict() for token in settings.firebase.collection('TokenPair').where(filter=FieldFilter('from_token_id', '==', settings.FIAT)).stream()]
		direct_convert = [token for token in direct_convert if token['to_token_id'] in all_tokens]
		reverse_convert = [token.to_dict() for token in settings.firebase.collection('TokenPair').where(filter=FieldFilter('to_token_id', '==', settings.FIAT)).stream()]
		reverse_convert = [token for token in reverse_convert if token['from_token_id'] in all_tokens]

		full_results = []
		for token in direct_convert:
			results = requests.get('https://api.kraken.com/0/public/OHLC', { 'pair': token['kraken_pair'], 'interval': 1 }).json()['result'][token['kraken_pair']]
			results = [{
				'timestamp': result[0],
				'open': acc_calc(1, '/', result[1] if float(result[1]) != 0 else 1),
				'high': acc_calc(1, '/', result[2] if float(result[2]) != 0 else 1),
				'low': acc_calc(1, '/', result[3] if float(result[3]) != 0 else 1),
				'close': acc_calc(1, '/', result[4] if float(result[4]) != 0 else 1),
				'vwap': acc_calc(1, '/', result[5] if float(result[5]) != 0 else 1),
				'volume': acc_calc(1, '/', result[6] if float(result[6]) != 0 else 1),
				'count': result[7],
			} for result in results[:24]]
			full_results.append({ 'token':token['to_token_id'], 'data': results })

		for token in reverse_convert:
			results = requests.get('https://api.kraken.com/0/public/OHLC', { 'pair': token['kraken_pair'], 'interval': 1 }).json()['result'][token['kraken_pair']]
			results = [{
				'timestamp': result[0],
				'open': Decimal(result[1]),
				'high': Decimal(result[2]),
				'low': Decimal(result[3]),
				'close': Decimal(result[4]),
				'vwap': Decimal(result[5]),
				'volume': Decimal(result[6]),
				'count': result[7],
			} for result in results[:24]]
			full_results.append({ 'token':token['from_token_id'], 'data': results })

		accum_value = 0
		results = []
		for result in full_results:
			data = result['data']
			token = result['token']

			amount = wallet_map.get(token, {}).get('amount', 0)
			price = round(data[0]['close'], 2)
			value = acc_calc(amount, '*', price)
			accum_value = acc_calc(accum_value, '+', value)

		if settings.FIAT in wallet_map:
			amount = wallet_map.get(token, {}).get('amount', 0)
			accum_value = acc_calc(accum_value, '+', amount)

		return JsonResponse({ 'results': { 'value': float(accum_value) } })
