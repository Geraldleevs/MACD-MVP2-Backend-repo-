import asyncio
from datetime import timedelta
import aiohttp
from Krakenbot.exceptions import NotEnoughTokenException, TokenNotFoundException
from rest_framework.request import Request
from Krakenbot.models.firebase_order_book import FirebaseOrderBook
from Krakenbot.utils import acc_calc, authenticate_scheduler_oicd, clean_kraken_pair, log_error, log_warning, log
from django.utils import timezone

class CheckOrders:
	KRAKEN_OHLC_API = 'https://api.kraken.com/0/public/OHLC'

	async def __fetch_kraken_ohlc(self, session: aiohttp.ClientSession, pair: str, since: int, reverse_pair_name: str = None):
		async with session.get(self.KRAKEN_OHLC_API, params={'pair': pair, 'interval': 1, 'since': since}) as response:
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

				return (pair, high, low) if reverse_pair_name is None else (reverse_pair_name, high, low)
			return (pair, None, None) if reverse_pair_name is None else (reverse_pair_name, None, None)

	def __trade(self, success_pairs):
		order_book = FirebaseOrderBook()
		trade_count = 0

		for success_pair in success_pairs:
			try:
				order_book.complete_order(success_pair)
				trade_count += 1
			except KeyError:
				order_details = order_book.get(success_pair)
				to_amount = acc_calc(order_details.get('volume', '0'), '*', order_details.get('price_str', '0'))
				message = {
					'message': 'Order Fails due to Invalid Fields',
					'Order ID': order_details.get('id'),
					'UID': order_details.get('uid'),
					'From': f'{order_details.get('volume')} {order_details.get('from_token')}',
					'To': f'{str(to_amount)} {order_details.get('to_token')}',
				}
				log_warning(message)
			except NotEnoughTokenException:
				order_details = order_book.get(success_pair)
				to_amount = acc_calc(order_details.get('volume', '0'), '*', order_details.get('price_str', '0'))
				message = {
					'message': 'Order Fails due to Not Enough Token',
					'Order ID': order_details.get('id'),
					'UID': order_details.get('uid'),
					'From': f'{order_details.get('volume')} {order_details.get('from_token')}',
					'To': f'{str(to_amount)} {order_details.get('to_token')}',
				}
				log_warning(message)

		log(f'Trade Success: {trade_count}')

	async def __check_orders_success(self, order_prices):
		last_minute = timezone.now() - timedelta(minutes=2)
		since = int(last_minute.timestamp())
		prices = {}
		async with aiohttp.ClientSession() as session:
			tasks = [self.__fetch_kraken_ohlc(session, pair, since) for pair in order_prices]
			reverse_tasks = [self.__fetch_kraken_ohlc(session, order_prices[pair]['reverse'], since, pair) for pair in order_prices]
			results = await asyncio.gather(*tasks)
			reverse_results = await asyncio.gather(*reverse_tasks)
			results = { pair: (high, low) for (pair, high, low) in results if high is not None and low is not None }
			reverse_results = { pair: (acc_calc(1, '/', high), acc_calc(1, '/', low)) for (pair, high, low) in reverse_results if high is not None and low is not None }
			prices = { **results, **reverse_results }

		success_pair = []
		for pair in order_prices:
			values = prices.get(pair)
			if values is None or values[0] is None or values[1] is None:
				log_error(f'Check Orders Failed due to token price not found! ({pair})')
				continue

			(high, low) = values

			for (order_price, order_id) in order_prices[pair]['data']:
				if acc_calc(order_price, '-', low) >= 0 and acc_calc(order_price, '-', high) <= 0:
					success_pair.append(order_id)

		return success_pair


	def __get_orders(self):
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
				token_pair_price[pair] = { 'data': [], 'reverse': reverse_pair }
			token_pair_price[pair]['data'].append((price, order_id))

		return token_pair_price

	def check(self, request: Request):
		authenticate_scheduler_oicd(request)
		order_prices = self.__get_orders()
		success_pairs = asyncio.run(self.__check_orders_success(order_prices))
		self.__trade(success_pairs)
