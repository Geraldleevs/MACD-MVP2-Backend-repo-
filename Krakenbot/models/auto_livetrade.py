from Krakenbot.Realtime_Backtest import apply_backtest, get_livetrade_result
from Krakenbot.exceptions import NotEnoughTokenException
from Krakenbot.models.firebase_livetrade import FirebaseLiveTrade
from rest_framework.request import Request
from Krakenbot.models.firebase_order_book import FirebaseOrderBook
from Krakenbot.models.firebase_token import FirebaseToken
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

	def __trade(self, trade_decisions: list[dict], market_prices: list[dict[str, str | float]], trade_type: str):
		firebase_order_book = FirebaseOrderBook()
		prices = { price['token']: price['price_str'] for price in market_prices }
		trade_count = 0

		for decision in trade_decisions:
			try:
				uid = decision['uid']
				from_token = decision['cur_token']
				to_token = decision['fiat'] if decision['cur_token'] == decision['token_id'] else decision['token_id']
				from_amount = decision['amount_str']
				bot_name = decision['name']
				bot_id = decision['livetrade_id']
				firebase_order_book.create_order(uid, from_token, to_token, prices[decision['token_id']], from_amount, bot_name, bot_id)
				trade_count += 1
			except KeyError:
				message = {
					'message': 'Livetrade Trading Fails due to Invalid Fields',
					'Livetrade': decision.get('livetrade_id'),
					'UID': decision.get('uid', 'No User Found'),
					'From': f'{decision.get('amount', 'No Amount')} {decision.get('cur_token', 'No Token Found')}',
					'Price': f'{prices.get(decision.get('token_id', ''), 'Price Not Found!')}',
				}
				log_warning(message)

			except NotEnoughTokenException:
				message = {
					'message': 'Livetrade Trading Fails due to Not Enough Token',
					'Livetrade': decision.get('livetrade_id'),
					'UID': decision.get('uid'),
					'From': f'{decision.get('amount')} {decision.get('cur_token')}',
					'Price': prices[decision['token_id']],
				}
				log_warning(message)

		log(f'Order Placed ({trade_type}): {trade_count}')

	async def __check_trade(self, timeframe: str, fiat: str):
		firebase_livetrade = FirebaseLiveTrade()
		livetrades = firebase_livetrade.filter(timeframe=timeframe, is_active=True, fiat=fiat, status='READY_TO_TRADE')
		if len(livetrades) == 0:
			return
		all_livetrade_token = { livetrade['token_id'] for livetrade in livetrades }

		all_tokens = FirebaseToken().filter(is_fiat=False)
		all_tokens = { token['id'] + fiat: token['id'] for token in all_tokens if token['id'] in all_livetrade_token }

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

		self.__trade(trade_decisions['buy'], Market().get_market(convert_from=fiat), 'Buy')
		self.__trade(trade_decisions['sell'], Market().get_market(convert_to=fiat), 'Sell')

	async def livetrade(self, request: Request):
		authenticate_scheduler_oicd(request)
		timeframe = request.data.get('timeframe', None)

		firebase_token = FirebaseToken()
		all_fiat = firebase_token.filter(is_fiat=True)

		for fiat in all_fiat:
			await self.__check_trade(timeframe, fiat['token_id'])
