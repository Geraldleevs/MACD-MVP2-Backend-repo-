from Krakenbot import settings
from typing import TypedDict
from datetime import datetime
from django.utils import timezone
from google.cloud.firestore_v1.base_query import FieldFilter

class NewsField(TypedDict):
	time: datetime
	title: str
	description: str
	content: str
	banner_image: str
	url: str
	source: str

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

	def upsert(self, data: NewsField):
		query = self.__collection
		query = query.where(filter=FieldFilter('url', '==', data['url']))
		doc = query.get()

		if len(doc) > 0:
			self.update(doc[0].id, data)
		else:
			self.create(data)

	def delete_by_id(self, id):
		self.__collection.document(id).delete()

	def delete_all_before(self, before: datetime):
		docs = self.__collection.where(filter=FieldFilter('time', '<', before)).get()
		for doc in docs:
			doc.reference.delete()

	def fetch_next_query(self):
		doc = self.__next_fetch.get().to_dict()
		return doc

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
