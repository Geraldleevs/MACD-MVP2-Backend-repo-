from datetime import datetime
from Krakenbot import settings
from typing import Literal, TypedDict
from google.cloud.firestore_v1.base_query import FieldFilter
from django.utils import timezone
from Krakenbot.exceptions import NoUserSelectedException
import os

class LiveTradeField(TypedDict):
	livetrade_id: str
	uid: str
	start_time: datetime
	end_time: datetime
	strategy: str
	timeframe: str
	cur_token: str
	token_id: str
	amount: float
	is_active: bool

class FirebaseLiveTrade:
	__count_doc_id = '_count'

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
		doc_count = self.add_and_get_count()
		doc_ref = self.__livetrade.document()
		doc_ref.set({**data, 'name': f'{self.__bot_name}-{doc_count}', 'status': 'READY_TO_TRADE'})
		doc_ref.update({ 'livetrade_id': doc_ref.id })
		self.add_user_livetrade(doc_ref)
		return doc_ref.id

	def update(self, id, data: LiveTradeField):
		doc_ref = self.__livetrade.document(id)
		doc_ref.update(data)

	def close(self, id):
		doc_ref = self.__livetrade.document(id)
		doc_ref.update({ 'is_active': False, 'end_time': timezone.now() })
		self.remove_user_livetrade(doc_ref)

	def has(self, id):
		if id is None or id == '':
			return False
		return self.__livetrade.document(id).get().exists

	def delete_by_id(self, id):
		self.__livetrade.document(id).delete()

	def get(self, id):
		return self.__livetrade.document(id).get().to_dict()

	def all(self):
		docs = self.__livetrade.stream()
		return [doc.to_dict() for doc in docs]

	def update_status(self, id, status: Literal['ORDER_PLACED', 'READY_TO_TRADE'], order_id = None):
		data = { 'status': status }

		if status == 'ORDER_PLACED':
			data['order_id'] = order_id
		else:
			data['order_id'] = None

		doc_ref = self.__livetrade.document(id)
		if doc_ref.get().exists:
			doc_ref.update(data)

		return doc_ref.get().to_dict()

	def filter(self, strategy = None, timeframe = None, token_id = None, is_active = None, fiat = None, uid = None, status: Literal['ORDER_PLACED', 'READY_TO_TRADE'] = None):
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

		docs = query.stream()
		return [doc.to_dict() for doc in docs]
