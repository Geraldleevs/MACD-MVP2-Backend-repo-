import os
import pandas as pd
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

	# TODO: This function should be removed once the Branch `Demo-Branch-WIP-NEW` is merged
	def __apply_backtest(self, pairs: list[str], intervals: list[int], since: datetime) -> dict[str, dict[str, pd.DataFrame]]:
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

		# TODO: Replace this with any other time duration, this is for backtest since 366 days before
		since = timezone.now() - timedelta(days=366)

		# TODO: This function call should be replaced by the `apply_backtest` function in `Realtime_Backtest.py` from Branch `Demo-Branch-WIP-NEW`
		# results = apply_backtest(all_tokens.keys(), [self.INTERVAL[timeframe]], since)
		results = self.__apply_backtest(all_tokens.keys(), [self.INTERVAL[timeframe]], since)

		results = { all_tokens[pair]: value for (pair, value) in results.items() } # To replace pair with just token id, e.g. BTCGBP -> BTC

		trade_decisions = { 'buy': [], 'sell': [] }

		for livetrade in livetrades:
			try:
				## TODO: Use `get_livetrade_result` from the Branch `Demo-Branch-WIP-NEW` to get the decision of buy/sell
				# decision = get_livetrade_result(results[livetrade['token_id']][str(self.INTERVAL[timeframe])], livetrade['strategy'])
				decision = results[livetrade['token_id']][str(self.INTERVAL[timeframe])]

				if decision == -1 and livetrade['cur_token'] == livetrade['token_id']:
					trade_decisions['sell'].append(livetrade)
				elif decision == 1 and livetrade['cur_token'] != livetrade['token_id']:
					trade_decisions['buy'].append(livetrade)
			except KeyError:
				pass

		self.__trade(trade_decisions['buy'], Market().get_market(convert_from=self.FIAT))
		self.__trade(trade_decisions['sell'], Market().get_market(convert_to=self.FIAT))
