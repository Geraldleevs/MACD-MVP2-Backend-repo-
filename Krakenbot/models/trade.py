from Krakenbot.exceptions import BadRequestException, NotAuthorisedException
from Krakenbot.models.firebase_wallet import FirebaseWallet
from rest_framework.request import Request
from rest_framework.authentication import get_authorization_header
from Krakenbot.models.market import Market
import firebase_admin.auth

class Trade:
	def parse_request(self, request: Request):
		trade_type = request.data.get('trade_type', '').upper()
		session_id = request.data.get('session_id', '')
		uid = request.data.get('uid', '')
		token_id = request.data.get('token_id', '').upper()
		amount = request.data.get('amount', '')
		value = request.data.get('value', '')
		jwt_token = get_authorization_header(request).decode('utf-8').split(' ')

		if uid == '' or len(jwt_token) < 2:
			raise NotAuthorisedException()

		try:
			if uid != firebase_admin.auth.verify_id_token(jwt_token[1])['uid']:
				raise NotAuthorisedException()
		except Exception:
			raise NotAuthorisedException()

		return (trade_type, session_id, uid, token_id, amount, value)

	def trade(self, request: Request):
		(trade_type, session_id, uid, token_id, amount, value) = self.parse_request(request)
		firebase = FirebaseWallet(uid)

		'''
		# This code is for reserving token price for 5 mins for user to buy
		if trade_type == 'RESERVE':
			try:
				price = Market().get_market(token_id=token_id)[0]['price']
				session = firebase.create_price_session(token_id, price)
				return session
			except IndexError:
				raise BadRequestException()

		'''
		try:
			amount = float(amount)
			value = float(value)
		except ValueError:
			raise BadRequestException()

		if (trade_type != 'BUY' and trade_type != 'SELL') or amount <= 0 or value <= 0 or token_id == '' or session_id == '':
			raise BadRequestException()

		'''
		# This code is for fetching reserved token price for user to buy, to prevent user tricking the system
		price = firebase.fetch_session_price(session_id, token_id)

		if round(amount * price, 2) != value:
			raise BadRequestException()
		'''

		if trade_type == 'BUY':
			firebase.buy(token_id, amount, value)
		elif trade_type == 'SELL':
			firebase.sell(token_id, amount, value)

		firebase.close_session(session_id)
		firebase.clear_expired_session()
		return firebase.get_wallet(token_id)[0]
