from datetime import datetime
from Krakenbot import settings
from typing import TypedDict
from google.cloud.firestore_v1.base_query import FieldFilter
from django.utils import timezone

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
	def __init__(self, uid):
		self.uid = uid
		self.__livetrade = settings.firebase.collection(u'livetrade')
		self.__user_livetrade = settings.firebase.collection(u'users').document(uid)

	def add_user_livetrade(self, livetrade_ref):
		user_doc = self.__user_livetrade.get().to_dict()
		existing_livetrades = user_doc.get('livetrades', [])
		self.__user_livetrade.update({ 'livetrades': [*existing_livetrades, livetrade_ref]})

	def remove_user_livetrade(self, livetrade_ref):
		user_doc = self.__user_livetrade.get().to_dict()
		existing_livetrades = user_doc.get('livetrades', [])
		if livetrade_ref in existing_livetrades:
			existing_livetrades.remove(livetrade_ref)
		self.__user_livetrade.update({ 'livetrades': existing_livetrades })

	def create(self, data: LiveTradeField):
		doc_ref = self.__livetrade.document()
		doc_ref.set(data)
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

	def filter(self, strategy = None, timeframe = None, token_id = None, is_active = None):
		query = self.__livetrade

		if strategy is not None:
			query = query.where(filter=FieldFilter('strategy', '==', strategy))

		if timeframe is not None:
			query = query.where(filter=FieldFilter('timeframe', '==', timeframe))

		if token_id is not None:
			query = query.where(filter=FieldFilter('token_id', '==', token_id))

		if is_active is not None:
			query = query.where(filter=FieldFilter('is_active', '==', is_active))

		docs = query.stream()
		return [doc.to_dict() for doc in docs]
