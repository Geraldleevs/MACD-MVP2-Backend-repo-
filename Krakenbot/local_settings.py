from firebase_admin.credentials import Certificate
from firebase_admin import firestore
from dotenv import load_dotenv, dotenv_values
import firebase_admin
import os

load_dotenv()

__firebase_admin_settings = {
	'type': 'service_account',
	'project_id': os.environ.get('FIREBASE_PROJECT_ID'),
	'private_key_id': os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
	'private_key': '\n'.join(dotenv_values('.env').get('FIREBASE_PRIVATE_KEY', os.environ.get('FIREBASE_PRIVATE_KEY', '')).split(r'\n')),
	'client_email': os.environ.get('FIREBASE_CLIENT_EMAIL'),
	'client_id': os.environ.get('FIREBASE_CLIENT_ID'),
	'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
	'token_uri': 'https://oauth2.googleapis.com/token',
	'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
	'client_x509_cert_url': os.environ.get('FIREBASE_CLIENT_X509_CERT_URL'),
	'universe_domain': 'googleapis.com',
}

firebase_admin.initialize_app(Certificate(__firebase_admin_settings))
firebase = firestore.client()
firebase.batch()

class settings:
	firebase = firebase
	db_batch = firebase.batch()

FIAT = os.environ.get('FIAT', 'GBP')
DEMO_AMOUNT = float(os.environ.get('DEMO_ACCOUNT_AMOUNT', '10000'))
TIMEFRAMES = { timeframe.split('->')[1]: timeframe.split('->')[0] for timeframe in os.environ.get('TIMEFRAME_MAP', '').split(';') }
INTERVAL_MAP = {
    '1min': 1,
    '5min': 5,
    '15min': 15,
    '30min': 30,
    '1h': 60,
    '4h': 240,
    '1d': 1440,
}

KRAKEN_OHLC_API = 'https://api.kraken.com/0/public/OHLC'
KRAKEN_PAIR_API = 'https://api.kraken.com/0/public/Ticker'
COIN_GECKO_API = 'https://api.coingecko.com/api/v3/coins/markets'
