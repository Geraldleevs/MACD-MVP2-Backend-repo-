from datetime import datetime
from pandas import DataFrame
from Krakenbot import settings
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import CollectionReference, DocumentReference
from django.utils import timezone

class FirebaseCandle:
	__candle_token: DocumentReference
	__candle_data: CollectionReference

	def __init__(self, token_pair, timeframe, timestamp_column = 'Unix_Timestamp'):
		self.__timestamp_column = timestamp_column
		self.change_pair(token_pair, timeframe)

	def change_pair(self, token_pair, timeframe):
		self.__candle_token = settings.firebase.collection(u'candle').document(token_pair)
		self.__candle_data = self.__candle_token.collection(timeframe)

	def save(self, data: DataFrame):
		batch = settings.db_batch
		data['time'] = data[self.__timestamp_column].apply(timezone.datetime.fromtimestamp)
		records = data.to_dict('records')

		for candle in records:
			ref = self.__candle_data.document(str(candle[self.__timestamp_column]))
			batch.set(ref, candle)

		batch.commit()

	def save_single(self, data: DataFrame, index = -1):
		'''
		Default saving the last record
		'''

		records = data.to_dict('records')
		record = records[index]
		record['time'] = timezone.datetime.fromtimestamp(record[self.__timestamp_column])
		self.__candle_data.document(str(record[self.__timestamp_column])).set(record)

	def remove_oldest(self):
		oldest = self.__candle_data.order_by(self.__timestamp_column).limit(1).get()[0]
		oldest.reference.delete()

	def remove_older_than(self, timestamp: int = None, time: datetime = None, inclusive = False):
		'''
		Specify time or timestamp, but not both.

		If both given, timestamp will be used.

		If both not provided, nothing happen.
		'''

		query = self.__candle_data
		operator = '<=' if inclusive else '<'

		if timestamp is not None:
			query = query.where(filter=FieldFilter(self.__timestamp_column, operator, timestamp))
		elif time is not None:
			query = query.where(filter=FieldFilter('time', operator, time))
		else:
			return

		docs = query.get()
		batch = settings.db_batch

		for doc in docs:
			batch.delete(doc.reference)

		batch.commit()

	def fetch_all(self):
		query = self.__candle_data.order_by(self.__timestamp_column).get()
		data = [record.to_dict() for record in query]
		return DataFrame(data)

	def fetch_last(self, count = 1):
		query = self.__candle_data.order_by(self.__timestamp_column).limit_to_last(count).get()
		data = [record.to_dict() for record in query]
		return DataFrame(data)
