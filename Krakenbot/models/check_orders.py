from Krakenbot.exceptions import NotEnoughTokenException, TokenNotFoundException
from rest_framework.request import Request
from Krakenbot.models.firebase_order_book import FirebaseOrderBook
from Krakenbot.models.market import Market
from Krakenbot.utils import acc_calc, authenticate_scheduler_oicd, log_warning, log

class CheckOrders:
	def __trade(self, success_pairs):
		order_book = FirebaseOrderBook()
		trade_count = 0

		for success_pair in success_pairs:
			try:
				order_book.complete_order(success_pair)
				trade_count += 1
			except KeyError:
				order_details = order_book.get(success_pair)
				to_amount = acc_calc(order_details.get('volume', '0'), '*', order_details.get('price_str', '0'))
				message = {
					'message': 'Order Fails due to Invalid Fields',
					'Order ID': order_details.get('id'),
					'UID': order_details.get('uid'),
					'From': f'{order_details.get('volume')} {order_details.get('from_token')}',
					'To': f'{str(to_amount)} {order_details.get('to_token')}',
				}
				log_warning(message)
			except NotEnoughTokenException:
				order_details = order_book.get(success_pair)
				to_amount = acc_calc(order_details.get('volume', '0'), '*', order_details.get('price_str', '0'))
				message = {
					'message': 'Order Fails due to Not Enough Token',
					'Order ID': order_details.get('id'),
					'UID': order_details.get('uid'),
					'From': f'{order_details.get('volume')} {order_details.get('from_token')}',
					'To': f'{str(to_amount)} {order_details.get('to_token')}',
				}
				log_warning(message)

		log(f'Trade Success: {trade_count}')

	def __check_orders_success(self, order_prices):
		market = Market()
		success_pair = []
		for from_token in order_prices:
			prices = market.get_market(convert_from=from_token, include_inactive='INCLUDE')
			prices = { price['token']: price['price_str'] for price in prices }

			for to_token in order_prices[from_token]:
				market_price = prices.get(to_token, None)
				if market_price is None:
					raise TokenNotFoundException()

				for (order_price, order_id) in order_prices[from_token][to_token]:
					if acc_calc(order_price, '-', market_price) < 0:
						continue
					success_pair.append(order_id)

		return success_pair


	def __get_orders(self):
		order_book = FirebaseOrderBook()
		orders = order_book.filter(status='OPEN')
		token_pair_price = {}
		for order in orders:
			order_id = order['id']
			price = order['price']
			from_token = order['from_token']
			to_token = order['to_token']
			if from_token not in token_pair_price:
				token_pair_price[from_token] = {}
			if to_token not in token_pair_price[from_token]:
				token_pair_price[from_token][to_token] = []
			token_pair_price[from_token][to_token].append((price, order_id))

		return token_pair_price

	def check(self, request: Request):
		authenticate_scheduler_oicd(request)
		order_prices = self.__get_orders()
		success_pairs = self.__check_orders_success(order_prices)
		self.__trade(success_pairs)
