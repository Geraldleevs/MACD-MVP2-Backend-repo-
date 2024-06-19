from Krakenbot.exceptions import BadRequestException, NotAuthorisedException
from Krakenbot.models.firebase_wallet import FirebaseWallet
from rest_framework.request import Request
from rest_framework.authentication import get_authorization_header
import firebase_admin.auth

class Trade:
	def parse_request(self, request: Request):
		trade_type = request.data.get('trade_type', '').upper()
		uid = request.data.get('uid', '')
		token_id = request.data.get('token_id', '').upper()
		amount = request.data.get('amount', '')
		value = request.data.get('value', '')
		jwt_token = get_authorization_header(request).decode('utf-8').split(' ')

		try:
			amount = float(amount)
			value = float(value)
		except ValueError:
			raise BadRequestException()

		if amount <= 0 or value <= 0 or token_id == '' or (trade_type != 'BUY' and trade_type != 'SELL'):
			raise BadRequestException()

		if uid == '' or len(jwt_token) < 2:
			raise NotAuthorisedException()

		try:
			if uid != firebase_admin.auth.verify_id_token(jwt_token[1])['uid']:
				raise NotAuthorisedException()
		except Exception:
			raise NotAuthorisedException()

		return (trade_type, uid, token_id, amount, value)

	def trade(self, request: Request):
		(trade_type, uid, token_id, amount, value) = self.parse_request(request)
		firebase = FirebaseWallet(uid)
		if trade_type == 'BUY':
			firebase.buy(token_id, amount, value)
		elif trade_type == 'SELL':
			firebase.sell(token_id, amount, value)
		return firebase.get_wallet(token_id)[0]
