from rest_framework.request import Request
from Krakenbot.exceptions import NotEnoughTokenException
from Krakenbot.models.firebase_livetrade import FirebaseLiveTrade
from Krakenbot.models.firebase_order_book import FirebaseOrderBook
from Krakenbot.models.firebase_token import FirebaseToken
from Krakenbot.models.market import Market
from Krakenbot.utils import acc_calc, authenticate_scheduler_oicd, log_error, log, log_warning

class CheckLossProfit:
	def __init__(self):
		self.firebase_livetrade = FirebaseLiveTrade()
		self.firebase_order_book = FirebaseOrderBook()

	def __check_take_profit(self, prices, take_profit_livetrades):
		order_created = 0
		take_profit_set = 0

		for livetrade in take_profit_livetrades:
			try:
				token_id = livetrade['token_id']
				fiat = livetrade['fiat']
				cur_token = livetrade['cur_token']
				price = prices.get(f'{token_id}{fiat}')
				if price is None:
					log_error(f'Check Stop Loss Failed due to token price not found! ({token_id}{fiat})')
					continue

				value = livetrade['amount_str']
				if cur_token == token_id:
					value = acc_calc(value, '*', price, 2)

				if acc_calc(value, '-', livetrade['take_profit']) < 0:
					continue

				if livetrade.get('order_id') is not None:
					self.firebase_order_book.cancel_order(livetrade['order_id'])

				livetrade_id = livetrade['livetrade_id']
				bot_name = livetrade['name']
				if cur_token == token_id:
					uid = livetrade['uid']
					amount = livetrade['amount_str']
					self.firebase_order_book.create_order(uid, cur_token, fiat, price, amount, bot_name, livetrade_id)
					order_created += 1

				self.firebase_livetrade.taking_profit(livetrade_id)
				take_profit_set += 1

			except KeyError:
				message = {
					'message': 'Take Profit Fails due to Invalid Fields',
					'Livetrade': livetrade.get('livetrade_id'),
					'UID': livetrade.get('uid', 'No User Found'),
					'Take Profit': livetrade.get('take_profit'),
				}
				log_warning(message)

			except NotEnoughTokenException:
				message = {
					'message': 'Take Profit Fails due to Not Enough Token',
					'Livetrade': livetrade.get('livetrade_id'),
					'UID': livetrade.get('uid'),
					'Take Profit': livetrade.get('take_profit'),
				}
				log_warning(message)


		log(f'Take Profit Set: {take_profit_set}; Order Created: {order_created}')

	def __check_stop_loss(self, prices, stop_loss_livetrades):
		order_created = 0
		stop_loss_set = 0

		for livetrade in stop_loss_livetrades:
			try:
				token_id = livetrade['token_id']
				fiat = livetrade['fiat']
				cur_token = livetrade['cur_token']
				price = prices.get(f'{token_id}{fiat}')
				if price is None:
					log_error(f'Check Stop Loss Failed due to token price not found! ({token_id}{fiat})')
					continue

				value = livetrade['amount_str']
				if cur_token == token_id:
					value = acc_calc(value, '*', price, 2)

				if acc_calc(value, '-', livetrade['stop_loss']) > 0:
					continue

				if livetrade.get('order_id') is not None:
					self.firebase_order_book.cancel_order(livetrade['order_id'])

				livetrade_id = livetrade['livetrade_id']
				bot_name = livetrade['name']
				if cur_token == token_id:
					uid = livetrade['uid']
					amount = livetrade['amount_str']
					self.firebase_order_book.create_order(uid, cur_token, fiat, price, amount, bot_name, livetrade_id)
					order_created += 1

				self.firebase_livetrade.stop_loss_pause(livetrade_id)
				stop_loss_set += 1

			except KeyError:
				message = {
					'message': 'Stop Loss Fails due to Invalid Fields',
					'Livetrade': livetrade.get('livetrade_id'),
					'UID': livetrade.get('uid', 'No User Found'),
					'Stop Loss': livetrade.get('stop_loss'),
				}
				log_warning(message)

			except NotEnoughTokenException:
				message = {
					'message': 'Stop Loss Fails due to Not Enough Token',
					'Livetrade': livetrade.get('livetrade_id'),
					'UID': livetrade.get('uid'),
					'Stop Loss': livetrade.get('stop_loss'),
				}
				log_warning(message)

		log(f'Stop Loss Set: {stop_loss_set}; Order Created: {order_created}')

	def __get_livetrades_and_prices(self):
		take_profit_livetrades = self.firebase_livetrade.filter(is_active=True, has_take_profit=True, taken_profit=False)
		stop_loss_livetrades = self.firebase_livetrade.filter(is_active=True, has_stop_loss=True, stopped_loss=False)

		fiats = FirebaseToken().filter(is_fiat=True)
		prices = {}
		for fiat in fiats:
			market_prices = Market().get_market(convert_to=fiat)
			market_prices = { f'{market_price['token']}{fiat}': market_price['price_str'] for market_price in market_prices }
			prices = { **prices, **market_prices }

		return prices, take_profit_livetrades, stop_loss_livetrades

	def check(self, request: Request):
		authenticate_scheduler_oicd(request)
		prices, take_profit_livetrades, stop_loss_livetrades = self.__get_livetrades_and_prices()

		self.__check_take_profit(prices, take_profit_livetrades)
		self.__check_stop_loss(prices, stop_loss_livetrades)
