import asyncio
import os
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from Krakenbot.exceptions import ServerErrorException, SessionExpiredException
from Krakenbot.models.auto_livetrade import AutoLiveTrade
from Krakenbot.models.backtest import BackTest
from Krakenbot.models.firebase_livetrade import FirebaseLiveTrade
from Krakenbot.models.firebase_users import FirebaseUsers
from Krakenbot.models.firebase_wallet import FirebaseWallet, NotEnoughTokenException
from Krakenbot.models.market import Market
from Krakenbot.models.news import News
from Krakenbot.models.trade import BadRequestException, NotAuthorisedException, Trade
from Krakenbot.models.update_candles import UpdateCandles
from Krakenbot.models.update_history_prices import UpdateHistoryPrices

class MarketView(APIView):
	def get(self, request: Request):
		try:
			result = Market().get_market(request)
			return Response(result, status=200)
		except BadRequestException:
			return Response(status=400)

class BackTestView(APIView):
	def post(self, request: Request):
		try:
			BackTest().backtest(request)
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)

class UpdateHistoryPricesView(APIView):
	def post(self, request: Request):
		try:
			asyncio.run(UpdateHistoryPrices().update(request))
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)

class TradeView(APIView):
	def post(self, request: Request):
		try:
			result = Trade().trade(request)
			return Response(result, status=200)
		except NotAuthorisedException:
			return Response(status=401)
		except BadRequestException:
			return Response(status=400)
		except NotEnoughTokenException:
			return Response(status=400)
		except SessionExpiredException:
			return Response(status=403)

class NewsView(APIView):
	def post(self, request: Request):
		try:
			News().fetch_news(request)
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)
		except BadRequestException:
			return Response(status=400)
		except ServerErrorException:
			return Response(status=500)

class AutoLiveTradeView(APIView):
	def post(self, request: Request):
		try:
			asyncio.run(AutoLiveTrade().livetrade(request))
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)

class UpdateCandlesView(APIView):
	def post(self, request: Request):
		try:
			UpdateCandles().update(request)
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)


class RecalibrateBotView(APIView):
	def post(self, request: Request):
		if os.environ.get('PYTHON_ENV') != 'development':
			return Response(status=404)

		uids = FirebaseUsers().get_all_user_id()
		for uid in uids:
			firebase_livetrade = FirebaseLiveTrade()
			livetrades = firebase_livetrade.filter(uid=uid, is_active=True)
			if len(livetrades) == 0:
				continue

			wallet = {}
			for livetrade in livetrades:
				cur_token = livetrade.get('cur_token', None)
				if cur_token is None:
					continue
				amount = livetrade.get('amount', 0)
				wallet[cur_token] = wallet.get(cur_token, 0) + amount

			firebase_wallet = FirebaseWallet(uid)
			for token in wallet:
				amount = wallet.get(token, 0)
				firebase_wallet.set_bot_amount(token, amount)
		return Response(status=200)
