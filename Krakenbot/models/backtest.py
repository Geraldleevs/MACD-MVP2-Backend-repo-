import os
import requests
from Krakenbot.MVP_Backtest import main as backtest
from Krakenbot.exceptions import NotAuthorisedException
from Krakenbot.models.firebase_recommendation import FirebaseRecommendation
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.authentication import get_authorization_header

class BackTest:
	def authorise(self, request: Request):
		token = get_authorization_header(request).decode('utf-8').split(' ')

		if len(token) < 2:
			raise NotAuthorisedException()

		try:
			auth = requests.get('https://oauth2.googleapis.com/tokeninfo', params={'id_token': token[1]}).json()

			if 'error' in auth.keys():
				raise NotAuthorisedException()

			if auth['iss'] != 'https://accounts.google.com' or \
					auth['email'] != os.environ.get('GCLOUD_EMAIL') or \
					auth['aud'] != os.environ.get('API_URL') + '/api/backtest':
				raise NotAuthorisedException()

		except Exception:
			raise NotAuthorisedException()

	def backtest(self, request: Request):
		if os.environ.get('PYTHON_ENV') != 'development':
			self.authorise(request)

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
