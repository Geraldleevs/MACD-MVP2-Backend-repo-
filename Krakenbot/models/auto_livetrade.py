import os
from datetime import datetime, timedelta
from random import randint
from Krakenbot.exceptions import NotEnoughTokenException
from Krakenbot.models.firebase_livetrade import FirebaseLiveTrade
from django.utils import timezone
from rest_framework.request import Request
from Krakenbot.models.firebase_token import FirebaseToken
from Krakenbot.models.firebase_wallet import FirebaseWallet
from Krakenbot.models.market import Market
from Krakenbot.utils import authenticate_scheduler_oicd

class AutoLiveTrade:
	INTERVAL = {
		'1min': 1,
		'5min': 5,
		'15min': 15,
		'30min': 30,
		'1h': 60,
		'4h': 240,
		'1d': 1440,
	}

	def __init__(self):
		self.FIAT = os.environ.get('FIAT', 'GBP')

	def __apply_backtest(self, pairs: list[str], intervals: list[int], since: datetime) -> dict[str, dict[str, int]]:
		# Parse the since here from datetime to timestamp to call Kraken API
		since = since.timestamp()

		results = {}

		for pair in pairs:
			results[pair] = {}
			for interval in intervals:
				results[pair][str(interval)] = round(randint(-1, 1)) # Simulate a random number among [-1, 0, 1]: [Sell, Do nothing, Buy]

		return results

	def __trade(self, trade_decisions: list[dict], market_prices: list[dict[str, str | float]]):
		firebase_livetrade = FirebaseLiveTrade()
		prices = { price['token']: price['price'] for price in market_prices }

		for decision in trade_decisions:
			try:
				from_token = decision['cur_token']
				to_token = self.FIAT if decision['cur_token'] == decision['token_id'] else decision['token_id']
				from_amount = decision['amount']
				to_amount = from_amount * prices[decision['token_id']]
				trade_result = FirebaseWallet(decision['uid']).trade_by_krakenbot(from_token, from_amount, to_token, to_amount)
				firebase_livetrade.update(decision['livetrade_id'], { 'amount': trade_result['to_amount'], 'cur_token': trade_result['to_token'] })
			except KeyError:
				pass
			except NotEnoughTokenException:
				pass

	async def livetrade(self, request: Request):
		authenticate_scheduler_oicd(request)
		timeframe = request.data.get('timeframe', None)

		firebase_livetrade = FirebaseLiveTrade()
		livetrades = firebase_livetrade.filter(timeframe=timeframe, is_active=True)

		all_tokens = FirebaseToken().all()
		all_tokens = { token['id'] + self.FIAT: token['id'] for token in all_tokens if token['is_fiat'] == False }

		since = timezone.now() - timedelta(days=366)

		backtest_result = self.__apply_backtest(all_tokens.keys(), [self.INTERVAL[timeframe]], since)
		results = { all_tokens[pair]: value for (pair, value) in backtest_result.items() }

		trade_decisions = { 'buy': [], 'sell': [] }

		for livetrade in livetrades:
			try:
				decision = results[livetrade['token_id']][str(self.INTERVAL[timeframe])]

				if decision == 0:
					print("Do Nothing")
					continue
				elif decision == -1 and livetrade['cur_token'] == livetrade['token_id']:
					print("Sell")
					trade_decisions['sell'].append(livetrade)
					pass
				elif decision == 1 and livetrade['cur_token'] != livetrade['token_id']:
					print("Buy")
					trade_decisions['buy'].append(livetrade)
					pass
			except KeyError:
				pass

		self.__trade(trade_decisions['buy'], Market().get_market(convert_from=self.FIAT))
		self.__trade(trade_decisions['sell'], Market().get_market(convert_to=self.FIAT))
