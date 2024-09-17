from datetime import datetime, timedelta
from pandas import DataFrame
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import CollectionReference, DocumentReference
import pytz

try:
	from Krakenbot import settings
except ModuleNotFoundError:
	from local_settings import settings

class FirebaseCandle:
	__candle_token: DocumentReference = None
	__candle_data: CollectionReference = None

	def __init__(self, token_pair = None, timeframe = None, timestamp_column = 'Unix_Timestamp'):
		self.__timestamp_column = timestamp_column
		self.__db_batch = settings.db_batch
		self.__candle = settings.firebase.collection(u'candle')

		if token_pair is not None and timeframe is not None:
			self.change_pair(token_pair, timeframe)

	def change_pair(self, token_pair, timeframe):
		self.__candle_token = self.__candle.document(token_pair)
		self.__candle_data = self.__candle_token.collection(timeframe)

	def __combine_existing(self, ref: DocumentReference, commit_array: list, overwrite: bool):
		if ref.get().exists:
			existing = ref.get().to_dict()['candles']
			if overwrite:
				committing_timestamp = [candle[self.__timestamp_column] for candle in commit_array]
				commit_array = [*commit_array, *[candle for candle in existing if candle[self.__timestamp_column] not in committing_timestamp]]
			else:
				existing_timestamp = [candle[self.__timestamp_column] for candle in existing]

				no_new_data = len([candle for candle in commit_array if candle[self.__timestamp_column] not in existing_timestamp]) == 0
				if no_new_data:
					return False

				commit_array = [*existing, *[candle for candle in commit_array if candle[self.__timestamp_column] not in existing_timestamp]]

			commit_array.sort(key=lambda x: x[self.__timestamp_column])
		return commit_array

	def __set_data(self, today, overwrite, commit_array):
		batch = self.__db_batch
		cur_date = datetime.fromtimestamp(today, tz=pytz.UTC)
		ref = self.__candle_data.document(str(int(today)))
		commit_array = self.__combine_existing(ref, commit_array, overwrite)

		# If old data is already having the whole day's data, do not need to update
		if commit_array != False:
			batch.set(ref, { 'date': cur_date, 'candles': commit_array })

	def save(self, data: DataFrame, overwrite = True, batch_save = True):
		'''
		Use `batch_save = False` if the dataframe is too big to upload at once, firebase limit 11534336 bytes
		'''
		if self.__candle_token is None or self.__candle_data is None:
			return

		batch = self.__db_batch
		data = data.sort_values(self.__timestamp_column)
		records = data.to_dict('records')

		first_date = datetime.fromtimestamp(records[0][self.__timestamp_column], tz=pytz.UTC)
		today = datetime(first_date.year, first_date.month, first_date.day, tzinfo=pytz.UTC)
		tomorrow = today + timedelta(days=1)
		today = today.timestamp()
		tomorrow = tomorrow.timestamp()
		one_day_timestamp = tomorrow - today

		commit_array = []
		for candle in records:
			if today <= candle[self.__timestamp_column] < tomorrow:
				commit_array.append(candle)
				continue

			self.__set_data(today, overwrite, commit_array)
			commit_array = [candle]
			today = tomorrow
			tomorrow += one_day_timestamp

			if not batch_save:
				batch.commit()

		# Handle leftovers
		if len(commit_array) > 0:
			self.__set_data(today, overwrite, commit_array)

		batch.commit()

	def remove_older_than(self, date: datetime | None = None, inclusive = False):
		if self.__candle_token is None or self.__candle_data is None:
			return

		query = self.__candle_data
		operator = '<=' if inclusive else '<'

		if date is not None:
			query = query.where(filter=FieldFilter('date', operator, date))
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

		query = self.__candle_data.order_by('date').get()
		data = [record.to_dict() for record in query]
		return_data = [candle for day in data for candle in day['candles']]
		return DataFrame(return_data)

	def fetch_last(self, count = 1):
		'''Return `[ ]` if no candle is chosen'''
		if self.__candle_token is None or self.__candle_data is None:
			return []

		query = self.__candle_data.order_by('date').limit_to_last(count).get()
		data = [record.to_dict() for record in query]
		return_data = [candle for day in data for candle in day['candles']]
		return return_data[-count:]

	def fetch_cur_token(self):
		return self.__candle_token.get().to_dict().get('token_id', None)

	def fetch_pairs(self):
		docs = self.__candle.stream()
		return [doc.id for doc in docs]
