import os
import asyncio
import aiohttp
import requests
from datetime import datetime, timedelta
from rest_framework.request import Request
from Krakenbot.models.firebase_token import FirebaseToken
from Krakenbot.models.firebase_users import FirebaseUsers
from Krakenbot.models.firebase_wallet import FirebaseWallet
from Krakenbot.utils import authenticate_scheduler_oicd, clean_kraken_pair, usd_to_gbp
from django.utils import timezone

class UpdateHistoryPrices:
	KRAKEN_OHLC_API = 'https://api.kraken.com/0/public/OHLC'
	COIN_GECKO_API = 'https://api.coingecko.com/api/v3/coins/markets'

	def __init__(self):
		self.FIAT = os.environ.get('FIAT', 'GBP')
		try:
			self.INTERVAL = int(os.environ.get('TOKEN_HISTORY_INTERVAL_IN_MINUTES', '120'))
		except ValueError:
			self.INTERVAL = 120

		try:
			self.HISTORY_COUNT = int(os.environ.get('MAX_TOKEN_HISTORY_IN_DAYS', '7')) * 24 * 60 // self.INTERVAL # Multiply into minutes
		except ValueError:
			self.HISTORY_COUNT = 7 * 24 * 60 // self.INTERVAL # 7 Days

	async def __fetch_kraken_ohlc(self, session: aiohttp.ClientSession, pair: str):
		async with session.get(self.KRAKEN_OHLC_API, params={'pair': pair, 'interval': self.INTERVAL}) as response:
			if response.status == 200:
				kraken_results = await response.json()
				if len(kraken_results['error']) > 0:
					return (pair, [timezone.now() - timedelta(minutes=self.HISTORY_COUNT), timezone.now()], [0, 0])

				results = clean_kraken_pair(kraken_results)[pair]
				try:
					results = results[-(self.HISTORY_COUNT + 1):] # +1 to get latest one that is not closed yet
				except IndexError:
					pass # Get all results (Capped at 720 by Kraken)

				times = [timezone.datetime.fromtimestamp(result[0]) for result in results]
				close_prices = [float(result[4]) for result in results] # Get close price only

				return (pair, times, close_prices)
			return (pair, timezone.now() - timedelta(minutes=self.HISTORY_COUNT), [0, 0])

	async def __fetch_gecko_metrics(self, tokens: dict[str, str]):
		query = { 'vs_currency': self.FIAT, 'ids': ','.join([token for token in tokens]) }
		results = requests.get(self.COIN_GECKO_API, params=query)

		if results.status_code != 200:
			return {}

		results = results.json()
		metrics = {}
		for result in results:
			metrics[tokens[result['id']]] = {
				'market_cap': result['market_cap'],
				'fully_diluted_valuation': result['fully_diluted_valuation'],
				'total_volume': result['total_volume'],
				'circulating_supply': result['circulating_supply'],
				'total_supply': result['total_supply'],
				'max_supply': result['max_supply'] if result['max_supply'] is not None else -1,
				'all_time_high': result['ath'],
				'all_time_low': result['atl'],
				'all_time_high_time': datetime.fromisoformat(result['ath_date']),
				'all_time_low_time': datetime.fromisoformat(result['atl_date'])
			}

		return metrics

	def __update_user_history(self, prices: dict[str, float]):
		all_user_id = FirebaseUsers().get_all_user_id()
		current_time = timezone.now()
		for uid in all_user_id:
			wallet = FirebaseWallet(uid).get_wallet()
			value = 0

			for token in wallet:
				try:
					token_id = token['id']
					total_amount = token.get('amount', 0) + token.get('krakenbot_amount', 0)
					if total_amount > 0:
						value += prices.get(token_id, 0) * total_amount
				except KeyError:
					continue

			FirebaseUsers(uid).update_portfolio_value(value, current_time)


	async def update(self, request: Request):
		authenticate_scheduler_oicd(request)
		firebase = FirebaseToken()
		firebase_tokens = firebase.filter(is_active=None, is_fiat=False)
		pairs = [token.get('token_id') + self.FIAT for token in firebase_tokens]
		pairs.append('GBPUSD')

		firebase.start_batch_write()
		coin_gecko_ids = { token.get('coingecko_id'): token.get('token_id') for token in firebase_tokens }
		metrics = await self.__fetch_gecko_metrics(coin_gecko_ids)
		for metric in metrics:
			firebase.update(metric, metrics[metric])

		firebase.update_history_prices(self.FIAT, [timezone.now() - timedelta(days=7), timezone.now()], [1, 1])

		async with aiohttp.ClientSession() as session:
			tasks = [self.__fetch_kraken_ohlc(session, pair) for pair in pairs]
			results = await asyncio.gather(*tasks)
			results = [(pair.replace(self.FIAT, ''), times, close_prices) for (pair, times, close_prices) in results if close_prices != [0, 0]]
			all_tokens = [token for (token, _, close_prices) in results if close_prices != [0, 0]]
			all_prices = {self.FIAT: 1}

			usd_pairs = [
				token.get('token_id') + 'USD' for token in firebase.filter(is_active=None)
				if token.get('token_id') not in ['USD', self.FIAT, *all_tokens]
			]

			if len(usd_pairs) > 0:
				tasks = [self.__fetch_kraken_ohlc(session, pair) for pair in usd_pairs]
				usd_results = await asyncio.gather(*tasks)
				usd_results = [(pair.replace('USD', ''), times, close_prices) for (pair, times, close_prices) in usd_results if close_prices != [0, 0]] # Skip failed tokens
				for (token, times, close_prices) in usd_results:
					usd_rate = await usd_to_gbp()
					close_prices = [close_price * usd_rate for close_price in close_prices]
					all_prices[token] = close_prices[-1]
					firebase.update_history_prices(token, times, close_prices)

			for (token, times, close_prices) in results:
				if close_prices == [0, 0]: # Skip failed tokens
					continue
				if token == 'USD':
					close_prices = [1 / price for price in close_prices]
				firebase.update_history_prices(token, times, close_prices)
				all_prices[token] = close_prices[-1]
			firebase.commit_batch_write()

		self.__update_user_history(all_prices)
