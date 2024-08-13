import os
from Krakenbot.Realtime_Backtest import apply_backtest, get_livetrade_result
from Krakenbot.exceptions import NotEnoughTokenException
from Krakenbot.models.firebase_livetrade import FirebaseLiveTrade
from rest_framework.request import Request
from Krakenbot.models.firebase_token import FirebaseToken
from Krakenbot.models.firebase_wallet import FirebaseWallet
from Krakenbot.models.market import Market
from Krakenbot.utils import authenticate_scheduler_oicd, log_warning, log

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

	def __trade(self, trade_decisions: list[dict], market_prices: list[dict[str, str | float]], trade_type: str):
		firebase_livetrade = FirebaseLiveTrade()
		prices = { price['token']: price['price'] for price in market_prices }
		trade_count = 0

		for decision in trade_decisions:
			try:
				from_token = decision['cur_token']
				to_token = self.FIAT if decision['cur_token'] == decision['token_id'] else decision['token_id']
				from_amount = decision['amount']
				to_amount = from_amount * prices[decision['token_id']]
				bot_name = decision['name']
				bot_id = decision['livetrade_id']
				trade_result = FirebaseWallet(decision['uid']).trade_by_krakenbot(from_token, from_amount, to_token, to_amount, bot_name, bot_id)
				firebase_livetrade.update(decision['livetrade_id'], { 'amount': trade_result['to_amount'], 'cur_token': trade_result['to_token'] })
				trade_count += 1
			except KeyError:
				message = {
					'message': 'Livetrade Trading Fails due to Invalid Fields',
					'Livetrade': decision.get('livetrade_id'),
					'UID': decision.get('uid', 'No User Found'),
					'From': f'{decision.get('amount', 'No Amount')} {decision.get('cur_token', 'No Token Found')}',
					'To': f'{decision.get('amount', 0) * prices.get(decision.get('token_id', ''), 0)} {self.FIAT if decision.get('cur_token', '1') == decision.get('token_id', '2') else decision.get('token_id', 'No Token Found')}',
				}
				log_warning(message)

			except NotEnoughTokenException:
				message = {
					'message': 'Livetrade Trading Fails due to Not Enough Token',
					'Livetrade': decision.get('livetrade_id'),
					'UID': decision.get('uid'),
					'From': f'{decision.get('amount')} {decision.get('cur_token')}',
					'To': f'{decision.get('amount') * prices.get(decision.get('token_id'))} {self.FIAT if decision.get('cur_token') == decision.get('token_id') else decision.get('token_id')}',
				}
				log_warning(message)

		log(f'Trade Count ({trade_type}): {trade_count}')

	async def livetrade(self, request: Request):
		authenticate_scheduler_oicd(request)
		timeframe = request.data.get('timeframe', None)

		firebase_livetrade = FirebaseLiveTrade()
		livetrades = firebase_livetrade.filter(timeframe=timeframe, is_active=True)

		all_tokens = FirebaseToken().all()
		all_tokens = { token['id'] + self.FIAT: token['id'] for token in all_tokens if token['is_fiat'] == False }

		results = await apply_backtest(all_tokens.keys(), [self.INTERVAL[timeframe]])
		results = { all_tokens[pair]: value for (pair, value) in results.items() } # To replace pair with just token id, e.g. BTCGBP -> BTC

		trade_decisions = { 'buy': [], 'sell': [] }

		for livetrade in livetrades:
			try:
				strategies = livetrade['strategy'].split(' (')[0]
				[strategy_1, strategy_2] = strategies.split(' & ')
				decision_1 = get_livetrade_result(results[livetrade['token_id']][str(self.INTERVAL[timeframe])], strategy_1)
				decision_2 = get_livetrade_result(results[livetrade['token_id']][str(self.INTERVAL[timeframe])], strategy_2)

				if decision_1 == decision_2 == -1 and livetrade['cur_token'] == livetrade['token_id']:
					trade_decisions['sell'].append(livetrade)
				elif decision_1 == decision_2 == 1 and livetrade['cur_token'] != livetrade['token_id']:
					trade_decisions['buy'].append(livetrade)
			except (KeyError, ValueError, IndexError):
				message = {
					'message': 'Livetrade Fails due to Unknown Strategy',
					'Livetrade': livetrade.get('livetrade_id', 'ID Not Found'),
					'Timeframe': timeframe,
					'Strategy': livetrade.get('strategy', 'Strategy Not Found'),
				}
				log_warning(message)

		self.__trade(trade_decisions['buy'], Market().get_market(convert_from=self.FIAT), 'Buy')
		self.__trade(trade_decisions['sell'], Market().get_market(convert_to=self.FIAT), 'Sell')
