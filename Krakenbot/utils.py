import os
import requests
from Krakenbot.exceptions import NotAuthorisedException
from rest_framework.request import Request
from rest_framework.authentication import get_authorization_header

def authenticate_scheduler_oicd(request: Request):
	if os.environ.get('PYTHON_ENV') == 'development':
		return

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
