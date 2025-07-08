import math
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Literal

import numpy as np
import pytz
from django.conf import settings
from django.utils import timezone
from google.cloud.firestore_v1 import Client, CollectionReference, DocumentReference, WriteBatch
from google.cloud.firestore_v1.base_query import FieldFilter
from pandas import DataFrame

from core.calculations import calculate
from core.exceptions import NotEnoughTokenException

FIREBASE: Client = settings.FIREBASE
DB_BATCH: WriteBatch = settings.DB_BATCH
INTERVAL_MAP: dict[str, int] = settings.INTERVAL_MAP


class Platform(Enum):
	BINANCE = 'binance'


class FirebaseCandle:
	MAX_UPLOAD_LIMIT = 50000
	TIMESTAMP_NS_THRES = 100000000000000
	TIMESTAMP_MS_THRES = 100000000000
	TABLE_NAME = 'Candle'
	__candle_token: DocumentReference = None
	__candle_data: CollectionReference = None
	__record_per_day: int = None

	def __init__(self, token_pair=None, timeframe=None, platform=None):
		self.__timestamp_column = 'Open Time'
		self.__db_batch = DB_BATCH
		self.__candle = FIREBASE.collection(self.TABLE_NAME)

		if None not in [token_pair, timeframe, platform]:
			self.change_pair(token_pair, timeframe, platform)

	def change_pair(self, token_pair: str, timeframe: str, platform: Platform):
		if isinstance(platform, Platform):
			platform = platform.value
		self.__candle_token = self.__candle.document(token_pair)
		self.__candle_data = self.__candle_token.collection(f'{platform}_{timeframe}')
		self.__record_per_day = 24 * 60 / INTERVAL_MAP[timeframe]

	def __combine_existing(self, ref: DocumentReference, commit_array: list, overwrite: bool, all_docs: list[str]):
		time_col = self.__timestamp_column

		if ref.id in all_docs:
			existing = ref.get().to_dict()['candles']
			if overwrite:
				committing_timestamp = [candle[time_col] for candle in commit_array]
				commit_array = [
					*commit_array,
					*[candle for candle in existing if candle[time_col] not in committing_timestamp],
				]
			else:
				existing_timestamp = [candle[time_col] for candle in existing]

				no_new_data = len([c for c in commit_array if c[time_col] not in existing_timestamp]) == 0
				if no_new_data:
					return False

				commit_array = [
					*existing,
					*[candle for candle in commit_array if candle[time_col] not in existing_timestamp],
				]

			commit_array.sort(key=lambda x: x[time_col])
		return commit_array

	def __set_data(self, today: int, overwrite: bool, commit_array: list[dict], all_docs: list[str]):
		batch = self.__db_batch
		cur_date = datetime.fromtimestamp(today, tz=pytz.UTC)
		ref = self.__candle_data.document(str(int(today)))
		commit_array = self.__combine_existing(ref, commit_array, overwrite, all_docs)

		# If old data is already having the whole day's data, do not need to update
		if commit_array is not False:
			batch.set(ref, {'date': cur_date, 'candles': commit_array})

	def save(self, token_id: str, from_token: str, to_token: str):
		self.__candle_token.set({'token_id': token_id, 'from_token': from_token, 'to_token': to_token})

	def save_ohlc(self, data: DataFrame, overwrite=True, batch_save=True):
		"""
		Use `batch_save = False` if the dataframe is too big to upload at once, firebase limit 11534336 bytes
		"""

		if self.__candle_token is None or self.__candle_data is None:
			return

		assert data.columns.to_list() == ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume']

		batch = self.__db_batch
		data = data.sort_values(self.__timestamp_column)
		timestamp_in_ms = False

		first_timestamp = data[self.__timestamp_column].iloc[0]
		last_timestamp = data[self.__timestamp_column].iloc[-1]
		if first_timestamp > self.TIMESTAMP_MS_THRES:
			timestamp_in_ms = True
			first_timestamp = int(first_timestamp / 1000)
			last_timestamp = int(last_timestamp / 1000)
		else:
			data[self.__timestamp_column] = data[self.__timestamp_column] * 1000

		first_date = datetime.fromtimestamp(first_timestamp, tz=pytz.UTC)
		today = datetime(first_date.year, first_date.month, first_date.day, tzinfo=pytz.UTC)
		today_timestamp = int(today.timestamp())
		one_day_timestamp = int(timedelta(days=1).total_seconds())

		last_date = datetime.fromtimestamp(last_timestamp, tz=pytz.UTC)
		query = self.__candle_data.where(filter=FieldFilter('date', '>=', today))
		query = query.where(filter=FieldFilter('date', '<', last_date))
		all_docs = [doc.id for doc in query.stream()]

		for timestamp in range(today_timestamp, last_timestamp, one_day_timestamp):
			tomorrow = timestamp + one_day_timestamp
			if timestamp_in_ms:
				filter_query = data[self.__timestamp_column] >= timestamp * 1000
				filter_query = filter_query & (data[self.__timestamp_column] < (tomorrow * 1000))
			else:
				filter_query = data[self.__timestamp_column] >= timestamp
				filter_query = filter_query & (data[self.__timestamp_column] < tomorrow)

			commit_array = data[filter_query].to_dict('records')
			self.__set_data(timestamp, overwrite, commit_array, all_docs)

			if not batch_save:
				batch.commit()

		batch.commit()

	def remove_older_than(self, date: datetime | None = None, inclusive=False):
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

	def fetch_last(self, count=1):
		"""Return `[ ]` if no candle is chosen"""
		if self.__candle_token is None or self.__candle_data is None:
			return []

		days = math.ceil(count / self.__record_per_day) + 1
		query = self.__candle_data.order_by('date').limit_to_last(days).get()
		data = [record.to_dict() for record in query]
		return_data = [candle for day in data for candle in day['candles']]
		return return_data[-count:]

	def fetch_first(self, count=1):
		"""Return `[ ]` if no candle is chosen"""
		if self.__candle_token is None or self.__candle_data is None:
			return []

		days = math.ceil(count / self.__record_per_day) + 1
		query = self.__candle_data.order_by('date').limit(days).get()
		data = [record.to_dict() for record in query]
		return_data = [candle for day in data for candle in day['candles']]
		return return_data[-count:]

	def fetch_all(self):
		if self.__candle_token is None or self.__candle_data is None:
			return

		query = self.__candle_data.order_by('date').get()
		data = [record.to_dict() for record in query]
		return_data = [candle for day in data for candle in day['candles']]
		return DataFrame(return_data)

	def fetch(self, start_date: datetime = None, end_date: datetime = None):
		"""Return `[ ]` if no candle is chosen"""
		if self.__candle_token is None or self.__candle_data is None:
			return []

		query = self.__candle_data.order_by('date')

		start_timestamp = None
		if start_date is not None:
			before_start = start_date - timedelta(days=1)
			start_timestamp = int(start_date.timestamp())
			query = query.where(filter=FieldFilter('date', '>=', before_start))

		end_timestamp = None
		if end_date is not None:
			after_end = end_date + timedelta(days=1)
			end_timestamp = int(end_date.timestamp())
			query = query.where(filter=FieldFilter('date', '<=', after_end))

		data = DataFrame([candle for record in query.stream() for candle in record.to_dict()['candles']])

		first_timestamp = data[self.__timestamp_column].iloc[0]
		if first_timestamp > self.TIMESTAMP_MS_THRES:
			if start_timestamp is not None:
				start_timestamp *= 1000
			if end_timestamp is not None:
				end_timestamp *= 1000

		query = np.repeat(True, len(data))
		if start_timestamp is not None:
			query = query & data[self.__timestamp_column] >= start_timestamp
		if end_timestamp is not None:
			query = query & data[self.__timestamp_column] < end_timestamp

		return_data = data[query].replace(np.nan, None).to_dict('records')
		return return_data

	def fetch_cur_token(self):
		return self.__candle_token.get().to_dict()

	def fetch_pairs(self):
		docs = self.__candle.stream()
		return [doc.to_dict() for doc in docs]

	def fetch_pair(self, token_id: str):
		doc = self.__candle.where(filter=FieldFilter('token_id', '==', token_id)).limit(1).get()[0]
		return doc.to_dict()


class FirebaseOrderBook:
	ORDER_BOOK_TABLE = 'OrderBook'
	__OPEN_STATUS = 'OPEN'
	__COMPLETED_STATUS = 'COMPLETED'
	__CANCELLED_STATUS = 'CANCELLED'

	def __init__(self):
		self.__order_book = FIREBASE.collection(self.ORDER_BOOK_TABLE)

	def create_order(self, uid, from_token, to_token, price, volume):
		FirebaseWallet(uid).hold_token_for_order(from_token, volume)

		new_order = {
			'uid': uid,
			'from_token': from_token,
			'to_token': to_token,
			'price': str(price),
			'volume': str(volume),
			'created_time': timezone.now(),
			'closed_time': None,
			'status': self.__OPEN_STATUS,
		}

		doc_ref: DocumentReference = self.__order_book.document()
		doc_ref.set(new_order)
		doc_ref.update({'order_id': doc_ref.id})

		return {'id': doc_ref.id, **doc_ref.get().to_dict()}

	def cancel_order(self, id):
		doc_ref: DocumentReference = self.__order_book.document(id)
		doc = doc_ref.get()

		if not doc.exists or doc.to_dict().get('status') != self.__OPEN_STATUS:
			raise ValueError('Order is not open!')

		order_data = doc.to_dict()
		FirebaseWallet(order_data['uid']).release_token_hold(order_data['from_token'], order_data['volume'])

		update_data = {
			'closed_time': timezone.now(),
			'status': self.__CANCELLED_STATUS,
		}
		doc_ref.update(update_data)
		return {**doc_ref.get().to_dict(), 'id': doc_ref.id}

	def complete_order(self, id):
		doc_ref: DocumentReference = self.__order_book.document(id)
		doc = doc_ref.get()

		if not doc.exists or doc.to_dict().get('status') != self.__OPEN_STATUS:
			raise ValueError('Order is not open!')

		order_data = doc.to_dict()
		uid = order_data['uid']
		from_token = order_data['from_token']
		from_amount = order_data['volume']
		to_token = order_data['to_token']
		to_amount = calculate(from_amount, '*', order_data['price'])
		transaction = FirebaseWallet(uid).complete_order(from_token, from_amount, to_token, to_amount)

		update_data = {
			'closed_time': timezone.now(),
			'status': self.__COMPLETED_STATUS,
			'transaction_id': transaction['id'],
		}
		doc_ref.update(update_data)
		return {**doc_ref.get().to_dict(), 'id': doc_ref.id}

	def delete_by_id(self, id):
		doc: DocumentReference = self.__order_book.document(id)
		doc.delete()

	def filter(
		self,
		since: datetime = None,
		before: datetime = None,
		status: Literal['OPEN', 'CANCELLED', 'CLOSED', 'ALL'] = 'ALL',
		uid: str = None,
	):
		query = self.__order_book

		match status:
			case 'OPEN':
				query = query.where(filter=FieldFilter('status', '==', self.__OPEN_STATUS))

			case 'CANCELLED':
				query = query.where(filter=FieldFilter('status', '==', self.__CANCELLED_STATUS))

			case 'CLOSED':
				query = query.where(filter=FieldFilter('status', '==', self.__COMPLETED_STATUS))

		if since is not None:
			query = query.where(filter=FieldFilter('created_time', '>=', since))

		if before is not None:
			query = query.where(filter=FieldFilter('created_time', '<=', before))

		if uid is not None:
			query = query.where(filter=FieldFilter('uid', '==', uid))

		query = query.order_by('created_time')
		docs = query.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def get(self, id):
		doc_ref: DocumentReference = self.__order_book.document(id)
		doc = doc_ref.get()
		return {**doc.to_dict(), 'id': doc.id}

	def has(self, id):
		doc_ref: DocumentReference = self.__order_book.document(id)
		return doc_ref.get().exists


class FirebaseWallet:
	USER_TABLE = 'User'
	WALLET_TABLE = 'wallet'
	TRANSACTION_TABLE = 'transaction'
	USER_AMOUNT = 'amount'
	HOLD_AMOUNT = 'hold_amount'

	def __init__(self, uid):
		self.__user_doc: DocumentReference = FIREBASE.collection(self.USER_TABLE).document(uid)
		self.__wallet_collection: CollectionReference = self.__user_doc.collection(self.WALLET_TABLE)
		self.__transaction_collection: CollectionReference = self.__user_doc.collection(self.TRANSACTION_TABLE)

	def demo_init(self, token, amount):
		transaction: DocumentReference = self.__transaction_collection.document()
		transaction.set(
			{
				'time': timezone.now(),
				'from_token': token,
				'from_amount': str(amount),
				'to_token': token,
				'to_amount': str(amount),
				'operated_by': 'System',
				'trade_type': 'Buy',
			}
		)
		transaction.update({'id': transaction.id})
		wallet: DocumentReference = self.__wallet_collection.document(token)
		wallet.set({'token_id': token, self.USER_AMOUNT: str(amount)})

	def trade(self, from_token, from_amount, to_token, to_amount, previous_amount=None):
		trade_type = 'Convert'
		profit = None
		if previous_amount is not None:
			profit = calculate(to_amount, '-', previous_amount)

		from_amount = Decimal(str(from_amount))
		from_after_trade = self.__update(from_token, -from_amount)
		to_after_trade = self.__upsert(to_token, to_amount)

		transaction: DocumentReference = self.__transaction_collection.document()
		transaction.set(
			{
				'time': timezone.now(),
				'from_token': from_token,
				'from_amount': str(from_amount),
				'to_token': to_token,
				'to_amount': str(to_amount),
				'trade_type': trade_type,
				'profit': str(profit) if profit is not None else None,
				'from_amount_after_trade': str(from_after_trade),
				'to_amount_after_trade': str(to_after_trade),
			}
		)
		transaction.update({'id': transaction.id})
		return transaction.get().to_dict()

	def _edit(self, token: str, data: dict[str, any]):
		doc_ref: DocumentReference = self.__wallet_collection.document(token)
		doc_ref.update(data)
		return {'id': doc_ref.id, **doc_ref.get().to_dict()}

	def __update(self, token, change) -> Decimal:
		doc_ref: DocumentReference = self.__wallet_collection.document(token)
		new_value = calculate(doc_ref.get().to_dict().get(self.USER_AMOUNT, 0), '+', change)

		if new_value < 0:
			raise NotEnoughTokenException

		doc_ref.update({self.USER_AMOUNT: str(new_value)})
		return new_value

	def __upsert(self, token, change) -> Decimal:
		doc_ref: DocumentReference = self.__wallet_collection.document(token)
		doc = doc_ref.get()

		if doc.exists:
			new_value = calculate(doc.to_dict().get(self.USER_AMOUNT, 0), '+', change)

			if new_value < 0:
				raise NotEnoughTokenException

			doc_ref.update({self.USER_AMOUNT: str(new_value)})
		else:
			new_value = calculate(0, '+', change)
			doc_ref.set({'token_id': token, self.USER_AMOUNT: str(new_value)})

		return new_value

	def get_wallet(self, token_id=None):
		if token_id is None:
			docs = self.__wallet_collection.stream()
		else:
			docs = self.__wallet_collection.where(filter=FieldFilter('token_id', '==', token_id)).stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def get_transaction(self):
		docs = self.__transaction_collection.order_by('-time').stream()
		return [{**doc.to_dict()} for doc in docs]

	def hold_token_for_order(self, token_id, amount):
		has_wallet = len(self.__wallet_collection.limit(1).get()) > 0
		if not has_wallet:
			self.demo_init(settings.INITIAL_TOKEN, settings.INITIAL_AMOUNT)

		doc_ref: DocumentReference = self.__wallet_collection.document(token_id)
		doc = doc_ref.get()

		if not doc.exists:
			raise NotEnoughTokenException

		new_value = doc.to_dict().get(self.USER_AMOUNT, 0)
		new_value = calculate(new_value, '-', amount)

		if new_value < 0:
			raise NotEnoughTokenException

		hold_value = doc.to_dict().get(self.HOLD_AMOUNT, 0)
		hold_value = 0 if hold_value is None else hold_value
		hold_value = calculate(hold_value, '+', amount)

		new_data = {
			self.USER_AMOUNT: str(new_value),
			self.HOLD_AMOUNT: str(hold_value),
		}

		doc_ref.update(new_data)

	def release_token_hold(self, token_id, amount):
		doc_ref: DocumentReference = self.__wallet_collection.document(token_id)
		doc = doc_ref.get()

		if not doc.exists:
			raise NotEnoughTokenException

		hold_value = doc.to_dict().get(self.HOLD_AMOUNT, 0)
		hold_value = calculate(hold_value, '-', amount)

		if hold_value < 0:
			raise NotEnoughTokenException

		new_value = doc.to_dict().get(self.USER_AMOUNT, 0)
		new_value = calculate(new_value, '+', amount)

		new_data = {
			self.USER_AMOUNT: str(new_value),
			self.HOLD_AMOUNT: str(hold_value),
		}

		doc_ref.update(new_data)

	def complete_order(self, from_token, from_amount, to_token, to_amount):
		from_doc_ref: DocumentReference = self.__wallet_collection.document(from_token)
		from_doc = from_doc_ref.get()

		if not from_doc.exists:
			raise NotEnoughTokenException

		new_hold_value = from_doc.to_dict().get(self.HOLD_AMOUNT, 0)
		new_hold_value = calculate(new_hold_value, '-', from_amount)

		if new_hold_value < 0:
			raise NotEnoughTokenException

		self.release_token_hold(from_token, from_amount)
		transaction = self.trade(from_token, from_amount, to_token, to_amount)
		return transaction
