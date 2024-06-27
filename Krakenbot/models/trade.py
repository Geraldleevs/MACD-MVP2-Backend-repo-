from Krakenbot.exceptions import BadRequestException, NotAuthorisedException
from Krakenbot.models.firebase_livetrade import FirebaseLiveTrade
from Krakenbot.models.firebase_wallet import FirebaseWallet
from rest_framework.request import Request
from rest_framework.authentication import get_authorization_header
from Krakenbot.models.market import Market
from django.utils import timezone
import firebase_admin.auth

class Trade:
	def parse_request(self, request: Request):
		uid = request.data.get('uid', '')
		from_token = request.data.get('from_token', '').upper()
		to_token = request.data.get('to_token', '').upper()
		from_amount = request.data.get('from_amount', '')
		jwt_token = get_authorization_header(request).decode('utf-8').split(' ')
		demo_init = request.data.get('demo_init', '')
		livetrade = request.data.get('livetrade', '').upper()
		strategy = request.data.get('strategy', '')
		timeframe = request.data.get('timeframe', '')

		if uid == '' or len(jwt_token) < 2:
			raise NotAuthorisedException()

		try:
			if uid != firebase_admin.auth.verify_id_token(jwt_token[1])['uid']:
				raise NotAuthorisedException()
		except Exception:
			raise NotAuthorisedException()

		return (
			uid,
			from_token,
			to_token,
			from_amount,
			demo_init,
			livetrade,
			strategy,
			timeframe
		)

	def trade(self, request: Request):
		(
			uid,
			from_token,
			to_token,
			from_amount,
			demo_init,
			livetrade,
			strategy,
			timeframe
		) = self.parse_request(request)
		firebase = FirebaseWallet(uid)

		if demo_init == 'demo_init':
			try:
				firebase.demo_init(from_token, float(from_amount))
			except ValueError:
				firebase.demo_init(from_token, 10000)
			return

		if livetrade == 'LIVETRADE':
			try:
				from_amount = float(from_amount)
				livetrade_id = FirebaseLiveTrade(uid).create({
					'uid': uid,
					'start_time': timezone.now(),
					'strategy': strategy,
					'timeframe': timeframe,
					'token_id': to_token,
					'amount': from_amount,
					'is_active': True
				})
				firebase.update(from_token, -from_amount)
				return {
					'id': livetrade_id,
					'strategy': strategy,
					'timeframe': timeframe,
					'token_id': to_token,
					'amount': from_amount,
				}
			except ValueError:
				raise BadRequestException()

		try:
			price = Market().get_market(convert_from=from_token, convert_to=to_token)[0]
			from_amount = float(from_amount)
			to_amount = from_amount * price['price']
		except IndexError:
			raise BadRequestException()
		except ValueError:
			raise BadRequestException()
		except KeyError:
			raise BadRequestException()

		transaction = firebase.trade(from_token, from_amount, to_token, to_amount)
		return transaction
