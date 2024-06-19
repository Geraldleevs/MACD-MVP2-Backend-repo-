from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from Krakenbot.models.backtest import BackTest
from Krakenbot.models.firebase_wallet import NotEnoughTokenException
from Krakenbot.models.market import Market
from Krakenbot.models.trade import BadRequestException, NotAuthorisedException, Trade

class MarketView(APIView):
	def get(self, request: Request):
		result = Market().get_market(request)
		return Response(result, 200)

class BackTestView(APIView):
	def post(self, request: Request):
		try:
			result = BackTest().backtest(request)
			return Response(result, status=200)
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
