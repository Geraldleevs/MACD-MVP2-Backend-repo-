from rest_framework.request import Request
from Krakenbot.exceptions import BadRequestException
from Krakenbot.models.firebase_token import FirebaseToken
import requests

class Market:
	KRAKEN_PAIR_API = 'https://api.kraken.com/0/public/Ticker'
	DEFAULT_CURRENCY = 'GBP'
	KRAKEN_CLEAN_PAIRS = [
		('XETC', 'ETC'),
		('XETH', 'ETH'),
		('XLTC', 'LTC'),
		('XMLN', 'MLN'),
		('XREP', 'REP'),
		('XXBT', 'BTC'),
		('XBT', 'BTC'),
		('XXDG', 'XDG'),
		('XXLM', 'XLM'),
		('XXMR', 'XMR'),
		('XXRP', 'XRP'),
		('XZEC', 'ZEC'),
		('ZAUD', 'AUD'),
		('ZEUR', 'EUR'),
		('ZGBP', 'GBP'),
		('ZUSD', 'USD'),
		('ZCAD', 'CAD'),
		('ZJPY', 'JPY')
	]

	def fetch_kraken_pair(self, token, reverse_price = False):
		result = requests.get(self.KRAKEN_PAIR_API).json()

		if len(result['error']) > 0:
			return []

		result = self.clean_kraken_pair(result)
		result = self.parse_kraken_pair(result, token, reverse_price)
		return result

	def clean_kraken_pair(self, kraken_result):
		results = {}

		for (pair, result) in kraken_result['result'].items():
			for (clean_pair, replace_with) in self.KRAKEN_CLEAN_PAIRS:
				if clean_pair in pair:
					pair = pair.replace(clean_pair, replace_with)

			results[pair] = {'ask': result['a'], 'bid': result['b']}

		return results

	def parse_kraken_pair(self, kraken_result, token, reverse_price):
		def get_price(result, property_path):
			price = float(result[property_path][0])
			if property_path == 'bid' and price > 0:
				price = 1 / price
			return price

		sell = 'bid' if reverse_price else 'ask'
		buy = 'ask' if reverse_price else 'bid'
		filtered_results = {}

		for (pair, result) in kraken_result.items():
			if (token is not None and token in pair):
				filtered_results[pair] = result

		results = {}
		for (pair, result) in filtered_results.items():
			if pair.startswith(token):
				price = get_price(result, sell)
			elif pair.endswith(token):
				price = get_price(result, buy)

			result_token = pair.replace(token, '')

			if result_token not in results:
				results[result_token] = price

		return [{ 'token': token, 'price': price } for (token, price) in results.items()]

	def get_market(self, request: Request = { 'query_params': {} }, convert_from = None, convert_to = None):
		if convert_from is None:
			convert_from = request.query_params.get('convert_from', '').upper()

		if convert_to is None:
			convert_to = request.query_params.get('convert_to', '').upper()

		if convert_from == '' and convert_to == '':
			raise BadRequestException()

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

		market = self.fetch_kraken_pair(current_token, reverse_price)
		if not reverse_price and convert_to != '':
			market = [price for price in market if price['token'] == convert_to]
		else:
			other_tokens = firebase_token.all()
			other_tokens = [token['token_id'] for token in other_tokens]
			market = [price for price in market if price['token'] in other_tokens]

		return market
