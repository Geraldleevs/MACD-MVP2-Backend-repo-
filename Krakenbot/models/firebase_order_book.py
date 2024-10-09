from datetime import datetime
from typing import Literal
from Krakenbot import settings
from google.cloud.firestore_v1.base_query import FieldFilter
from django.utils import timezone
from Krakenbot.exceptions import BadRequestException
from Krakenbot.models.firebase_wallet import FirebaseWallet
from Krakenbot.utils import acc_calc

class FirebaseLiveTrade:
	__OPEN_STATUS = 'OPEN'
	__COMPLETED_STATUS = 'COMPLETED'
	__CANCELLED_STATUS = 'CANCELLED'

	def __init__(self):
		self.__order_book = settings.firebase.collection(u'order_book')

	def create_order(self, uid, from_token, to_token, price, volume):
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
		}

		doc_ref = self.__order_book.document()
		doc_ref.set(new_order)
		return { **doc_ref.get().to_dict(), 'id': doc_ref.id }

	def cancel_order(self, id):
		doc_ref = self.__order_book.document(id)
		doc = doc_ref.get()

		if not doc.exists or doc.to_dict().get('status') != self.__OPEN_STATUS:
			raise BadRequestException()

		order_data = doc.to_dict()
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
		FirebaseWallet(uid).complete_order(from_token, from_amount, to_token, to_amount)

		update_data = {
			'closed_time': timezone.now(),
			'status': self.__COMPLETED_STATUS,
		}
		doc_ref.update(update_data)
		return { **doc_ref.get().to_dict(), 'id': doc_ref.id }

	def filter(self, since: datetime = None, before: datetime = None, status: Literal['OPEN', 'CANCELLED', 'CLOSED', 'ALL'] = 'ALL', uid: str = None):
		query = self.__livetrade

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

		docs = query.stream()
		return [{ **doc.to_dict(), 'id': doc.id } for doc in docs]
