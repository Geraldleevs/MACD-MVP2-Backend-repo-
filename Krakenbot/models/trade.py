import os
from Krakenbot.exceptions import BadRequestException, NotAuthorisedException
from Krakenbot.models.firebase_livetrade import FirebaseLiveTrade
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
		strategy = request.data.get('strategy', '')
		timeframe = request.data.get('timeframe', '')

		if uid == '' or len(jwt_token) < 2:
			raise NotAuthorisedException()

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
			'strategy': strategy,
			'timeframe': timeframe
		}

	def livetrade(self, request):
		uid = request['uid']
		livetrade = request['livetrade']
		from_amount = request['from_amount']
		strategy = request['strategy']
		timeframe = request['timeframe']
		from_token = request['from_token']
		to_token = request['to_token']
		livetrade_id = request['livetrade_id']
		firebase_wallet = FirebaseWallet(uid)
		firebase_livetrade = FirebaseLiveTrade(uid)

		if livetrade == 'RESERVE':
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
					'is_active': True
				})
				firebase_wallet.reserve_krakenbot_amount(from_token, from_amount)
				return {
					'id': livetrade_id,
					'strategy': strategy,
					'timeframe': timeframe,
					'fiat': from_token,
					'token_id': to_token,
					'amount': from_amount,
				}
			except ValueError:
				raise BadRequestException()
		elif livetrade in ['UNRESERVE', 'SELL']:
			if not firebase_livetrade.has(livetrade_id):
				raise BadRequestException()
			livetrade_details = firebase_livetrade.get(livetrade_id)
			cur_token = livetrade_details['cur_token']
			amount = livetrade_details['amount_str']
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

		if request['demo_init'] == 'demo_init':
			FirebaseWallet(request['uid']).demo_init(request['from_token'], self.demo_amount)
		elif request['livetrade'] != '':
			return self.livetrade(request)
		else:
			return self.convert(request['uid'], request['from_token'], request['from_amount'], request['to_token'])
