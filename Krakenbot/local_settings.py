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
