from Krakenbot import settings
from django.utils import timezone
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.collection import CollectionReference
from Krakenbot.exceptions import NotEnoughTokenException
from Krakenbot.models.firebase_token import FirebaseToken

class FirebaseWallet:
	def __init__(self, uid):
		self.__user_doc = settings.firebase.collection(u'users').document(uid)
		self.__wallet_collection: CollectionReference = self.__user_doc.collection('wallet')
		self.__transaction_collection: CollectionReference = self.__user_doc.collection('transaction')

	def demo_init(self, token, amount):
		transaction = self.__transaction_collection.document()
		transaction.set({
			'time': timezone.now(),
			'from_token': 'Demo Account',
			'from_amount': 0,
			'to_token': token,
			'to_amount': amount,
		})
		transaction.update({ 'id': transaction.id })
		wallet = self.__wallet_collection.document(token)
		wallet.set({ 'token_id': token, 'amount': amount })

	def trade(self, from_token, from_amount, to_token, to_amount):
		from_wallet = self.__wallet_collection.document(from_token)
		from_wallet_doc = from_wallet.get()

		firebase_token = FirebaseToken().get(to_token)
		if firebase_token.get('is_fiat', False):
			to_amount = round(to_amount, 2)

		if not from_wallet_doc.exists or from_wallet_doc.to_dict()['amount'] < from_amount:
			raise NotEnoughTokenException()

		to_wallet = self.__wallet_collection.document(to_token)
		to_wallet_doc = to_wallet.get()

		transaction = self.__transaction_collection.document()
		transaction.set({
			'time': timezone.now(),
			'from_token': from_token,
			'from_amount': from_amount,
			'to_token': to_token,
			'to_amount': to_amount,
		})
		transaction.update({ 'id': transaction.id })

		from_wallet.update({ 'amount': from_wallet_doc.to_dict()['amount'] - from_amount })

		if to_wallet_doc.exists:
			to_wallet.update({ 'amount': to_wallet_doc.to_dict()['amount'] + to_amount })
		else:
			to_wallet.set({ 'token_id': to_token, 'amount': to_amount })

		return transaction.get().to_dict()

	def get_wallet(self, token_id = None):
		if token_id is None:
			docs = self.__wallet_collection.stream()
		else:
			docs = self.__wallet_collection.where(filter=FieldFilter('token_id', '==', token_id)).stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def get_transaction(self):
		docs = self.__transaction_collection.order_by('-time').stream()
		return [{**doc.to_dict()} for doc in docs]
