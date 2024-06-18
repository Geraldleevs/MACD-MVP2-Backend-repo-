import os
import requests
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import get_authorization_header
from Krakenbot.models.backtest import BackTest
from Krakenbot.models.market import Market


class MarketView(APIView):
	def get(self, request: Request):
		token_id = request.query_params.get('token_id', '').upper()
		result = Market(token_id).get_market()
		return Response(result, 200)


class BackTestView(APIView):
	def post(self, request: Request):
		if os.environ.get('PYTHON_ENV') == 'development':
			result = BackTest().backtest()
			return Response(result, status=200)
		else:
			token = get_authorization_header(request).decode('utf-8').split(' ')
			if len(token) < 2:
				return Response(status=401)
			auth = requests.get('https://oauth2.googleapis.com/tokeninfo', params={'id_token': token[1]}).json()
			if 'error' in auth.keys():
				return Response(status=401)
			if auth['iss'] == 'https://accounts.google.com' and \
					auth['email'] == os.environ.get('GCLOUD_EMAIL') and \
					auth['aud'] == os.environ.get('API_URL') + '/api/backtest':
				result = BackTest().backtest()
				return Response(result, status=200)
