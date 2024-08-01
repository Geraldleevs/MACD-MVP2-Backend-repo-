from datetime import datetime
from Krakenbot import settings
from google.cloud.firestore_v1.base_query import FieldFilter

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

	def update_history_prices(self, token_id, start_time: datetime, close_prices: list[float]):
		doc_ref = self.__collection.document(token_id)
		doc = doc_ref.get()
		update_data = {'history_prices': { 'start_time': start_time, 'data': close_prices }}

		if doc.exists:
			if self.__batch_writing:
				self.__batch.update(doc_ref, update_data)
			else:
				doc_ref.update(update_data)

	def all(self):
		query = self.__collection
		query = query.where(filter=FieldFilter('is_active', '==', True))
		docs = query.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def filter(self, token_id = None, is_active = True):
		query = self.__collection

		if token_id is not None and token_id != '':
			query = query.where(filter=FieldFilter('token_id', '==', token_id))
		if is_active is not None:
			query = query.where(filter=FieldFilter('is_active', '==', is_active))

		docs = query.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]
