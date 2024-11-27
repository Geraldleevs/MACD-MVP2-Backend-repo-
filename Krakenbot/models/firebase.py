from datetime import datetime, timedelta
from decimal import Decimal
from pandas import DataFrame
from typing import Literal, TypedDict
import os
import pytz

from django.utils import timezone
from google.cloud.firestore_v1 import CollectionReference, DocumentReference
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.collection import CollectionReference

try:
	from Krakenbot import settings
	from Krakenbot.exceptions import BadRequestException, DatabaseIncorrectDataException, NotEnoughTokenException, NoUserSelectedException
	from Krakenbot.utils import acc_calc
except ModuleNotFoundError:
	from local_settings import settings
	from exceptions import BadRequestException, DatabaseIncorrectDataException, NotEnoughTokenException, NoUserSelectedException
	from utils import acc_calc


class AnalysisField(TypedDict):
	goal_length: str
	risk: str
	summary: str
	analysis: str
	technical_analysis: str


class LiveTradeField(TypedDict):
	livetrade_id: str
	uid: str
	start_time: datetime
	end_time: datetime
	strategy: str
	timeframe: str
	fiat: str
	cur_token: str
	token_id: str
	amount: float
	is_active: bool
	take_profit: float
	stop_loss: float


class NewsField(TypedDict):
	time: datetime
	title: str
	description: str
	content: str
	banner_image: str
	url: str
	source: str


class RecommendationField(TypedDict):
	token_id: str
	timeframe: str
	strategy: str
	profit: float
	profit_percent: float
	summary: str
	strategy_description: str
	updated_on: datetime


class PortfolioValues(TypedDict):
	uid: str
	value: Decimal
	time: datetime


class FirebaseAnalysis:
	def __init__(self):
		self.__analysis = settings.firebase.collection(u'analysis')

	def save(self, token_id: str, analysis: list[AnalysisField]):
		doc = self.__analysis.document(token_id)

		analysis = {
			data['goal_length'].lower(): {
				'risk': data['risk'].lower(),
				'summary': data['summary'],
				'analysis': data['analysis'],
				'technical_analysis': data['technical_analysis']
			} for data in analysis}

		data = { 'token_id': token_id, 'analysis': analysis }

		if doc.get().exists:
			doc.update(data)
		else:
			doc.set(data)

	def fetch_all(self):
		docs = self.__analysis.stream()
		return [doc.to_dict() for doc in docs]

	def fetch_strategy_description(self):
		doc = self.__analysis.document('Strategy').get()
		return doc.to_dict()['text']

	def get_risk(self, token_id, timeframe: Literal['very_short', 'short', 'medium','long'], default = 'Risk'):
		doc = self.__analysis.document(token_id).get()
		if doc.exists:
			try:
				return doc.to_dict()['analysis'][timeframe]['risk']
			except KeyError:
				pass
		return default

	def get_analysis(self, token_id, timeframe: Literal['very_short', 'short', 'medium','long'], default = 'Summary'):
		doc = self.__analysis.document(token_id).get()
		if doc.exists:
			try:
				analysis = doc.to_dict()['analysis'][timeframe]
				return {
					'analysis': analysis['analysis'],
					'summary': analysis['summary'],
					'technical_analysis': analysis['technical_analysis']
				}
			except KeyError:
				pass
		return {
			'analysis': default,
			'summary': default,
			'technical_analysis': default
		}


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

	def fetch_since(self, date: datetime):
		''' Return `[ ]` if no candle is chosen '''
		if self.__candle_token is None or self.__candle_data is None:
			return []

		yesterday = date - timedelta(days=1)
		timestamp = int(date.timestamp())

		query = self.__candle_data.where(filter=FieldFilter('date', '>=', yesterday)).stream()
		data = [record.to_dict() for record in query]
		return_data = [candle for day in data for candle in day['candles'] if candle['Unix_Timestamp'] >= timestamp]
		return return_data

	def fetch_cur_token(self):
		return self.__candle_token.get().to_dict().get('token_id', None)

	def fetch_pairs(self):
		docs = self.__candle.stream()
		return [doc.id for doc in docs]

	def fetch_pair(self, token_id: str):
		doc = self.__candle.where(filter=FieldFilter('token_id', '==', token_id)).limit(1).get()[0]
		return doc.id

	def save_fluctuations(self, close_mean: float, close_std_dev: float, high_mean: float, high_std_dev: float, low_mean: float, low_std_dev: float):
		self.__candle_token.update({
			'close_mean': close_mean,
			'close_std_dev': close_std_dev,
			'high_mean': high_mean,
			'high_std_dev': high_std_dev,
			'low_mean': low_mean,
			'low_std_dev': low_std_dev,
		})

	def get_fluctuations(self):
		return self.__candle_token.get().to_dict()

class FirebaseDiscover:
	def __init__(self):
		self.__discover = settings.firebase.collection(u'discover')

	def save(self, token_id: str, about: str):
		doc_ref = self.__discover.document(token_id)
		if doc_ref.get().exists:
			doc_ref.update({ 'about': about })
		else:
			doc_ref.set({ 'about': about, 'token_id': token_id })


class FirebaseLiveTrade:
	__count_doc_id = '_count'
	STOPPED_LOSS_STATUS ='STOP_LOSS'
	TAKING_PROFIT_STATUS ='TAKING_PROFIT'

	def __init__(self, uid = None):
		self.uid = uid
		self.__bot_name = os.environ.get('BOT_NAME', 'Krakenbot')
		self.__livetrade = settings.firebase.collection(u'livetrade')
		self.__user_livetrade = settings.firebase.collection(u'users').document(uid)

	def get_count(self):
		count_doc = self.__livetrade.document(self.__count_doc_id).get()
		count = count_doc.to_dict().get('count', 0)
		return count

	def add_and_get_count(self):
		count_doc = self.__livetrade.document(self.__count_doc_id)
		count = count_doc.get().to_dict().get('count', 0) + 1
		count_doc.set({ 'count': count })
		return count

	def add_user_livetrade(self, livetrade_ref):
		if self.uid is None:
			raise NoUserSelectedException()
		user_doc = self.__user_livetrade.get().to_dict()
		existing_livetrades = user_doc.get('livetrades', [])
		self.__user_livetrade.update({ 'livetrades': [*existing_livetrades, livetrade_ref]})

	def remove_user_livetrade(self, livetrade_ref):
		if self.uid is None:
			raise NoUserSelectedException()
		user_doc = self.__user_livetrade.get().to_dict()
		existing_livetrades = user_doc.get('livetrades', [])
		if livetrade_ref in existing_livetrades:
			existing_livetrades.remove(livetrade_ref)
		self.__user_livetrade.update({ 'livetrades': existing_livetrades })

	def create(self, data: LiveTradeField):
		take_profit = data.get('take_profit')
		stop_loss = data.get('stop_loss')
		if take_profit is not None and float(take_profit) > 0:
			data['take_profit'] = round(float(take_profit), 2)
		else:
			data['take_profit'] = None
		if stop_loss is not None and float(stop_loss) > 0:
			data['stop_loss'] = round(float(stop_loss), 2)
		else:
			data['stop_loss'] = None

		doc_count = self.add_and_get_count()
		doc_ref = self.__livetrade.document()
		bot_name = f'{self.__bot_name}-{doc_count}'
		doc_ref.set({**data, 'name': bot_name, 'status': 'READY_TO_TRADE'})
		doc_ref.update({ 'livetrade_id': doc_ref.id })
		self.add_user_livetrade(doc_ref)

		return { 'id': doc_ref.id, **doc_ref.get().to_dict() }

	def update(self, id, data: LiveTradeField):
		doc_ref = self.__livetrade.document(id)
		doc_ref.update(data)

	def update_take_profit_stop_loss(self, id, take_profit, stop_loss):
		if take_profit is not None and float(take_profit) > 0:
			take_profit = round(float(take_profit), 2)
		else:
			take_profit = None
		if stop_loss is not None and float(stop_loss) > 0:
			stop_loss = round(float(stop_loss), 2)
		else:
			stop_loss = None
		doc_ref = self.__livetrade.document(id)
		doc_ref.update({ 'take_profit': take_profit, 'stop_loss': stop_loss })

	def update_take_profit(self, id, take_profit):
		if take_profit is not None and float(take_profit) > 0:
			take_profit = round(float(take_profit), 2)
		else:
			take_profit = None
		doc_ref = self.__livetrade.document(id)
		doc_ref.update({ 'take_profit': take_profit })

	def update_stop_loss(self, id, stop_loss):
		if stop_loss is not None and float(stop_loss) > 0:
			stop_loss = round(float(stop_loss), 2)
		else:
			stop_loss = None
		doc_ref = self.__livetrade.document(id)
		doc_ref.update({ 'stop_loss': stop_loss })

	def close(self, id):
		doc_ref = self.__livetrade.document(id)
		doc_ref.update({ 'is_active': False, 'end_time': timezone.now(), 'status': 'COMPLETED' })
		self.remove_user_livetrade(doc_ref)

	def has(self, id):
		if id is None or id == '':
			return False
		doc = self.__livetrade.document(id).get()

		if not doc.exists:
			return False

		if self.uid:
			return doc.to_dict()['uid'] == self.uid

		return False

	def delete_by_id(self, id):
		self.__livetrade.document(id).delete()

	def get(self, id):
		return self.__livetrade.document(id).get().to_dict()

	def all(self):
		docs = self.__livetrade.stream()
		return [doc.to_dict() for doc in docs]

	def update_status(self, id, status: Literal['ORDER_PLACED', 'READY_TO_TRADE', 'COMPLETED'], order_id = None):
		data = { 'status': status }

		if status == 'ORDER_PLACED':
			data['order_id'] = order_id
		else:
			data['order_id'] = None

		if status == 'COMPLETED':
			data['is_active'] = False

		doc_ref = self.__livetrade.document(id)
		if doc_ref.get().exists:
			doc_ref.update(data)

		return doc_ref.get().to_dict()

	def taking_profit(self, id):
		doc_ref = self.__livetrade.document(id)
		if doc_ref.get().exists:
			doc_ref.update({ 'status': self.TAKING_PROFIT_STATUS })

	def stop_loss_pause(self, id):
		doc_ref = self.__livetrade.document(id)
		if doc_ref.get().exists:
			doc_ref.update({ 'status': self.STOPPED_LOSS_STATUS })

	def stop_loss_unpause(self, id):
		doc_ref = self.__livetrade.document(id)
		if doc_ref.get().exists:
			doc_ref.update({ 'status': 'READY_TO_TRADE' })

	def filter(self, strategy = None, timeframe = None, token_id = None, is_active = None, fiat = None, uid = None,
						status: Literal['ORDER_PLACED', 'READY_TO_TRADE'] = None, has_stop_loss: bool = None, has_take_profit: bool = None,
						stopped_loss: bool = None, taken_profit: bool = None):
		query = self.__livetrade

		if strategy is not None:
			query = query.where(filter=FieldFilter('strategy', '==', strategy))

		if timeframe is not None:
			query = query.where(filter=FieldFilter('timeframe', '==', timeframe))

		if token_id is not None:
			query = query.where(filter=FieldFilter('token_id', '==', token_id))

		if is_active is not None:
			query = query.where(filter=FieldFilter('is_active', '==', is_active))

		if fiat is not None:
			query = query.where(filter=FieldFilter('fiat', '==', fiat))

		if uid is not None:
			query = query.where(filter=FieldFilter('uid', '==', uid))

		if status is not None:
			query = query.where(filter=FieldFilter('status', '==', status))

		if has_stop_loss == True:
			query = query.where(filter=FieldFilter('stop_loss', '>', 0))

		if has_take_profit == True:
			query = query.where(filter=FieldFilter('take_profit', '>', 0))

		if stopped_loss is not None:
			query = query.where(filter=FieldFilter('status', '==' if stopped_loss else '!=', self.STOPPED_LOSS_STATUS))

		if taken_profit is not None:
			query = query.where(filter=FieldFilter('status', '==' if taken_profit else '!=', self.TAKING_PROFIT_STATUS))

		docs = query.stream()
		return [doc.to_dict() for doc in docs]


class FirebaseNews:
	def __init__(self):
		self.__collection = settings.firebase.collection(u'news')
		self.__next_fetch = settings.firebase.collection(u'next_fetch').document('news')

	def create(self, data: NewsField):
		doc_ref = self.__collection.document()
		doc_ref.set(data)

	def update(self, id, data: NewsField):
		doc_ref = self.__collection.document(id)
		doc_ref.update(data)

	def upsert(self, data: NewsField, tag: str):
		query = self.__collection
		query = query.where(filter=FieldFilter('url', '==', data['url']))
		doc = query.get()

		if len(doc) > 0:
			tags = doc[0].to_dict()['tag']
			if tag not in tags:
				tags.append(tag)
			self.update(doc[0].id, { **data, 'tag': tags })
		else:
			self.create({ **data, 'tag': [tag] })

	def delete_by_id(self, id):
		self.__collection.document(id).delete()

	def delete_all_before(self, before: datetime):
		docs = self.__collection.where(filter=FieldFilter('time', '<', before)).get()
		for doc in docs:
			doc.reference.delete()

	def fetch_next_query(self):
		doc = self.__next_fetch.get().to_dict()
		cur_index = doc.get('id', 0)
		queries = doc.get('queries', [])

		if len(queries) == 0:
			raise DatabaseIncorrectDataException()

		cur_index %= len(queries)
		query = queries[cur_index]
		tag = query.get('tag', '')
		query = query.get('query', '')
		return (cur_index, query, tag)

	def update_next_query(self, update_id = None):
		if update_id is not None:
			self.__next_fetch.update({ 'id': update_id })
		else:
			doc = self.fetch_next_query()
			self.__next_fetch.update({ 'id': doc.get('id', 0) + 1 })

	def all(self):
		docs = self.__collection.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def filter(self, id = None, date = None):
		query = self.__collection

		if id is not None:
			doc = query.document(id).get()
			return { **doc.to_dict(), 'id': doc.id }

		if date is not None:
			start_time = timezone.datetime(date.year, date.month, date.day, 0, 0, 0, 0)
			end_time = timezone.datetime(date.year, date.month, date.day, 23, 59, 59, 999999)
			query = query.where(filter=FieldFilter('time', '>=', start_time))
			query = query.where(filter=FieldFilter('time', '<=', end_time))
			docs = query.stream()
			return [{ **doc.to_dict(), 'id': doc.id } for doc in docs]

		return self.all()


class FirebaseOrderBook:
	__OPEN_STATUS = 'OPEN'
	__COMPLETED_STATUS = 'COMPLETED'
	__CANCELLED_STATUS = 'CANCELLED'

	def __init__(self):
		self.__order_book = settings.firebase.collection(u'order_book')

	def create_order(self, uid, from_token, to_token, price, volume, created_by = 'USER', bot_id = None):
		if created_by == 'USER':
			FirebaseWallet(uid).hold_token_for_order(from_token, volume)

		new_order = {
			'uid': uid,
			'from_token': from_token,
			'to_token': to_token,
			'price': float(price),
			'price_str': str(price),
			'volume': str(volume),
			'created_time': timezone.now(),
			'closed_time': None,
			'status': self.__OPEN_STATUS,
			'created_by': created_by,
			'bot_id': bot_id,
		}

		doc_ref = self.__order_book.document()
		doc_ref.set(new_order)
		doc_ref.update({ 'order_id': doc_ref.id })

		if bot_id is not None:
			FirebaseLiveTrade(uid).update_status(bot_id, 'ORDER_PLACED', doc_ref.id)

		return { 'id': doc_ref.id, **doc_ref.get().to_dict() }

	def cancel_order(self, id):
		doc_ref = self.__order_book.document(id)
		doc = doc_ref.get()

		if not doc.exists or doc.to_dict().get('status') != self.__OPEN_STATUS:
			raise BadRequestException()

		order_data = doc.to_dict()
		if doc.to_dict().get('created_by', 'USER') == 'USER':
			FirebaseWallet(order_data['uid']).release_token_hold(order_data['from_token'], order_data['volume'])

		update_data = {
			'closed_time': timezone.now(),
			'status': self.__CANCELLED_STATUS,
		}
		doc_ref.update(update_data)
		return { **doc_ref.get().to_dict(), 'id': doc_ref.id }

	def complete_order(self, id):
		doc_ref = self.__order_book.document(id)
		doc = doc_ref.get()

		if not doc.exists or doc.to_dict().get('status') != self.__OPEN_STATUS:
			raise BadRequestException()

		order_data = doc.to_dict()
		uid = order_data['uid']
		from_token = order_data['from_token']
		from_amount = order_data['volume']
		to_token = order_data['to_token']
		to_amount = acc_calc(from_amount, '*', order_data['price_str'])
		created_by = order_data.get('created_by', 'USER')
		bot_id = order_data.get('bot_id')
		transaction = FirebaseWallet(uid).complete_order(from_token, from_amount, to_token, to_amount, created_by, bot_id)

		if created_by != 'USER' and bot_id is not None:
			firebase_livetrade = FirebaseLiveTrade(uid)
			firebase_livetrade.update(bot_id, {
				'amount': float(transaction['to_amount']),
				'amount_str': str(transaction['to_amount_str']),
				'cur_token': transaction['to_token']
			})
			livetrade_details = firebase_livetrade.get(bot_id)
			status = livetrade_details['status']
			stopping_loss = status == firebase_livetrade.STOPPED_LOSS_STATUS
			taking_profit = status == firebase_livetrade.TAKING_PROFIT_STATUS
			if taking_profit or stopping_loss:
				cur_token = livetrade_details['cur_token']
				amount = livetrade_details['amount_str']
				firebase_livetrade.close(bot_id)
				FirebaseWallet(uid).unreserve_krakenbot_amount(cur_token, amount)
			else:
				firebase_livetrade.update_status(bot_id, 'READY_TO_TRADE')

		update_data = {
			'closed_time': timezone.now(),
			'status': self.__COMPLETED_STATUS,
			'transaction_id': transaction['id'],
		}
		doc_ref.update(update_data)
		return { **doc_ref.get().to_dict(), 'id': doc_ref.id }

	def filter(self, since: datetime = None, before: datetime = None, status: Literal['OPEN', 'CANCELLED', 'CLOSED', 'ALL'] = 'ALL', uid: str = None):
		query = self.__order_book

		match (status):
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
		return [{ **doc.to_dict(), 'id': doc.id } for doc in docs]

	def get(self, id):
		doc_ref = self.__order_book.document(id)
		doc = doc_ref.get()
		return { **doc.to_dict(), 'id': doc.id }

	def has(self, id):
		doc_ref = self.__order_book.document(id)
		return doc_ref.get().exists


class FirebaseRecommendation:
	def __init__(self):
		self.__collection = settings.firebase.collection(u'recommendation')

	def delete_all(self):
		docs = self.__collection.stream()
		for doc in docs:
			doc.reference.delete()

	def create(self, data: RecommendationField):
		doc_ref = self.__collection.document()
		doc_ref.set(data)

	def update(self, id, data: RecommendationField):
		doc_ref = self.__collection.document(id)
		doc_ref.update(data)

	def upsert(self, data: RecommendationField):
		query = self.__collection.where(filter=FieldFilter('token_id', '==', data['token_id']))
		query = query.where(filter=FieldFilter('timeframe', '==', data['timeframe']))
		doc = query.get()

		if len(doc) > 0:
			self.update(doc[0].id, data)
		else:
			self.create(data)

	def delete_by_id(self, id):
		self.__collection.document(id).delete()

	def all(self):
		docs = self.__collection.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def filter(self, token_id = None, timeframe = None):
		query = self.__collection

		if token_id is not None:
			query = query.where(filter=FieldFilter('token_id', '==', token_id))

		if timeframe is not None:
			query = query.where(filter=FieldFilter('timeframe', '==', timeframe))

		docs = query.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]


class FirebaseToken:
	def __init__(self):
		self.__collection = settings.firebase.collection(u'token')
		self.__batch = settings.db_batch
		self.__batch_writing = False

	def get(self, token_id):
		query = self.__collection
		query = query.where(filter=FieldFilter('token_id', '==', token_id))
		doc = query.get()[0]
		return { **doc.to_dict(), 'id': doc.id }

	def start_batch_write(self):
		self.__batch_writing = True

	def commit_batch_write(self):
		self.__batch.commit()
		self.__batch_writing = False

	def update_history_prices(self, token_id, times: list[datetime], close_prices: list[Decimal]):
		doc_ref = self.__collection.document(token_id)
		doc = doc_ref.get()
		close_prices = [float(close_price) for close_price in close_prices]
		update_data = {'history_prices': { 'start_time': times[0], 'times': times, 'data': close_prices }}

		if doc.exists:
			if self.__batch_writing:
				self.__batch.update(doc_ref, update_data)
			else:
				doc_ref.update(update_data)

	def update(self, token_id, data):
		doc_ref = self.__collection.document(token_id)
		doc = doc_ref.get()

		if doc.exists:
			if self.__batch_writing:
				self.__batch.update(doc_ref, data)
			else:
				doc_ref.update(data)

	def all(self):
		query = self.__collection
		query = query.where(filter=FieldFilter('is_active', '==', True))
		docs = query.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def filter(self, token_id = None, is_active = True, is_fiat = None):
		query = self.__collection

		if token_id is not None and token_id != '':
			query = query.where(filter=FieldFilter('token_id', '==', token_id))
		if is_active is not None:
			query = query.where(filter=FieldFilter('is_active', '==', is_active))
		if is_fiat is not None:
			query = query.where(filter=FieldFilter('is_fiat', '==', is_fiat))

		docs = query.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]


class FirebaseUsers:
	def __init__(self, uid = None):
		self.__users = settings.firebase.collection(u'users')
		if uid:
			self.__user_doc = self.__users.document(uid)
		else:
			self.__user_doc = None

	def update_portfolio_value(self, value: Decimal, time: datetime):
		'''
		raise `NoUserSelectedException` if not initialised with uid
		'''
		if self.__user_doc is None:
			raise NoUserSelectedException()

		time = datetime(time.year, time.month, time.day, time.hour, tzinfo=time.tzinfo)
		current_timestamp = time.timestamp()
		portfolio = self.__user_doc.collection('portfolio').document(str(current_timestamp))
		amount = float(acc_calc(value, '+', 0, 2))
		portfolio.set({ 'time': time, 'value': amount })

	def batch_update_portfolio(self, values: list[PortfolioValues]):
		batch = settings.db_batch

		for value in values:
			time = value['time']
			time = datetime(time.year, time.month, time.day, time.hour, tzinfo=time.tzinfo)
			current_timestamp = time.timestamp()
			user_portfolio = self.__users.document(value['uid']).collection('portfolio').document(str(current_timestamp))
			amount = float(acc_calc(value['value'], '+', 0, 2))
			batch.set(user_portfolio, { 'time': time, 'value': amount })

		batch.commit()

	def get(self):
		'''
		raise `NoUserSelectedException` if not initialised with uid
		'''
		if self.__user_doc is None:
			raise NoUserSelectedException()

		doc = self.__user_doc.get()
		return doc.to_dict()

	def __get_all(self, include_deactivated: None | bool = None):
		if include_deactivated == False:
			query = self.__users.where(filter=FieldFilter('deactivated', '!=', True))
		else:
			query = self.__users
		docs = query.stream()
		return docs

	def get_all_user_id(self, include_deactivated: None | bool = None):
		docs = self.__get_all(include_deactivated)
		return [doc.id for doc in docs]

	def get_all(self, include_deactivated: None | bool = None):
		docs = self.__get_all(include_deactivated)
		return [doc.to_dict() for doc in docs]


class FirebaseWallet:
	USER_AMOUNT = 'amount'
	USER_AMOUNT_STR = 'amount_str'
	BOT_AMOUNT = 'krakenbot_amount'
	BOT_AMOUNT_STR = 'krakenbot_amount_str'
	HOLD_AMOUNT = 'hold_amount'
	HOLD_AMOUNT_STR = 'hold_amount_str'
	USER_NAME = 'User'
	BOT_NAME = 'Krakenbot'

	def __init__(self, uid):
		self.__user_doc = settings.firebase.collection(u'users').document(uid)
		self.__wallet_collection: CollectionReference = self.__user_doc.collection('wallet')
		self.__transaction_collection: CollectionReference = self.__user_doc.collection('transaction')

	def demo_init(self, token, amount):
		transaction = self.__transaction_collection.document()
		transaction.set({
			'time': timezone.now(),
			'from_token': token,
			'from_amount': float(amount),
			'from_amount_str': str(amount),
			'to_token': token,
			'to_amount': float(amount),
			'to_amount_str': str(amount),
			'operated_by': 'System',
			'trade_type': 'Buy'
		})
		transaction.update({ 'id': transaction.id })
		wallet = self.__wallet_collection.document(token)
		wallet.set({ 'token_id': token, self.USER_AMOUNT: float(amount), self.USER_AMOUNT_STR: str(amount) })

	def __trade(self, from_token, from_amount, to_token, to_amount, operate_by = USER_NAME, bot_id = None, previous_amount = None):
		firebase_token = FirebaseToken()
		from_fiat = firebase_token.get(from_token).get('is_fiat', False)
		to_fiat = firebase_token.get(to_token).get('is_fiat', False)

		if to_fiat:
			to_amount = acc_calc(to_amount, '+', 0, 2)

		if from_fiat and to_fiat:
			trade_type = 'Convert'
		elif from_fiat:
			trade_type = 'Buy'
		elif to_fiat:
			trade_type = 'Sell'
		else:
			trade_type = 'Convert'

		profit = None
		if to_fiat and previous_amount is not None:
			profit = acc_calc(to_amount, '-', previous_amount, 2)

		from_amount = Decimal(str(from_amount))
		from_after_trade = self.__update(from_token, -from_amount, operate_by, 2 if from_fiat else None)
		to_after_trade = self.__upsert(to_token, to_amount, operate_by, 2 if to_fiat else None)

		transaction = self.__transaction_collection.document()
		transaction.set({
			'time': timezone.now(),
			'from_token': from_token,
			'from_amount': float(from_amount),
			'from_amount_str': str(from_amount),
			'to_token': to_token,
			'to_amount': float(to_amount),
			'to_amount_str': str(to_amount),
			'operated_by': operate_by,
			'bot_id': bot_id,
			'trade_type': trade_type,
			'profit': float(profit) if profit is not None else None,
			'from_amount_after_trade': float(from_after_trade),
			'to_amount_after_trade': float(to_after_trade),
			'from_amount_after_trade_str': str(from_after_trade),
			'to_amount_after_trade_str': str(to_after_trade)
		})
		transaction.update({ 'id': transaction.id })

		return transaction.get().to_dict()

	def trade_by_user(self, from_token, from_amount, to_token, to_amount):
		return self.__trade(from_token, from_amount, to_token, to_amount, self.USER_NAME)

	def trade_by_krakenbot(self, from_token, from_amount, to_token, to_amount, name, bot_id):
		firebase_livetrade = FirebaseLiveTrade()
		previous_amount = firebase_livetrade.get(bot_id).get('previous_amount', None)
		trade_result = self.__trade(from_token, from_amount, to_token, to_amount, name, bot_id, previous_amount)

		to_fiat = FirebaseToken().get(to_token).get('is_fiat', False)
		if to_fiat:
			firebase_livetrade.update(bot_id, { 'previous_amount': trade_result.get('to_amount', None) })
		else:
			firebase_livetrade.update(bot_id, { 'previous_amount': trade_result.get('from_amount', None) })

		return trade_result

	def _edit(self, token: str, data: dict[str, any]):
		doc_ref = self.__wallet_collection.document(token)
		doc_ref.update(data)
		return { 'id': doc_ref.id, **doc_ref.get().to_dict() }

	def __update(self, token, change, type = USER_NAME, rounding: int | None = None) -> Decimal:
		amount_field = self.BOT_AMOUNT if type != self.USER_NAME else self.USER_AMOUNT
		amount_field_str = self.BOT_AMOUNT_STR if type != self.USER_NAME else self.USER_AMOUNT_STR
		doc_ref = self.__wallet_collection.document(token)
		doc = doc_ref.get()

		if rounding is None:
			new_value = acc_calc(doc.to_dict().get(amount_field_str, 0), '+', change)
		else:
			new_value = acc_calc(doc.to_dict().get(amount_field_str, 0), '+', change, rounding)

		if new_value < 0:
			raise NotEnoughTokenException()

		doc_ref.update({ amount_field: float(new_value), amount_field_str: str(new_value) })

		updated_doc = doc_ref.get().to_dict()
		return acc_calc(updated_doc.get(self.BOT_AMOUNT_STR, 0), '+', updated_doc.get(self.USER_AMOUNT_STR, 0))

	def __upsert(self, token, change, type = USER_NAME, rounding: int | None = None) -> Decimal:
		amount_field = self.BOT_AMOUNT if type != self.USER_NAME else self.USER_AMOUNT
		amount_field_str = self.BOT_AMOUNT_STR if type != self.USER_NAME else self.USER_AMOUNT_STR
		doc_ref = self.__wallet_collection.document(token)
		doc = doc_ref.get()

		if doc.exists:
			if rounding is None:
				new_value = acc_calc(doc.to_dict().get(amount_field_str, 0), '+', change)
			else:
				new_value = acc_calc(doc.to_dict().get(amount_field_str, 0), '+', change, rounding)

			if new_value < 0:
				raise NotEnoughTokenException()

			doc_ref.update({ amount_field: float(new_value), amount_field_str: str(new_value) })
		else:
			if rounding is None:
				new_value = acc_calc(0, '+', change)
			else:
				new_value = acc_calc(0, '+', change, rounding)
			doc_ref.set({ 'token_id': token, amount_field: float(new_value), amount_field_str: str(new_value) })

		updated_doc = doc_ref.get().to_dict()
		return acc_calc(updated_doc.get(self.BOT_AMOUNT_STR, 0), '+', updated_doc.get(self.USER_AMOUNT_STR, 0))

	def reserve_krakenbot_amount(self, token, amount):
		is_fiat = FirebaseToken().get(token).get('is_fiat', False)
		amount = Decimal(str(amount))
		self.__update(token, -amount, self.USER_NAME, 2 if is_fiat else None)
		self.__update(token, amount, self.BOT_NAME, 2 if is_fiat else None)

		wallet = self.__wallet_collection.document(token)
		return wallet.get().to_dict()

	def unreserve_krakenbot_amount(self, token, amount):
		is_fiat = FirebaseToken().get(token).get('is_fiat', False)
		amount = Decimal(str(amount))
		self.__update(token, -amount, self.BOT_NAME, 2 if is_fiat else None)
		self.__update(token, amount, self.USER_NAME, 2 if is_fiat else None)

		wallet = self.__wallet_collection.document(token)
		return wallet.get().to_dict()

	def get_wallet(self, token_id = None):
		if token_id is None:
			docs = self.__wallet_collection.stream()
		else:
			docs = self.__wallet_collection.where(filter=FieldFilter('token_id', '==', token_id)).stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def get_transaction(self):
		docs = self.__transaction_collection.order_by('-time').stream()
		return [{**doc.to_dict()} for doc in docs]

	def set_bot_amount(self, token, bot_amount):
		doc_ref = self.__wallet_collection.document(token)
		doc_ref.update({self.BOT_AMOUNT: float(bot_amount), self.BOT_AMOUNT_STR: str(bot_amount)})

	def hold_token_for_order(self, token_id, amount):
		doc_ref = self.__wallet_collection.document(token_id)
		doc = doc_ref.get()

		if not doc.exists:
			raise NotEnoughTokenException()

		is_fiat = FirebaseToken().get(token_id).get('is_fiat', False)
		new_value = doc.to_dict().get(self.USER_AMOUNT_STR, 0)
		if is_fiat:
			new_value = acc_calc(new_value, '-', amount, 2)
		else:
			new_value = acc_calc(new_value, '-', amount)

		if new_value < 0:
			raise NotEnoughTokenException()

		hold_value = doc.to_dict().get(self.HOLD_AMOUNT_STR, 0)
		hold_value = 0 if hold_value is None else hold_value
		if is_fiat:
			hold_value = acc_calc(hold_value, '+', amount, 2)
		else:
			hold_value = acc_calc(hold_value, '+', amount)

		new_data = {
			self.USER_AMOUNT: float(new_value),
			self.USER_AMOUNT_STR: str(new_value),
			self.HOLD_AMOUNT: float(hold_value),
			self.HOLD_AMOUNT_STR: str(hold_value),
		}

		doc_ref.update(new_data)

	def release_token_hold(self, token_id, amount):
		doc_ref = self.__wallet_collection.document(token_id)
		doc = doc_ref.get()

		if not doc.exists:
			raise NotEnoughTokenException()

		is_fiat = FirebaseToken().get(token_id).get('is_fiat', False)
		hold_value = doc.to_dict().get(self.HOLD_AMOUNT_STR, 0)
		if is_fiat:
			hold_value = acc_calc(hold_value, '-', amount, 2)
		else:
			hold_value = acc_calc(hold_value, '-', amount)

		if hold_value < 0:
			raise NotEnoughTokenException()

		new_value = doc.to_dict().get(self.USER_AMOUNT_STR, 0)
		if is_fiat:
			new_value = acc_calc(new_value, '+', amount, 2)
		else:
			new_value = acc_calc(new_value, '+', amount)

		new_data = {
			self.USER_AMOUNT: float(new_value),
			self.USER_AMOUNT_STR: str(new_value),
			self.HOLD_AMOUNT: float(hold_value),
			self.HOLD_AMOUNT_STR: str(hold_value),
		}

		doc_ref.update(new_data)

	def complete_order(self, from_token, from_amount, to_token, to_amount, created_by, bot_id):
		from_doc_ref = self.__wallet_collection.document(from_token)
		from_doc = from_doc_ref.get()

		if not from_doc.exists:
			raise NotEnoughTokenException()

		if created_by == 'USER':
			is_from_fiat = FirebaseToken().get(from_token).get('is_fiat', False)
			new_hold_value = from_doc.to_dict().get(self.HOLD_AMOUNT_STR, 0)
			if is_from_fiat:
				new_hold_value = acc_calc(new_hold_value, '-', from_amount, 2)
			else:
				new_hold_value = acc_calc(new_hold_value, '-', from_amount)

			if new_hold_value < 0:
				raise NotEnoughTokenException()

			self.release_token_hold(from_token, from_amount)
			transaction = self.trade_by_user(from_token, from_amount, to_token, to_amount)
		else:
			transaction = self.trade_by_krakenbot(from_token, from_amount, to_token, to_amount, created_by, bot_id)
		return transaction
