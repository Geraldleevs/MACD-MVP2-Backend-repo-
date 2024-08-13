from Krakenbot import settings
from django.utils import timezone
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.collection import CollectionReference
from Krakenbot.exceptions import NotEnoughTokenException
from Krakenbot.models.firebase_token import FirebaseToken

class FirebaseWallet:
	USER_AMOUNT = 'amount'
	BOT_AMOUNT = 'krakenbot_amount'
	USER_NAME = 'User'
	BOT_NAME = 'Krakenbot'

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
		wallet.set({ 'token_id': token, self.USER_AMOUNT: amount })

	def __trade(self, from_token, from_amount, to_token, to_amount, operate_by = USER_NAME, bot_id = None):
		if FirebaseToken().get(to_token).get('is_fiat', False):
			to_amount = round(to_amount, 2)

		self.__update(from_token, -from_amount, operate_by)
		self.__upsert(to_token, to_amount, operate_by)

		transaction = self.__transaction_collection.document()
		transaction.set({
			'time': timezone.now(),
			'from_token': from_token,
			'from_amount': from_amount,
			'to_token': to_token,
			'to_amount': to_amount,
			'operated_by': operate_by,
			'bot_id': bot_id
		})
		transaction.update({ 'id': transaction.id })

		return transaction.get().to_dict()

	def trade_by_user(self, from_token, from_amount, to_token, to_amount):
		return self.__trade(from_token, from_amount, to_token, to_amount, self.USER_NAME)

	def trade_by_krakenbot(self, from_token, from_amount, to_token, to_amount, name, bot_id):
		return self.__trade(from_token, from_amount, to_token, to_amount, name, bot_id)

	def __update(self, token, change, type = USER_NAME):
		amount_field = self.BOT_AMOUNT if type == self.BOT_NAME else self.USER_AMOUNT
		doc_ref = self.__wallet_collection.document(token)
		doc = doc_ref.get()

		if change < 0 and (not doc.exists or doc.to_dict().get(amount_field, 0) < (change * -1)):
			raise NotEnoughTokenException()

		doc_ref.update({ amount_field: doc.to_dict().get(amount_field, 0) + change })

	def __upsert(self, token, change, type = USER_NAME):
		amount_field = self.BOT_AMOUNT if type == self.BOT_NAME else self.USER_AMOUNT
		doc_ref = self.__wallet_collection.document(token)
		doc = doc_ref.get()

		if doc.exists:
			if doc.to_dict().get(amount_field, 0) < (change * -1):
				raise NotEnoughTokenException()
			doc_ref.update({ amount_field: doc.to_dict().get(amount_field, 0) + change })
		else:
			doc_ref.set({ 'token_id': token, amount_field: change })

	def update_amount(self, token, change):
		self.__update(token, change, self.USER_NAME)

	def update_krakenbot_amount(self, token, change):
		self.__update(token, change, self.BOT_NAME)

	def reserve_krakenbot_amount(self, token, amount):
		self.__update(token, -amount, self.USER_NAME)
		self.__update(token, amount, self.BOT_NAME)

		wallet = self.__wallet_collection.document(token)
		return wallet.get().to_dict()

	def unreserve_krakenbot_amount(self, token, amount):
		self.__update(token, -amount, self.BOT_NAME)
		self.__update(token, amount, self.USER_NAME)

		wallet = self.__wallet_collection.document(token)
		return wallet.get().to_dict()

	def get_wallet(self, token_id = None):
		if token_id is None:
			docs = self.__wallet_collection.stream()
		else:
			docs = self.__wallet_collection.where(filter=FieldFilter('token_id', '==', token_id)).stream()
		return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

	def get_transaction(self):
		docs = self.__transaction_collection.order_by('-time').stream()
		return [{**doc.to_dict()} for doc in docs]
