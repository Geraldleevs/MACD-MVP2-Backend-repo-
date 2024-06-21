from rest_framework.request import Request

SAMPLE_MARKET = [
	{ 'token': 'BTC', 'price': 52746.70 },
	{ 'token': 'BNB', 'price': 472.46 },
	{ 'token': 'SOL', 'price': 117.71 },
	{ 'token': 'ETH', 'price': 2725.45 },
	{ 'token': 'DOGE', 'price': 0.11 },
	{ 'token': 'XRP', 'price': 0.40 },
	{ 'token': 'ADA', 'price': 0.43 },
	{ 'token': 'TON', 'price': 5.21 }
]

class Market:
	def get_market(self, request: Request = { 'query_params': {} }, token_id = None):
		if token_id is None:
			token_id = request.query_params.get('token_id', None)

		if token_id is None or token_id == '':
			return SAMPLE_MARKET

		return [marketToken for marketToken in SAMPLE_MARKET if token_id.upper() == marketToken['token'].upper()]
