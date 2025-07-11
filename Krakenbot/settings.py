"""
Django settings for Krakenbot project.

Generated by 'django-admin startproject' using Django 3.2.25.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from firebase_admin.credentials import Certificate
from firebase_admin import firestore
from pathlib import Path
import firebase_admin
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/
env_key = os.environ.get('DJANGO_SECRET_KEY')
default_key = 'krakenbotdjangodefaultsecretkeyxeh)n76im*jn%0n185ami6ad*l0nly=vp7ujre^(h=3w*d&99j'
SECRET_KEY = env_key if env_key else default_key

DEBUG = True if os.environ.get('PYTHON_ENV') == 'development' else False

ALLOWED_HOSTS = ['*']

# Firebase Connection
firebase_admin_settings = {
	'type': 'service_account',
	'project_id': os.environ.get('FIREBASE_PROJECT_ID'),
	'private_key_id': os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
	'private_key': '\n'.join((os.environ.get('FIREBASE_PRIVATE_KEY') or '').split(r'\n')),
	'client_email': os.environ.get('FIREBASE_CLIENT_EMAIL'),
	'client_id': os.environ.get('FIREBASE_CLIENT_ID'),
	'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
	'token_uri': 'https://oauth2.googleapis.com/token',
	'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
	'client_x509_cert_url': os.environ.get('FIREBASE_CLIENT_X509_CERT_URL'),
	'universe_domain': 'googleapis.com',
}

if os.environ.get('IMAGE_BUILDING') != 'BUILDING':
	try:
		firebase_admin.initialize_app(Certificate(firebase_admin_settings))
	except ValueError:
		# To catch error raised if private key failed to read when running tests
		from dotenv import load_dotenv, dotenv_values
		load_dotenv()
		firebase_admin_settings['private_key'] = '\n'.join(dotenv_values('.env').get('FIREBASE_PRIVATE_KEY', os.environ.get('FIREBASE_PRIVATE_KEY', '')).split(r'\n'))
		firebase_admin.initialize_app(Certificate(firebase_admin_settings))
	finally:
		firebase = firestore.client()
		db_batch = firebase.batch()

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'rest_framework',
	'corsheaders',
]

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	'corsheaders.middleware.CorsMiddleware',
]

CORS_ALLOWED_ORIGINS = os.environ.get('CORS', 'https://mach-d-rlqsy3.flutterflow.app').split(';')
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = 'Krakenbot.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
			],
		},
	},
]

WSGI_APPLICATION = 'Krakenbot.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

# This is set for test cases
DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': BASE_DIR / 'db.sqlite3',
	}
}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
	{
		'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
	},
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Constants
FIAT = os.environ.get('FIAT', 'GBP')
DEMO_AMOUNT = float(os.environ.get('DEMO_ACCOUNT_AMOUNT', '10000'))
TIMEFRAMES = { timeframe.split('->')[1]: timeframe.split('->')[0] for timeframe in os.environ.get('TIMEFRAME_MAP', 'short->1h;medium->4h;long->1d').split(';') }
HISTORY_INTERVAL = int(os.environ.get('TOKEN_HISTORY_INTERVAL_IN_MINUTES', '60'))
HISTORY_COUNT = int(os.environ.get('MAX_TOKEN_HISTORY_IN_DAYS', '7')) * 24 * 60 // HISTORY_INTERVAL # Multiply into minutes
INTERVAL_MAP = {
	'1min': 1,
	'5min': 5,
	'15min': 15,
	'30min': 30,
	'1h': 60,
	'4h': 240,
	'1d': 1440,
}

GOOGLE_AUTH_EMAIL = 'https://accounts.google.com'
GCLOUD_EMAIL = os.environ.get('GCLOUD_EMAIL')
SERVER_API_URL = os.environ.get('API_URL')

KRAKEN_OHLC_API = 'https://api.kraken.com/0/public/OHLC'
KRAKEN_PAIR_API = 'https://api.kraken.com/0/public/Ticker'
COIN_GECKO_API = 'https://api.coingecko.com/api/v3/coins/markets'

GNEWS_API = 'https://gnews.io/api/v4/search'
GNEWS_API_KEY = os.environ.get('GNEWS_API_KEY')
GNEWS_LANG = 'en'
GNEWS_MAX_FETCH = float(os.environ.get('GNEWS_MAX_FETCH', '10'))
GNEWS_EXPIRY_DAY = float(os.environ.get('NEWS_EXPIRED_IN_DAY', '14'))
GNEWS_FETCH_FROM = float(os.environ.get('FETCH_NEWS_IN_DAY', '7'))
