from datetime import datetime
from Krakenbot import settings
from google.cloud.firestore_v1.base_query import FieldFilter

class FirebaseUsers:
	def __init__(self, uid = None):
		self.__users = settings.firebase.collection(u'users')
		if uid:
			self.__user_doc = self.__users.document(uid)
		else:
			self.__user_doc = None

	def update_portfolio_value(self, value: float, time: datetime):
		portfolio = self.__user_doc.get().to_dict().get('portfolio', [])
		time = datetime(time.year, time.month, time.day, time.hour, tzinfo=time.tzinfo)
		current_timestamp = time.timestamp()
		if len(portfolio) > 0:
			last_timestamp = portfolio[-1]['time'].timestamp()
			if last_timestamp - current_timestamp == 0:
				portfolio.pop()
		portfolio.append({ 'time': time, 'value': value })

		self.__user_doc.update({ 'portfolio': portfolio })

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
