import firebase_admin
from firebase_admin.credentials import Certificate
from firebase_admin import firestore
from Krakenbot import settings
from typing import TypedDict
from datetime import datetime
from google.cloud.firestore_v1.base_query import FieldFilter

class RecommendationField(TypedDict):
	token_id: str
	timeframe: str
	strategy: str
	profit: float
	profit_percent: float
	summary: str
	strategy_description: str
	updated_on: datetime


class FirebaseClientRecommendation:
	def __init__(self):
		firebase_admin.initialize_app(Certificate(settings.firebase_admin_settings))
		self.__db = firestore.client()
		self.__collection = self.__db.collection(u'recommendation')

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
