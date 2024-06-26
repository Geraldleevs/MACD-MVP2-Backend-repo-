from Krakenbot.MVP_Backtest import main as backtest
from Krakenbot.models.firebase_recommendation import FirebaseRecommendation
from django.utils import timezone
from rest_framework.request import Request

from Krakenbot.utils import authenticate_scheduler_oicd

class BackTest:
	def backtest(self, request: Request):
		authenticate_scheduler_oicd(request)
		results = backtest().reset_index().to_numpy()
		now = timezone.now()
		results = [{
			'token_id': value[0].split(' | ')[0],
			'timeframe': value[0].split(' | ')[1],
			'strategy': value[1],
			'profit': value[2],
			'profit_percent': value[3],
			'summary': 'Summary',
			'strategy_description': 'Strategy Description',
			'updated_on': now
		} for value in results]

		firebase = FirebaseRecommendation()
		for result in results:
			firebase.upsert(result)
