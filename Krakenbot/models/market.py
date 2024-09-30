import asyncio
from decimal import Decimal
from typing import Literal
from rest_framework.request import Request
from Krakenbot.exceptions import BadRequestException
from Krakenbot.models.firebase_token import FirebaseToken
from Krakenbot.utils import clean_kraken_pair, usd_to_gbp
import requests

class Market:
	KRAKEN_PAIR_API = 'https://api.kraken.com/0/public/Ticker'

	def __fetch_kraken_pair(self, token, reverse_price = False):
		result = requests.get(self.KRAKEN_PAIR_API).json()

		if len(result['error']) > 0:
			return []

		result = clean_kraken_pair(result)
		result = self.__parse_kraken_pair(result, token, reverse_price)
		return result

	def __get_price(self, result, property_path):
		price = Decimal(str(result[property_path][0]))
		last_open = Decimal(str(result['last_close']))
		if property_path == 'bid' and price > 0:
			price = 1 / price
			try:
				last_open = 1 / last_open
			except ZeroDivisionError:
				last_open = 0
		return (price, last_open)

	def __parse_kraken_pair(self, kraken_result, token, reverse_price):
		for (pair, result) in kraken_result.items():
			kraken_result[pair] = {'ask': result['a'], 'bid': result['b'], 'last_close': result['o']}

		sell = 'bid' if reverse_price else 'ask'
		buy = 'ask' if reverse_price else 'bid'
		filtered_results = {}

		for (pair, result) in kraken_result.items():
			if (token is not None and token in pair):
				filtered_results[pair] = result

		results = {}
		for (pair, result) in filtered_results.items():
			if pair.startswith(token):
				(price, last_close) = self.__get_price(result, sell)
			elif pair.endswith(token):
				(price, last_close) = self.__get_price(result, buy)
			else:
				continue

			result_token = pair.replace(token, '')

			if result_token not in results:
				results[result_token] = (price, last_close)

		return [{ 'token': token, 'price': price, 'last_close': last_close } for (token, (price, last_close)) in results.items()]

	def get_market(self, request: Request | None = None, convert_from = '', convert_to = '', exclude = '', force_convert: Literal['FORCE'] = '', include_inactive: Literal['INCLUDE'] = ''):
		'''
		force_convert can only be used when convert from/to GBP, but not specific pair
		'''

		if request is not None:
			convert_from = request.query_params.get('convert_from', '').strip().upper()
			convert_to = request.query_params.get('convert_to', '').strip().upper()
			exclude = request.query_params.get('exclude', '').strip().upper()
			force_convert = request.query_params.get('force_convert', '').strip().upper()
			include_inactive = request.query_params.get('include_inactive', '').strip().upper()
		else:
			convert_from = convert_from.upper()
			convert_to = convert_to.upper()
			exclude = exclude.upper()
			force_convert = force_convert.upper()
			include_inactive = include_inactive.upper()

		firebase_token = FirebaseToken()

		try:
			if convert_from != '':
				current_token = firebase_token.get(convert_from)
				reverse_price = False
			else:
				current_token = firebase_token.get(convert_to)
				reverse_price = True
			current_token = current_token['token_id']
		except Exception:
			raise BadRequestException()

		market = self.__fetch_kraken_pair(current_token, reverse_price)
		market.append({ 'token': current_token, 'price': 1, 'last_close': 1 })

		specific_convert = not reverse_price and convert_to != ''
		if specific_convert:
			market = [price for price in market if price['token'] == convert_to]
		else:
			other_tokens = firebase_token.filter(is_active=None) if include_inactive == 'INCLUDE' else firebase_token.all()
			other_tokens = [token['token_id'] for token in other_tokens]
			market = [price for price in market if price['token'] in other_tokens]

		if exclude != '':
			market = [price for price in market if price['token'] != exclude]

		if specific_convert or force_convert != 'FORCE' or 'GBP' not in [convert_from, convert_to]:
			return market

		all_market_token = [price['token'] for price in market]
		usd_market = self.__fetch_kraken_pair('USD', reverse_price)
		usd_market = [price for price in usd_market if price['token'] in other_tokens and price['token'] not in all_market_token]
		usd_rate = asyncio.run(usd_to_gbp())
		if not reverse_price:
			usd_rate = 1 / usd_rate
		usd_market = [{ 'token': price['token'], 'price': Decimal(str(price['price'])) * usd_rate, 'last_close': Decimal(str(price['last_close'])) * usd_rate } for price in usd_market]
		return [*market, *usd_market]
