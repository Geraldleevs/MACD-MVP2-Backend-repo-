from Krakenbot import settings
from google.cloud.firestore_v1.base_query import FieldFilter

class FirebaseToken:
	def __init__(self):
		self.__collection = settings.firebase.collection(u'token')

	def all(self):
		docs = self.__collection.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def filter(self, token_id = None):
		query = self.__collection

		if token_id is not None:
			query = query.where(filter=FieldFilter('token_id', '==', token_id))

		docs = query.stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]
