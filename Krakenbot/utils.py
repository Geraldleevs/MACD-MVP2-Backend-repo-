from typing import Literal
from decimal import ROUND_DOWN, Decimal
import json
import requests
import sys

import firebase_admin.auth
from rest_framework.authentication import get_authorization_header
from rest_framework.request import Request

try:
	from Krakenbot import settings
	from Krakenbot.exceptions import InvalidCalculationException, NotAuthorisedException
except ModuleNotFoundError:
	from exceptions import InvalidCalculationException, NotAuthorisedException
	from local_settings import settings


def authenticate_user_jwt(request: Request, req_type: Literal['get', 'post'] = 'post') -> str:
	'''
	Will only work in production server

	Returns:
		uid: User ID from request

	Raises:
		NotAuthorisedException: UID or JWT is invalid
	'''
	if req_type == 'post':
		uid = request.data.get('uid')
	else:
		uid = request.query_params.get('uid')

	if settings.DEBUG:
		return uid

	jwt_token = get_authorization_header(request).decode('utf-8').split(' ')

	try:
		if uid != firebase_admin.auth.verify_id_token(jwt_token[1])['uid']:
			raise NotAuthorisedException()
	except Exception:
		raise NotAuthorisedException()

	return uid


def authenticate_scheduler_oicd(request: Request) -> None:
	'''
	Will only work in production server

	Raises:
		NotAuthorisedException: If header is not a valid Google OICD key
	'''
	if settings.DEBUG:
		return

	try:
		token = get_authorization_header(request).decode('utf-8').split(' ')

		if len(token) < 2:
			raise NotAuthorisedException()

		auth = requests.get('https://oauth2.googleapis.com/tokeninfo', params={'id_token': token[1]}).json()

		if 'error' in auth.keys() or \
				auth['iss'] != settings.GOOGLE_AUTH_EMAIL or \
				auth['email'] != settings.GCLOUD_EMAIL or \
				auth['aud'] != settings.SERVER_API_URL:
			raise NotAuthorisedException()

	except Exception:
		raise NotAuthorisedException()


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


def clean_kraken_pair(kraken_result) -> dict[str, any]:
	'''
	Parse Kraken Pairs into standard token names, (e.g. `XXBT -> BTC` ; `ZGBP -> GBP`)

	Returns:
		kraken_result:
		`kraken_result['result']`, with cleaned token pairs' name
		`{ 'BTCGBP': Any, 'ETHGBP': Any, 'BTCDOGE': Any, ... }`
	'''
	results = {}

	for (pair, result) in kraken_result['result'].items():
		for (clean_pair, replace_with) in KRAKEN_CLEAN_PAIRS:
			if clean_pair in pair:
				pair = pair.replace(clean_pair, replace_with)

		results[pair] = result

	return results


async def usd_to_gbp() -> float:
	''' Return USD to GBP Rate '''
	result = requests.get(settings.KRAKEN_PAIR_API, { 'pair': 'GBPUSD' }).json()

	if len(result['error']) > 0:
		return 0

	try:
		return acc_calc(1, '/', result['result']['ZGBPZUSD']['c'][0])
	except (KeyError, ValueError):
		return 0


def acc_calc(
		num1: str | float | int | Decimal,
		op: Literal['+', '-', '*', '/', '%', '//',
								'==', '!=', '>', '>=', '<', '<='],
		num2: str | float | int | Decimal,
		decimal_count = 18
	) -> Decimal:
	'''
	Performs calculations with Float128 type with higher precision.
	Accepts `str`, `float`, `int`, `Decimal` types
	Returns:
		result:
		Result of calculation in decimal type
	'''

	full_decimal = 18
	full_decimal_places = '.' + '0' * (full_decimal - 1) + '1'
	full_decimal_places = Decimal(full_decimal_places)

	if decimal_count is None:
		decimal_count = full_decimal
	elif decimal_count < 0:
		raise InvalidCalculationException()
	decimal_places = '.' + '0' * (decimal_count - 1) + '1'
	decimal_places = Decimal(decimal_places)

	if num1 is None:
		num1 = 0
	if num2 is None:
		num2 = 0

	try:
		num1 = Decimal(str(num1))
		num2 = Decimal(str(num2))
	except Exception:
		raise InvalidCalculationException()

	match(op):
		case '+':
			result = num1 + num2

		case '-':
			result = num1 - num2

		case '*':
			result = num1 * num2

		case '/':
			result = num1 / num2

		case '%':
			result = num1 % num2

		case '//':
			result = num1 // num2

		case '==':
			return num1 == num2

		case '!=':
			return num1 != num2

		case '>':
			return num1 > num2

		case '>=':
			return num1 >= num2

		case '<':
			return num1 < num2

		case '<=':
			return num1 <= num2

		case _:
			raise InvalidCalculationException()

	result = result.quantize(decimal_places, rounding=ROUND_DOWN)
	return result


def log_warning(message):
	''' Google Cloud Log Warning '''
	log(message, 'WARNING')


def log_error(message):
	''' Google Cloud Log Error '''
	log(message, 'ERROR')


def log(message, severity = 'INFO'):
	''' Google Cloud Log '''
	entry = {
			'severity': severity,
			'message': message,
			'component': 'arbitrary-property'
	}

	print(json.dumps(entry))
	sys.stdout.flush()
