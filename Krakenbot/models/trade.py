import os
from Krakenbot.exceptions import BadRequestException, NotAuthorisedException
from Krakenbot.models.firebase_livetrade import FirebaseLiveTrade
from Krakenbot.models.firebase_order_book import FirebaseOrderBook
from Krakenbot.models.firebase_wallet import FirebaseWallet
from Krakenbot.utils import acc_calc
from rest_framework.request import Request
from rest_framework.authentication import get_authorization_header
from Krakenbot.models.market import Market
from django.utils import timezone
import firebase_admin.auth

class Trade:
	def __init__(self):
		try:
			self.demo_amount = float(os.environ.get('DEMO_ACCOUNT_AMOUNT', '10000'))
		except ValueError:
			self.demo_amount = 10000

	def parse_request(self, request: Request):
		uid = request.data.get('uid', '')
		from_token = request.data.get('from_token', '').upper()
		to_token = request.data.get('to_token', '').upper()
		from_amount = str(request.data.get('from_amount', ''))
		jwt_token = get_authorization_header(request).decode('utf-8').split(' ')
		demo_init = request.data.get('demo_init', '')
		livetrade = request.data.get('livetrade', '').upper()
		livetrade_id = request.data.get('livetrade_id', '')
		take_profit = request.data.get('take_profit', None)
		stop_loss = request.data.get('stop_loss', None)
		strategy = request.data.get('strategy', '')
		timeframe = request.data.get('timeframe', '')
		order = request.data.get('order', '').upper()
		order_price = request.data.get('order_price', '0')
		order_id = request.data.get('order_id', '')
		order_price_reverse = request.data.get('order_price_reverse', 'false').lower() == 'true'

		if uid == '' or len(jwt_token) < 2:
			raise NotAuthorisedException()

		try:
			if order == 'ORDER':
				float(order_price)

			if livetrade == 'UPDATE' and take_profit is not None:
				take_profit = float(take_profit)
				if take_profit < 0:
					raise ValueError()
			if livetrade == 'UPDATE' and stop_loss is not None:
				stop_loss = float(stop_loss)
				if stop_loss < 0:
					raise ValueError()
		except ValueError:
			raise BadRequestException()

		try:
			if uid != firebase_admin.auth.verify_id_token(jwt_token[1])['uid']:
				raise NotAuthorisedException()
		except Exception:
			raise NotAuthorisedException()

		return {
			'uid': uid,
			'from_token': from_token,
			'to_token': to_token,
			'from_amount': from_amount,
			'demo_init': demo_init,
			'livetrade': livetrade,
			'livetrade_id': livetrade_id,
			'take_profit': take_profit,
			'stop_loss': stop_loss,
			'strategy': strategy,
			'timeframe': timeframe,
			'order': order,
			'order_price': order_price,
			'order_id': order_id,
			'order_price_reverse': order_price_reverse,
		}

	def livetrade(self, request):
		uid = request['uid']
		livetrade = request['livetrade']
		take_profit = request['take_profit']
		stop_loss = request['stop_loss']
		from_amount = request['from_amount']
		strategy = request['strategy']
		timeframe = request['timeframe']
		from_token = request['from_token']
		to_token = request['to_token']
		livetrade_id = request['livetrade_id']
		firebase_wallet = FirebaseWallet(uid)
		firebase_livetrade = FirebaseLiveTrade(uid)

		match (livetrade):
			case 'RESERVE':
				try:
					livetrade_id = firebase_livetrade.create({
						'uid': uid,
						'start_time': timezone.now(),
						'strategy': strategy,
						'timeframe': timeframe,
						'cur_token': from_token,
						'fiat': from_token,
						'token_id': to_token,
						'initial_amount': float(from_amount),
						'initial_amount_str': from_amount,
						'amount': float(from_amount),
						'amount_str': from_amount,
						'is_active': True,
						'take_profit': take_profit,
						'stop_loss': stop_loss,
					})
					firebase_wallet.reserve_krakenbot_amount(from_token, from_amount)
					return {
						'id': livetrade_id,
						'strategy': strategy,
						'timeframe': timeframe,
						'fiat': from_token,
						'token_id': to_token,
						'amount': from_amount,
						'take_profit': take_profit,
						'stop_loss': stop_loss,
					}
				except ValueError:
					raise BadRequestException()

			case 'UPDATE':
				if not firebase_livetrade.has(livetrade_id):
					raise BadRequestException()
				if take_profit is not None and stop_loss is not None:
					firebase_livetrade.update_take_profit_stop_loss(livetrade_id, take_profit, stop_loss)
				elif take_profit is not None:
					firebase_livetrade.update_take_profit(livetrade_id, take_profit)
				elif stop_loss is not None:
					firebase_livetrade.update_stop_loss(livetrade_id, stop_loss)

			case 'UNRESERVE' | 'SELL':
				if not firebase_livetrade.has(livetrade_id):
					raise BadRequestException()
				livetrade_details = firebase_livetrade.get(livetrade_id)
				cur_token = livetrade_details['cur_token']
				amount = livetrade_details['amount_str']
				status = livetrade_details.get('status')
				order_id = livetrade_details.get('order_id')

				if status == 'ORDER_PLACED':
					FirebaseOrderBook().cancel_order(order_id)

				firebase_livetrade.close(livetrade_id)
				firebase_wallet.unreserve_krakenbot_amount(cur_token, amount)

				if livetrade == 'SELL':
					return self.convert(uid, cur_token, amount, to_token)

	def convert(self, uid, from_token, from_amount, to_token):
		if from_token == to_token:
			return
		try:
			firebase = FirebaseWallet(uid)
			price = Market().get_market(convert_from=from_token, convert_to=to_token)[0]['price_str']
			to_amount = acc_calc(from_amount, '*', price)
			transaction = firebase.trade_by_user(from_token, from_amount, to_token, to_amount)
			return transaction
		except (IndexError, ValueError, KeyError):
			raise BadRequestException()

	def trade(self, request: Request):
		request = self.parse_request(request)

		uid = request['uid']
		from_token = request['from_token']
		from_amount = request['from_amount']
		to_token = request['to_token']
		if request['demo_init'] == 'demo_init':
			FirebaseWallet(uid).demo_init(from_token, self.demo_amount)
		elif request['livetrade'] != '':
			return self.livetrade(request)
		elif request['order'] == 'ORDER':
			price = request['order_price']
			if request['order_price_reverse']:
				price = acc_calc(1, '/', price)
			return FirebaseOrderBook().create_order(uid, from_token, to_token, price, from_amount)
		elif request['order'] == 'CANCEL':
			order_id = request['order_id']
			firebase_order_book = FirebaseOrderBook()
			if firebase_order_book.get(order_id).get('created_by', 'USER') != 'USER':
				raise NotAuthorisedException()
			return firebase_order_book.cancel_order(order_id)
		else:
			return self.convert(uid, from_token, from_amount, to_token)
