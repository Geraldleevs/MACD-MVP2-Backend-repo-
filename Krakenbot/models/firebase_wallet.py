from decimal import Decimal
from Krakenbot import settings
from django.utils import timezone
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.collection import CollectionReference
from Krakenbot.exceptions import NotEnoughTokenException
from Krakenbot.models.firebase_livetrade import FirebaseLiveTrade
from Krakenbot.models.firebase_token import FirebaseToken
from Krakenbot.utils import acc_calc

class FirebaseWallet:
	USER_AMOUNT = 'amount'
	USER_AMOUNT_STR = 'amount_str'
	BOT_AMOUNT = 'krakenbot_amount'
	BOT_AMOUNT_STR = 'krakenbot_amount_str'
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
			'from_amount': float(amount),
			'from_amount_str': str(amount),
			'to_token': token,
			'to_amount': float(amount),
			'to_amount_str': str(amount),
			'operated_by': 'System',
			'trade_type': 'Buy'
		})
		transaction.update({ 'id': transaction.id })
		wallet = self.__wallet_collection.document(token)
		wallet.set({ 'token_id': token, self.USER_AMOUNT: float(amount), self.USER_AMOUNT_STR: str(amount) })

	def __trade(self, from_token, from_amount, to_token, to_amount, operate_by = USER_NAME, bot_id = None, previous_amount = None):
		firebase_token = FirebaseToken()
		from_fiat = firebase_token.get(from_token).get('is_fiat', False)
		to_fiat = firebase_token.get(to_token).get('is_fiat', False)

		if to_fiat:
			to_amount = acc_calc(to_amount, '+', 0, 2)

		if from_fiat and to_fiat:
			trade_type = 'Convert'
		elif from_fiat:
			trade_type = 'Buy'
		elif to_fiat:
			trade_type = 'Sell'
		else:
			trade_type = 'Convert'

		profit = None
		if to_fiat and previous_amount is not None:
			profit = acc_calc(to_amount, '-', previous_amount, 2)

		from_amount = Decimal(str(from_amount))
		from_after_trade = self.__update(from_token, -from_amount, operate_by, 2 if from_fiat else None)
		to_after_trade = self.__upsert(to_token, to_amount, operate_by, 2 if to_fiat else None)

		transaction = self.__transaction_collection.document()
		transaction.set({
			'time': timezone.now(),
			'from_token': from_token,
			'from_amount': float(from_amount),
			'from_amount_str': str(from_amount),
			'to_token': to_token,
			'to_amount': float(to_amount),
			'to_amount_str': str(to_amount),
			'operated_by': operate_by,
			'bot_id': bot_id,
			'trade_type': trade_type,
			'profit': float(profit) if profit is not None else None,
			'from_amount_after_trade': float(from_after_trade),
			'to_amount_after_trade': float(to_after_trade),
			'from_amount_after_trade_str': str(from_after_trade),
			'to_amount_after_trade_str': str(to_after_trade)
		})
		transaction.update({ 'id': transaction.id })

		return transaction.get().to_dict()

	def trade_by_user(self, from_token, from_amount, to_token, to_amount):
		return self.__trade(from_token, from_amount, to_token, to_amount, self.USER_NAME)

	def trade_by_krakenbot(self, from_token, from_amount, to_token, to_amount, name, bot_id):
		firebase_livetrade = FirebaseLiveTrade()
		previous_amount = firebase_livetrade.get(bot_id).get('previous_amount', None)
		trade_result = self.__trade(from_token, from_amount, to_token, to_amount, name, bot_id, previous_amount)

		to_fiat = FirebaseToken().get(to_token).get('is_fiat', False)
		if to_fiat:
			firebase_livetrade.update(bot_id, { 'previous_amount': trade_result.get('to_amount', None) })
		else:
			firebase_livetrade.update(bot_id, { 'previous_amount': trade_result.get('from_amount', None) })

		return trade_result

	def __update(self, token, change, type = USER_NAME, rounding: int | None = None) -> Decimal:
		amount_field = self.BOT_AMOUNT if type != self.USER_NAME else self.USER_AMOUNT
		amount_field_str = self.BOT_AMOUNT_STR if type != self.USER_NAME else self.USER_AMOUNT_STR
		doc_ref = self.__wallet_collection.document(token)
		doc = doc_ref.get()

		if rounding is None:
			new_value = acc_calc(doc.to_dict().get(amount_field_str, 0), '+', change)
		else:
			new_value = acc_calc(doc.to_dict().get(amount_field_str, 0), '+', change, rounding)

		if new_value < 0:
			raise NotEnoughTokenException()

		doc_ref.update({ amount_field: float(new_value), amount_field_str: str(new_value) })

		updated_doc = doc_ref.get().to_dict()
		return acc_calc(updated_doc.get(self.BOT_AMOUNT_STR, 0), '+', updated_doc.get(self.USER_AMOUNT_STR, 0))

	def __upsert(self, token, change, type = USER_NAME, rounding: int | None = None) -> Decimal:
		amount_field = self.BOT_AMOUNT if type != self.USER_NAME else self.USER_AMOUNT
		amount_field_str = self.BOT_AMOUNT_STR if type != self.USER_NAME else self.USER_AMOUNT_STR
		doc_ref = self.__wallet_collection.document(token)
		doc = doc_ref.get()

		if doc.exists:
			if rounding is None:
				new_value = acc_calc(doc.to_dict().get(amount_field_str, 0), '+', change)
			else:
				new_value = acc_calc(doc.to_dict().get(amount_field_str, 0), '+', change, rounding)

			if new_value < 0:
				raise NotEnoughTokenException()

			doc_ref.update({ amount_field: float(new_value), amount_field_str: str(new_value) })
		else:
			if rounding is None:
				new_value = acc_calc(0, '+', change)
			else:
				new_value = acc_calc(0, '+', change, rounding)
			doc_ref.set({ 'token_id': token, amount_field: float(new_value), amount_field_str: str(new_value) })

		updated_doc = doc_ref.get().to_dict()
		return acc_calc(updated_doc.get(self.BOT_AMOUNT_STR, 0), '+', updated_doc.get(self.USER_AMOUNT_STR, 0))

	def reserve_krakenbot_amount(self, token, amount):
		is_fiat = FirebaseToken().get(token).get('is_fiat', False)
		amount = Decimal(str(amount))
		self.__update(token, -amount, self.USER_NAME, 2 if is_fiat else None)
		self.__update(token, amount, self.BOT_NAME, 2 if is_fiat else None)

		wallet = self.__wallet_collection.document(token)
		return wallet.get().to_dict()

	def unreserve_krakenbot_amount(self, token, amount):
		is_fiat = FirebaseToken().get(token).get('is_fiat', False)
		amount = Decimal(str(amount))
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

	def set_bot_amount(self, token, bot_amount):
		doc_ref = self.__wallet_collection.document(token)
		doc_ref.update({self.BOT_AMOUNT: float(bot_amount), self.BOT_AMOUNT_STR: str(bot_amount)})
