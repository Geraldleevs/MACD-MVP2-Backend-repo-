SAMPLE_MARKET = [
	{ 'token': 'BTC', 'price': 52746.70 },
	{ 'token': 'BNB', 'price': 472.46 },
	{ 'token': 'SOL', 'price': 117.71 },
	{ 'token': 'ETH', 'price': 2725.45 },
	{ 'token': 'DOGE', 'price': 0.11 }
]

class Market:
	def __init__(self, token_id = ''):
		self.token_id = token_id

	def get_market(self):
		result = [marketToken for marketToken in SAMPLE_MARKET if self.token_id in marketToken['token']]
		return result
