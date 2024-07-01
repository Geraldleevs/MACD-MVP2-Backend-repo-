from rest_framework.request import Request
from Krakenbot.models.firebase_token import FirebaseToken
from Krakenbot.models.market import Market
from Krakenbot.utils import authenticate_scheduler_oicd

class UpdateLastClose:
	def update(self, request: Request):
		authenticate_scheduler_oicd(request)
		market = Market()
		market = market.get_market(convert_to=market.DEFAULT_CURRENCY, exclude=market.DEFAULT_CURRENCY)
		firebase_token = FirebaseToken()

		for token in market:
			firebase_token.update_close_price(token['token'], token['last_close'])
