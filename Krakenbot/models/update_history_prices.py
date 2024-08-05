import os
import asyncio
import aiohttp
from datetime import timedelta
from rest_framework.request import Request
from Krakenbot.models.firebase_token import FirebaseToken
from Krakenbot.utils import authenticate_scheduler_oicd, clean_kraken_pair, usd_to_gbp
from django.utils import timezone

class UpdateHistoryPrices:
	KRAKEN_OHLC_API = 'https://api.kraken.com/0/public/OHLC'

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

	async def __fetch_kraken_OHLC(self, session: aiohttp.ClientSession, pair: str):
		async with session.get(self.KRAKEN_OHLC_API, params={'pair': pair, 'interval': self.INTERVAL}) as response:
			if response.status == 200:
					kraken_results = await response.json()
					if len(kraken_results['error']) > 0:
						return (pair, timezone.now() - timedelta(minutes=self.HISTORY_COUNT), [0, 0])

					results = clean_kraken_pair(kraken_results)[pair]
					try:
						results = results[-(self.HISTORY_COUNT + 1):] # +1 to get latest one that is not closed yet
					except IndexError:
						pass # Get all results (Capped at 720 by Kraken)

					start_time = timezone.datetime.fromtimestamp(results[0][0])
					close_prices = [float(result[4]) for result in results] # Get close price only

					return (pair, start_time, close_prices)

	async def update(self, request: Request):
		authenticate_scheduler_oicd(request)
		firebase = FirebaseToken()
		pairs = [token.get('token_id') + self.FIAT for token in firebase.all() if token.get('token_id') != self.FIAT]

		firebase.start_batch_write()
		firebase.update_history_prices(self.FIAT, timezone.now() - timedelta(days=7), [1, 1])
		firebase.update_history_prices('USD', timezone.now() - timedelta(days=7), [1, 1])

		async with aiohttp.ClientSession() as session:
			tasks = [self.__fetch_kraken_OHLC(session, pair) for pair in pairs]
			results = await asyncio.gather(*tasks)
			results = [(pair.replace(self.FIAT, ''), start_time, close_prices) for (pair, start_time, close_prices) in results if close_prices != [0, 0]]
			all_tokens = [token for (token, _, close_prices) in results if close_prices != [0, 0]]

			usd_pairs = [
				token.get('token_id') + 'USD' for token in firebase.all()
				if token.get('token_id') not in ['USD', self.FIAT, *all_tokens]
			]

			if len(usd_pairs) > 0:
				tasks = [self.__fetch_kraken_OHLC(session, pair) for pair in usd_pairs]
				usd_results = await asyncio.gather(*tasks)
				usd_results = [(pair.replace('USD', ''), start_time, close_prices) for (pair, start_time, close_prices) in usd_results]
				for (token, start_time, close_prices) in usd_results:
					usd_rate = await usd_to_gbp()
					close_prices = [close_price * usd_rate for close_price in close_prices]
					firebase.update_history_prices(token, start_time, close_prices)

			for (token, start_time, close_prices) in results:
				firebase.update_history_prices(token, start_time, close_prices)
			firebase.commit_batch_write()
