import json
import os
import sys
import requests
from Krakenbot.exceptions import NotAuthorisedException
from rest_framework.request import Request
from rest_framework.authentication import get_authorization_header

def authenticate_scheduler_oicd(request: Request) -> None:
	'''
	Will only work in production server

	Raises:
		`NotAuthorisedException`: If header is not a valid Google OICD key
	'''
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
				auth['aud'] != os.environ.get('API_URL'):
			raise NotAuthorisedException()

	except Exception:
		raise NotAuthorisedException()


def clean_kraken_pair(kraken_result) -> dict[str, any]:
	'''
	Parse Kraken Pairs into standard token names, (e.g. `XXBT -> BTC` ; `ZGBP -> GBP`)

	Returns:
		The exact dict from `kraken_result['result']`, with cleaned token pairs' name
		`{ 'BTCGBP': Any, 'ETHGBP': Any, 'BTCDOGE': Any, ... }`
	'''

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
	results = {}

	for (pair, result) in kraken_result['result'].items():
		for (clean_pair, replace_with) in KRAKEN_CLEAN_PAIRS:
			if clean_pair in pair:
				pair = pair.replace(clean_pair, replace_with)

		results[pair] = result

	return results


async def usd_to_gbp() -> float:
	'''
	Return USD to GBP Rate
	'''
	KRAKEN_API = 'https://api.kraken.com/0/public/Ticker'
	result = requests.get(KRAKEN_API, { 'pair': 'GBPUSD' }).json()

	if len(result['error']) > 0:
		return 0

	try:
		return 1 / float(result['result']['ZGBPZUSD']['c'][0])
	except (KeyError, ValueError):
		return 0


def log_warning(message):
	'''
	Google Cloud Log Warning
	'''
	log(message, 'WARNING')


def log_error(message):
	'''
	Google Cloud Log Error
	'''
	log(message, 'ERROR')


def log(message, severity = 'INFO'):
	'''
	Google Cloud Log
	'''
	entry = {
			'severity': severity,
			'message': message,
			'component': 'arbitrary-property'
	}

	print(json.dumps(entry))
	sys.stdout.flush()
