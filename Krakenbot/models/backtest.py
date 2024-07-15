import os
from Krakenbot.MVP_Backtest import main as backtest
from Krakenbot.models.firebase_analysis import FirebaseAnalysis
from Krakenbot.models.firebase_recommendation import FirebaseRecommendation
from django.utils import timezone
from rest_framework.request import Request

from Krakenbot.utils import authenticate_scheduler_oicd

class BackTest:
	def __init__(self):
		timeframes = os.environ.get('TIMEFRAME_MAP', '').split(';')
		self.TIMEFRAMES = { timeframe.split('->')[1]: timeframe.split('->')[0] for timeframe in timeframes }

	def backtest(self, request: Request):
		authenticate_scheduler_oicd(request)
		firebase_analysis = FirebaseAnalysis()
		results = backtest().reset_index().to_numpy()
		now = timezone.now()
		results = [{
			'token_id': value[0].split(' | ')[0],
			'timeframe': value[0].split(' | ')[1],
			'strategy': value[1],
			'profit': value[2],
			'profit_percent': value[3],
			'risk': firebase_analysis.get_risk(value[0].split(' | ')[0], self.TIMEFRAMES[value[0].split(' | ')[1]]),
			'summary': firebase_analysis.get_description(value[0].split(' | ')[0], self.TIMEFRAMES[value[0].split(' | ')[1]]),
			'strategy_description': firebase_analysis.fetch_strategy_description(),
			'updated_on': now
		} for value in results]

		firebase = FirebaseRecommendation()
		for result in results:
			firebase.upsert(result)
