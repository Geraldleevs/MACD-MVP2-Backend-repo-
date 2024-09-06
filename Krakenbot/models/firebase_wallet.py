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
			'from_token': token,
			'from_amount': amount,
			'to_token': token,
			'to_amount': amount,
			'operated_by': 'System',
			'trade_type': 'Buy'
		})
		transaction.update({ 'id': transaction.id })
		wallet = self.__wallet_collection.document(token)
		wallet.set({ 'token_id': token, self.USER_AMOUNT: amount })

	def __trade(self, from_token, from_amount, to_token, to_amount, operate_by = USER_NAME, bot_id = None):
		firebase_token = FirebaseToken()
		from_fiat = firebase_token.get(from_token).get('is_fiat', False)
		to_fiat = firebase_token.get(to_token).get('is_fiat', False)

		if to_fiat:
			to_amount = round(to_amount, 2)

		if from_fiat and to_fiat:
			trade_type = 'Convert'
		elif from_fiat:
			trade_type = 'Buy'
		elif to_fiat:
			trade_type = 'Sell'
		else:
			trade_type = 'Convert'

		self.__update(from_token, -from_amount, operate_by, 2 if from_fiat else None)
		self.__upsert(to_token, to_amount, operate_by, 2 if to_fiat else None)

		transaction = self.__transaction_collection.document()
		transaction.set({
			'time': timezone.now(),
			'from_token': from_token,
			'from_amount': from_amount,
			'to_token': to_token,
			'to_amount': to_amount,
			'operated_by': operate_by,
			'bot_id': bot_id,
			'trade_type': trade_type
		})
		transaction.update({ 'id': transaction.id })

		return transaction.get().to_dict()

	def trade_by_user(self, from_token, from_amount, to_token, to_amount):
		return self.__trade(from_token, from_amount, to_token, to_amount, self.USER_NAME)

	def trade_by_krakenbot(self, from_token, from_amount, to_token, to_amount, name, bot_id):
		return self.__trade(from_token, from_amount, to_token, to_amount, name, bot_id)

	def __update(self, token, change, type = USER_NAME, rounding: int | None = None):
		amount_field = self.BOT_AMOUNT if type != self.USER_NAME else self.USER_AMOUNT
		doc_ref = self.__wallet_collection.document(token)
		doc = doc_ref.get()

		if change < 0 and (not doc.exists or doc.to_dict().get(amount_field, 0) < (change * -1)):
			raise NotEnoughTokenException()

		new_value = doc.to_dict().get(amount_field, 0) + change
		if rounding is not None:
			new_value = round(new_value, rounding)

		doc_ref.update({ amount_field: new_value })

	def __upsert(self, token, change, type = USER_NAME, rounding: int | None = None):
		amount_field = self.BOT_AMOUNT if type != self.USER_NAME else self.USER_AMOUNT
		doc_ref = self.__wallet_collection.document(token)
		doc = doc_ref.get()

		if doc.exists:
			new_value = doc.to_dict().get(amount_field, 0) + change
			if rounding is not None:
				new_value = round(new_value, rounding)

			if new_value < 0:
				raise NotEnoughTokenException()
			doc_ref.update({ amount_field: new_value })
		else:
			doc_ref.set({ 'token_id': token, amount_field: change })

	def update_amount(self, token, change):
		is_fiat = FirebaseToken().get(token).get('is_fiat', False)
		self.__update(token, change, self.USER_NAME, 2 if is_fiat else None)

	def update_krakenbot_amount(self, token, change):
		is_fiat = FirebaseToken().get(token).get('is_fiat', False)
		self.__update(token, change, self.BOT_NAME, 2 if is_fiat else None)

	def reserve_krakenbot_amount(self, token, amount):
		is_fiat = FirebaseToken().get(token).get('is_fiat', False)
		self.__update(token, -amount, self.USER_NAME, 2 if is_fiat else None)
		self.__update(token, amount, self.BOT_NAME, 2 if is_fiat else None)

		wallet = self.__wallet_collection.document(token)
		return wallet.get().to_dict()

	def unreserve_krakenbot_amount(self, token, amount):
		is_fiat = FirebaseToken().get(token).get('is_fiat', False)
		self.__update(token, -amount, self.BOT_NAME, 2 if is_fiat else None)
		self.__update(token, amount, self.USER_NAME, 2 if is_fiat else None)

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
