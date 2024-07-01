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
		('XDG', 'DOGE'),
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

	def __fetch_kraken_pair(self, token, reverse_price = False):
		result = requests.get(self.KRAKEN_PAIR_API).json()

		if len(result['error']) > 0:
			return []

		result = self.__clean_kraken_pair(result)
		result = self.__parse_kraken_pair(result, token, reverse_price)
		return result

	def __clean_kraken_pair(self, kraken_result):
		results = {}

		for (pair, result) in kraken_result['result'].items():
			for (clean_pair, replace_with) in self.KRAKEN_CLEAN_PAIRS:
				if clean_pair in pair:
					pair = pair.replace(clean_pair, replace_with)

			results[pair] = {'ask': result['a'], 'bid': result['b'], 'last_close': result['o']}

		return results

	def __get_price(self, result, property_path):
		price = float(result[property_path][0])
		last_open = float(result['last_close'])
		if property_path == 'bid' and price > 0:
			last_open = 1 / last_open
			price = 1 / price
		return (price, last_open)

	def __parse_kraken_pair(self, kraken_result, token, reverse_price):
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

	def get_market(self, request: Request = None, convert_from = '', convert_to = '', exclude = ''):
		if request is not None:
			convert_from = request.query_params.get('convert_from', '').upper()
			convert_to = request.query_params.get('convert_to', '').upper()
			exclude = request.query_params.get('exclude', '').upper()
		else:
			convert_from = convert_from.upper()
			convert_to = convert_to.upper()
			exclude = exclude.upper()

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

		market = self.__fetch_kraken_pair(current_token, reverse_price)
		market.append({ 'token': current_token, 'price': 1 })

		if not reverse_price and convert_to != '':
			market = [price for price in market if price['token'] == convert_to]
		else:
			other_tokens = firebase_token.all()
			other_tokens = [token['token_id'] for token in other_tokens]
			market = [price for price in market if price['token'] in other_tokens]

		if exclude != '':
			market = [price for price in market if price['token'] != exclude]

		return market
