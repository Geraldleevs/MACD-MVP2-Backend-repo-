from datetime import datetime, timedelta
from Krakenbot import settings
from typing import TypedDict
from django.utils import timezone
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.collection import CollectionReference
from Krakenbot.exceptions import NotEnoughTokenException, SessionExpiredException

class WalletField(TypedDict):
	token_id: str
	amount: float

class TransactionField(TypedDict):
	id: str
	time: datetime
	token_id: str
	amount: float
	price: float

class FirebaseWallet:
	def __init__(self, uid):
		self.__user_doc = settings.firebase.collection(u'users').document(uid)
		self.__wallet_collection: CollectionReference = self.__user_doc.collection('wallet')
		self.__transaction_collection: CollectionReference = self.__user_doc.collection('transaction')
		self.__session_collection: CollectionReference = self.__user_doc.collection('trade_session')

	def create_price_session(self, token_id, price):
		expired_on = timezone.now() + timedelta(minutes=5+1) # Extra 1 minute for API request latency
		session = self.__session_collection.document()
		session.set({ 'token_id': token_id, 'price': price, 'expired_on': expired_on })
		return {**session.get().to_dict(), 'session_id': session.id}

	def fetch_session_price(self, session_id, token_id):
		now = timezone.now()
		session = self.__session_collection.document(session_id)
		session = session.get()
		session_dict = session.to_dict()

		try:
			if session.exists and session_dict['token_id'] == token_id and session_dict['expired_on'] >= now:
				return session_dict['price']
			raise SessionExpiredException()
		except KeyError:
			raise SessionExpiredException()

	def clear_expired_session(self):
		now = timezone.now()
		sessions = self.__session_collection.where(filter=FieldFilter('expired_on', '<', now)).get()
		for session in sessions:
			session.reference.delete()

	def close_session(self, session_id):
		session = self.__session_collection.document(session_id)
		session.delete()

	def buy(self, token_id, amount, value):
		wallet = self.__wallet_collection.document(token_id)
		wallet_doc = wallet.get()
		transaction = self.__transaction_collection.document()
		transaction.set({
			'time': timezone.now(),
			'token_id': token_id,
			'amount': amount,
			'price': value / amount,
		})
		transaction.update({ 'id': transaction.id })

		if wallet_doc.exists:
			wallet.update({ 'amount': wallet_doc.to_dict()['amount'] + amount })
		else:
			wallet.set({ 'token_id': token_id, 'amount': amount })

	def sell(self, token_id, amount, value):
		wallet = self.__wallet_collection.document(token_id)
		wallet_doc = wallet.get()

		if wallet_doc.exists and wallet_doc.to_dict()['amount'] >= amount:
			wallet.update({ 'amount': wallet_doc.to_dict()['amount'] - amount })
		else:
			raise NotEnoughTokenException()

		transaction = self.__transaction_collection.document()
		transaction.set({
			'time': timezone.now(),
			'token_id': token_id,
			'amount': -amount,
			'price': value / amount,
		})

		transaction.update({ 'id': transaction.id })

	def get_wallet(self, token_id = None):
		if token_id is None:
			docs = self.__wallet_collection.stream()
		else:
			docs = self.__wallet_collection.where(filter=FieldFilter('token_id', '==', token_id)).stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def get_transaction(self):
		docs = self.__transaction_collection.order_by('-time').stream()
		return [{**doc.to_dict()} for doc in docs]
