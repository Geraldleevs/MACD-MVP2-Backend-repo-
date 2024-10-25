from datetime import datetime
from typing import Literal
from Krakenbot import settings
from google.cloud.firestore_v1.base_query import FieldFilter
from django.utils import timezone
from Krakenbot.exceptions import BadRequestException
from Krakenbot.models.firebase_livetrade import FirebaseLiveTrade
from Krakenbot.models.firebase_wallet import FirebaseWallet
from Krakenbot.utils import acc_calc

class FirebaseOrderBook:
	__OPEN_STATUS = 'OPEN'
	__COMPLETED_STATUS = 'COMPLETED'
	__CANCELLED_STATUS = 'CANCELLED'

	def __init__(self):
		self.__order_book = settings.firebase.collection(u'order_book')

	def create_order(self, uid, from_token, to_token, price, volume, created_by = 'USER', bot_id = None):
		if created_by == 'USER':
			FirebaseWallet(uid).hold_token_for_order(from_token, volume)

		new_order = {
			'uid': uid,
			'from_token': from_token,
			'to_token': to_token,
			'price': float(price),
			'price_str': str(price),
			'volume': str(volume),
			'created_time': timezone.now(),
			'closed_time': None,
			'status': self.__OPEN_STATUS,
			'created_by': created_by,
			'bot_id': bot_id,
		}

		doc_ref = self.__order_book.document()
		doc_ref.set(new_order)
		doc_ref.update({ 'order_id': doc_ref.id })

		if bot_id is not None:
			FirebaseLiveTrade(uid).update_status(bot_id, 'ORDER_PLACED', doc_ref.id)

		return { **doc_ref.get().to_dict() }

	def cancel_order(self, id):
		doc_ref = self.__order_book.document(id)
		doc = doc_ref.get()

		if not doc.exists or doc.to_dict().get('status') != self.__OPEN_STATUS:
			raise BadRequestException()

		order_data = doc.to_dict()
		if doc.to_dict().get('created_by', 'USER') == 'USER':
			FirebaseWallet(order_data['uid']).release_token_hold(order_data['from_token'], order_data['volume'])

		update_data = {
			'closed_time': timezone.now(),
			'status': self.__CANCELLED_STATUS,
		}
		doc_ref.update(update_data)
		return { **doc_ref.get().to_dict(), 'id': doc_ref.id }

	def complete_order(self, id):
		doc_ref = self.__order_book.document(id)
		doc = doc_ref.get()

		if not doc.exists or doc.to_dict().get('status') != self.__OPEN_STATUS:
			raise BadRequestException()

		order_data = doc.to_dict()
		uid = order_data['uid']
		from_token = order_data['from_token']
		from_amount = order_data['volume']
		to_token = order_data['to_token']
		to_amount = acc_calc(from_amount, '*', order_data['price_str'])
		created_by = order_data.get('created_by', 'USER')
		bot_id = order_data.get('bot_id')
		transaction = FirebaseWallet(uid).complete_order(from_token, from_amount, to_token, to_amount, created_by, bot_id)

		if created_by != 'USER' and bot_id is not None:
			firebase_livetrade = FirebaseLiveTrade(uid)
			livetrade_details = firebase_livetrade.get(bot_id)
			status = livetrade_details['status']
			stopping_loss = status == firebase_livetrade.STOPPED_LOSS_STATUS
			taking_profit = status == firebase_livetrade.TAKING_PROFIT_STATUS
			if taking_profit or stopping_loss:
				cur_token = livetrade_details['cur_token']
				amount = livetrade_details['amount_str']
				firebase_livetrade.close(bot_id)
				FirebaseWallet(uid).unreserve_krakenbot_amount(cur_token, amount)
			else:
				firebase_livetrade.update_status(bot_id, 'READY_TO_TRADE')
			firebase_livetrade.update(bot_id, {
				'amount': float(transaction['to_amount']),
				'amount_str': str(transaction['to_amount_str']),
				'cur_token': transaction['to_token']
			})

		update_data = {
			'closed_time': timezone.now(),
			'status': self.__COMPLETED_STATUS,
			'transaction_id': transaction['id'],
		}
		doc_ref.update(update_data)
		return { **doc_ref.get().to_dict(), 'id': doc_ref.id }

	def filter(self, since: datetime = None, before: datetime = None, status: Literal['OPEN', 'CANCELLED', 'CLOSED', 'ALL'] = 'ALL', uid: str = None):
		query = self.__order_book

		match (status):
			case 'OPEN':
				query = query.where(filter=FieldFilter('status', '==', self.__OPEN_STATUS))

			case 'CANCELLED':
				query = query.where(filter=FieldFilter('status', '==', self.__CANCELLED_STATUS))

			case 'CLOSED':
				query = query.where(filter=FieldFilter('status', '==', self.__COMPLETED_STATUS))

		if since is not None:
			query = query.where(filter=FieldFilter('created_time', '>=', since))

		if before is not None:
			query = query.where(filter=FieldFilter('created_time', '<=', before))

		if uid is not None:
			query = query.where(filter=FieldFilter('uid', '==', uid))

		query = query.order_by('created_time')
		docs = query.stream()
		return [{ **doc.to_dict(), 'id': doc.id } for doc in docs]

	def get(self, id):
		doc_ref = self.__order_book.document(id)
		doc = doc_ref.get()
		return { **doc.to_dict(), 'id': doc.id }
