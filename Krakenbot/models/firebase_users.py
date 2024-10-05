from datetime import datetime
from typing import TypedDict
from Krakenbot import settings
from google.cloud.firestore_v1.base_query import FieldFilter

from Krakenbot.exceptions import NoUserSelectedException

class PortfolioValues(TypedDict):
	uid: str
	value: float
	time: datetime

class FirebaseUsers:
	def __init__(self, uid = None):
		self.__users = settings.firebase.collection(u'users')
		if uid:
			self.__user_doc = self.__users.document(uid)
		else:
			self.__user_doc = None

	def update_portfolio_value(self, value: float, time: datetime):
		'''
		raise `NoUserSelectedException` if not initialised with uid
		'''
		if self.__user_doc is None:
			raise NoUserSelectedException()

		time = datetime(time.year, time.month, time.day, time.hour, tzinfo=time.tzinfo)
		current_timestamp = time.timestamp()
		portfolio = self.__user_doc.collection('portfolio').document(str(current_timestamp))
		portfolio.set({ 'time': time, 'value': value })

	def batch_update_portfolio(self, values: list[PortfolioValues]):
		batch = settings.db_batch

		for value in values:
			time = value['time']
			time = datetime(time.year, time.month, time.day, time.hour, tzinfo=time.tzinfo)
			current_timestamp = time.timestamp()
			user_portfolio = self.__users.document(value['uid']).collection('portfolio').document(str(current_timestamp))
			batch.set(user_portfolio, { 'time': time, 'value': value['value'] })

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
