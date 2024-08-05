from datetime import datetime
from pandas import DataFrame
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import CollectionReference, DocumentReference
from firebase_admin.credentials import Certificate
from firebase_admin import firestore
from dotenv import load_dotenv, dotenv_values
import firebase_admin
import os
import pytz

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

class LocalFirebaseCandle:
	__candle_token: DocumentReference = None
	__candle_data: CollectionReference = None

	def __init__(self, token_pair = None, timeframe = None, timestamp_column = 'Unix_Timestamp'):
		self.tzinfo = pytz.timezone('Europe/London').localize(datetime.now()).tzinfo

		self.__timestamp_column = timestamp_column
		self.__db_batch = firebase.batch()
		self.__candle = firebase.collection(u'candle')

		if token_pair is not None and timeframe is not None:
			self.change_pair(token_pair, timeframe)

	def change_pair(self, token_pair, timeframe):
		self.__candle_token = self.__candle.document(token_pair)
		self.__candle_data = self.__candle_token.collection(timeframe)

	def save(self, data: DataFrame):
		if self.__candle_token is None or self.__candle_data is None:
			return

		batch = self.__db_batch
		data['time'] = data[self.__timestamp_column].apply(lambda timestamp: datetime.fromtimestamp(timestamp, tz=self.tzinfo))
		records = data.to_dict('records')
		count = 0
		split_save = 10000

		for candle in records:
			ref = self.__candle_data.document(str(candle[self.__timestamp_column]))
			batch.set(ref, candle)

			# If too many, split committing
			count += 1
			if count >= split_save:
				print('Committing 10,000 Documents')
				batch.commit()
				count = 0

		batch.commit()

	def remove_older_than(self, timestamp: int | None = None, time: datetime | None = None, inclusive = False):
		'''
		Specify time or timestamp, but not both.

		If both given, timestamp will be used.

		If both not provided, nothing happen.
		'''

		if self.__candle_token is None or self.__candle_data is None:
			return

		query = self.__candle_data
		operator = '<=' if inclusive else '<'

		if timestamp is not None:
			query = query.where(filter=FieldFilter(self.__timestamp_column, operator, timestamp))
		elif time is not None:
			query = query.where(filter=FieldFilter('time', operator, time))
		else:
			return

		docs = query.get()
		batch = self.__db_batch

		for doc in docs:
			batch.delete(doc.reference)

		batch.commit()

	def fetch_all(self):
		if self.__candle_token is None or self.__candle_data is None:
			return

		query = self.__candle_data.order_by(self.__timestamp_column).get()
		data = [record.to_dict() for record in query]
		return DataFrame(data)

	def fetch_last(self, count = 1):
		'''Return `[ ]` if no candle is chosen'''
		if self.__candle_token is None or self.__candle_data is None:
			return []

		query = self.__candle_data.order_by(self.__timestamp_column).limit_to_last(count).get()
		return [record.to_dict() for record in query]

	def fetch_cur_token(self):
		return self.__candle_token.get().to_dict().get('token_id', None)

	def fetch_pairs(self):
		docs = self.__candle.stream()
		return [doc.id for doc in docs]
