from Krakenbot import settings
from google.cloud.firestore_v1.base_query import FieldFilter

class FirebaseToken:
	def __init__(self):
		self.__collection = settings.firebase.collection(u'token')

	def get(self, token_id):
		query = self.__collection
		query = query.where(filter=FieldFilter('token_id', '==', token_id))
		doc = query.get()[0]
		return { **doc.to_dict(), 'id': doc.id }

	def update_close_price(self, token_id, close_price: float):
		doc_ref = self.__collection.document(token_id)
		doc = doc_ref.get()

		if doc.exists:
			doc_ref.update({'last_close_price': close_price})

	def all(self):
		docs = self.__collection.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def filter(self, token_id = None):
		query = self.__collection

		if token_id is not None and token_id != '':
			query = query.where(filter=FieldFilter('token_id', '==', token_id))

		docs = query.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]
