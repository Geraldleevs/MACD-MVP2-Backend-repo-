from Krakenbot.exceptions import BadRequestException, NotAuthorisedException
from Krakenbot.models.firebase_wallet import FirebaseWallet
from rest_framework.request import Request
from rest_framework.authentication import get_authorization_header
from Krakenbot.models.market import Market
import firebase_admin.auth

class Trade:
	def parse_request(self, request: Request):
		uid = request.data.get('uid', '')
		from_token = request.data.get('from_token', '').upper()
		to_token = request.data.get('to_token', '').upper()
		from_amount = request.data.get('from_amount', '')
		jwt_token = get_authorization_header(request).decode('utf-8').split(' ')

		if uid == '' or len(jwt_token) < 2:
			raise NotAuthorisedException()

		try:
			if uid != firebase_admin.auth.verify_id_token(jwt_token[1])['uid']:
				raise NotAuthorisedException()
		except Exception:
			raise NotAuthorisedException()

		return (uid, from_token, to_token, from_amount)

	def trade(self, request: Request):
		(uid, from_token, to_token, from_amount) = self.parse_request(request)
		firebase = FirebaseWallet(uid)

		try:
			price = Market().get_market(convert_from=from_token, convert_to=to_token)[0]
			from_amount = float(from_amount)
			print('price', price)
			to_amount = from_amount * price['price']
		except IndexError:
			raise BadRequestException()
		except ValueError:
			raise BadRequestException()
		except KeyError:
			raise BadRequestException()

		transaction = firebase.trade(from_token, from_amount, to_token, to_amount)
		return transaction
