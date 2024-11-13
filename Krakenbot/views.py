from datetime import datetime, timedelta
from itertools import combinations
from typing import List, Literal
import asyncio
import aiohttp
import requests
import numpy as np
import pandas as pd

from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from Krakenbot import settings
from Krakenbot.exceptions import BadRequestException, DatabaseIncorrectDataException, NoUserSelectedException, NotAuthorisedException, ServerErrorException, NotEnoughTokenException
from Krakenbot.models.firebase import FirebaseAnalysis, FirebaseCandle, FirebaseLiveTrade, FirebaseNews, FirebaseOrderBook, FirebaseRecommendation, FirebaseToken, FirebaseUsers, FirebaseWallet, NewsField
from Krakenbot.MVP_Backtest import main as backtest, indicator_names
from Krakenbot.Realtime_Backtest import apply_backtest, get_livetrade_result
from Krakenbot.update_candles import main as update_candles
from Krakenbot.utils import acc_calc, authenticate_scheduler_oicd, authenticate_user_jwt, clean_kraken_pair, log, log_error, log_warning, usd_to_gbp


class MarketView(APIView):
	def get(self, request: Request):
		try:
			convert_from = request.query_params.get('convert_from', '').strip().upper()
			convert_to = request.query_params.get('convert_to', '').strip().upper()
			exclude = request.query_params.get('exclude', '').strip().upper()
			force_convert = request.query_params.get('force_convert', '').strip().upper()
			include_inactive = request.query_params.get('include_inactive', '').strip().upper()
			get_simulation = request.query_params.get('get_simulation', '').strip().upper()

			if get_simulation == 'GET SIMULATION':
				return SimulationView().get(request)

			result = self.get_market(convert_from, convert_to, exclude, force_convert, include_inactive)
			return Response(result, status=200)
		except BadRequestException:
			return Response(status=400)

	def get_market(self, convert_from = '', convert_to = '', exclude = '',
								force_convert: Literal['FORCE'] = '', include_inactive: Literal['INCLUDE'] = ''):
		''' force_convert can only be used when convert from/to GBP, but not specific pair '''

		convert_from = convert_from.upper()
		convert_to = convert_to.upper()
		exclude = exclude.upper()
		force_convert = force_convert.upper()
		include_inactive = include_inactive.upper()
		firebase_token = FirebaseToken()

		try:
			if convert_from != '':
				current_token = firebase_token.get(convert_from)
				reverse_price = False
			else:
				current_token = firebase_token.get(convert_to)
				reverse_price = True
			current_token = current_token['token_id']
		except Exception:
			raise BadRequestException()

		market = self.__fetch_kraken_pair(current_token, reverse_price)
		market.append({ 'token': current_token, 'price': 1, 'last_close': 1 }) # Add price for current token too

		specific_convert = convert_to != '' and not reverse_price
		if specific_convert:
			market = [price for price in market if price['token'] == convert_to]
		else:
			is_active = None if include_inactive == 'INCLUDE' else True
			other_tokens = firebase_token.filter(is_active=is_active)
			other_tokens = [token['token_id'] for token in other_tokens]
			market = [price for price in market if price['token'] in other_tokens]

		if exclude != '':
			market = [price for price in market if price['token'] != exclude]

		# Add string version of prices
		market = [{
			'token': price['token'],
			'price': float(price['price']),
			'last_close': float(price['last_close']),
			'price_str': str(price['price']),
			'last_close_str': str(price['last_close'])
		} for price in market]

		if specific_convert or force_convert != 'FORCE' or 'GBP' not in [convert_from, convert_to]:
			return market

		all_market_token = [price['token'] for price in market]
		usd_market = self.__fetch_kraken_pair('USD', reverse_price)
		usd_market = [price for price in usd_market if price['token'] in other_tokens and price['token'] not in all_market_token]
		usd_rate = asyncio.run(usd_to_gbp())
		if not reverse_price:
			usd_rate = acc_calc(1, '/', usd_rate)

		usd_market = [{
			'token': price['token'],
			'price': float(acc_calc(price['price'], '*', usd_rate)),
			'last_close': float(acc_calc(price['last_close'], '*', usd_rate)),
			'price_str': str(acc_calc(price['last_close'], '*', usd_rate)),
			'last_close_str': str(acc_calc(price['last_close'], '*', usd_rate))
		} for price in usd_market]

		return [*market, *usd_market]

	def __fetch_kraken_pair(self, token: str, reverse_price = False):
		try:
			result = requests.get(settings.KRAKEN_PAIR_API).json()

			if len(result['error']) > 0:
				return []

			result = clean_kraken_pair(result)
			result = self.__parse_kraken_pair(result, token, reverse_price)
			return result
		except Exception:
			return []

	def __get_price(self, result, property_path):
		price = result[property_path][0]
		last_open = result['last_close']
		if property_path == 'bid':
			try:
				price = acc_calc(1, '/', price)
			except ZeroDivisionError:
				price = 0
			try:
				last_open = acc_calc(1, '/', last_open)
			except ZeroDivisionError:
				last_open = 0
		return (price, last_open)

	def __parse_kraken_pair(self, kraken_result: dict[str, any], token: str, reverse_price: bool):
		for (pair, result) in kraken_result.items():
			kraken_result[pair] = {'ask': result['a'], 'bid': result['b'], 'last_close': result['o']}

		sell = 'bid' if reverse_price else 'ask'
		buy = 'ask' if reverse_price else 'bid'
		filtered_results: dict[str, any] = {}

		for (pair, result) in kraken_result.items():
			if (token is not None and token in pair):
				filtered_results[pair] = result

		results = {}
		for (pair, result) in filtered_results.items():
			if pair.startswith(token):
				(price, last_close) = self.__get_price(result, sell)
			elif pair.endswith(token):
				(price, last_close) = self.__get_price(result, buy)
			else:
				continue

			result_token = pair.replace(token, '')

			if result_token not in results:
				results[result_token] = (price, last_close)

		return [{ 'token': token, 'price': price, 'last_close': last_close } for (token, (price, last_close)) in results.items()]


class SimulationView(APIView):
	ALL_STRATEGIES = [f'{name_1} & {name_2}' for name_1, name_2 in combinations(indicator_names.values(), 2)]

	def get(self, request: Request):
		try:
			get_strategies = request.query_params.get('get_strategies', '').strip().upper()
			fiat = request.query_params.get('convert_from', settings.FIAT).strip().upper()
			token_id = request.query_params.get('convert_to', '').strip().upper()
			strategy = request.query_params.get('strategy', '')
			timeframe = request.query_params.get('timeframe', '')

			if get_strategies == 'GET STRATEGIES':
				return Response(self.ALL_STRATEGIES)

			if strategy != '' and strategy not in self.ALL_STRATEGIES:
				raise BadRequestException()
			if timeframe != '' and timeframe not in settings.TIMEFRAMES.keys():
				raise BadRequestException()

			firebase_token = FirebaseToken()
			fiat_token = firebase_token.filter(fiat, is_fiat=True)
			if len(fiat_token) < 1:
				raise BadRequestException()

			token = firebase_token.filter(token_id)
			if len(token) < 1:
				raise BadRequestException()

			token = token[0]
			history_prices = token.get('history_prices', {})
			history_dates = history_prices.get('times', [])
			history_prices = history_prices.get('data', [])

			if len(history_prices) < (5 * 24):
				raise BadRequestException()

			simulation_data = history_prices[-(6 * 24):-24] # -6d to -1d, not fetching previous 24 hours
			starting_time = history_dates[-(6 * 24)]
			starting_data = simulation_data[0]
			max_data = np.max(simulation_data)
			min_data = np.min(simulation_data)

			graph_max = max_data if max_data - starting_data > starting_data - min_data else starting_data + (starting_data - min_data)
			graph_min = min_data if max_data - starting_data < starting_data - min_data else starting_data - (max_data - starting_data)

			response = {
				'simulation_data': simulation_data,
				'graph_min': graph_min,
				'graph_max': graph_max
			}

			if strategy != '' and timeframe != '':
				response['backtest_decision'] = self.simulate_backtest(fiat, token_id, strategy, timeframe, starting_time)

			return Response(response, status=200)

		except BadRequestException:
			return Response(status=400)

	def simulate_backtest(self, fiat: str, token_id: str, strategy: str, timeframe: str, starting_time: datetime):
		interval = settings.INTERVAL_MAP[timeframe]
		candles = FirebaseCandle(f'{token_id}{fiat}', timeframe).fetch_since(starting_time)[:int(5 * 24 * 60 / interval)]
		candles = pd.DataFrame.from_dict(candles)

		strategy_1, strategy_2 = strategy.split(' & ')
		backtest_func = {strategy: func for (func, strategy) in indicator_names.items()}
		result_1 = backtest_func[strategy_1](candles)
		result_2 = backtest_func[strategy_2](candles)
		buy_signals = (result_1 == 1) & (result_2 == 1)
		sell_signals = (result_1 == -1) & (result_2 == -1)

		decisions = []
		empty_decision = [0] * int(interval / 60 - 1)
		for buy, sell in zip(buy_signals, sell_signals):
			if buy:
				decisions.extend([1, *empty_decision])
			elif sell:
				decisions.extend([-1, *empty_decision])
			else:
				decisions.extend([0, *empty_decision])

		return decisions


class BackTestView(APIView):
	def post(self, request: Request):
		try:
			authenticate_scheduler_oicd(request)
			self.backtest()
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)

	def backtest(self):
		firebase_analysis = FirebaseAnalysis()
		results = backtest().reset_index().to_numpy()

		firebase_token = FirebaseToken()
		all_tokens = firebase_token.filter(is_active=True)
		all_tokens = [price['token_id'] for price in all_tokens]

		now = timezone.now()
		results = [{
			'fiat': value[0].split(' | ')[0].split(':')[0],
			'token_id': value[0].split(' | ')[0].split(':')[1],
			'timeframe': value[0].split(' | ')[1],
			'strategy': value[1],
			'profit': value[2],
			'profit_percent': value[3],
			'risk': firebase_analysis.get_risk(value[0].split(' | ')[0].split(':')[1], settings.TIMEFRAMES[value[0].split(' | ')[1]], 'high'),
			'strategy_description': firebase_analysis.fetch_strategy_description(),
			'updated_on': now,
			**firebase_analysis.get_analysis(value[0].split(' | ')[0].split(':')[1], settings.TIMEFRAMES[value[0].split(' | ')[1]])
		} for value in results]

		results = [result for result in results if result['token_id'] in all_tokens]

		firebase = FirebaseRecommendation()
		firebase.delete_all()
		for result in results:
			firebase.create(result)


class UpdateHistoryPricesView(APIView):
	def post(self, request: Request):
		try:
			authenticate_scheduler_oicd(request)
			asyncio.run(self.update())
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)

	async def update(self):
		firebase = FirebaseToken()
		firebase_tokens = firebase.filter(is_active=None, is_fiat=False)
		pairs = [token.get('token_id') + settings.FIAT for token in firebase_tokens]
		pairs.append('GBPUSD')

		firebase.start_batch_write()
		coin_gecko_ids = { token.get('coingecko_id'): token.get('token_id') for token in firebase_tokens }
		metrics = await self.__fetch_gecko_metrics(coin_gecko_ids)
		for metric in metrics:
			firebase.update(metric, metrics[metric])

		firebase.update_history_prices(settings.FIAT, [timezone.now() - timedelta(days=7), timezone.now()], [1, 1])

		async with aiohttp.ClientSession() as session:
			tasks = [self.__fetch_kraken_ohlc(session, pair) for pair in pairs]
			results = await asyncio.gather(*tasks)
			results = [(pair.replace(settings.FIAT, ''), times, close_prices) for (pair, times, close_prices) in results if close_prices != [0, 0]]
			all_tokens = [token for (token, _, close_prices) in results if close_prices != [0, 0]]
			all_prices = {settings.FIAT: 1}

			usd_pairs = [
				token.get('token_id') + 'USD' for token in firebase.filter(is_active=None)
				if token.get('token_id') not in ['USD', settings.FIAT, *all_tokens]
			]

			if len(usd_pairs) > 0:
				tasks = [self.__fetch_kraken_ohlc(session, pair) for pair in usd_pairs]
				usd_results = await asyncio.gather(*tasks)
				usd_results = [(pair.replace('USD', ''), times, close_prices) for (pair, times, close_prices) in usd_results if close_prices != [0, 0]] # Skip failed tokens
				for (token, times, close_prices) in usd_results:
					usd_rate = await usd_to_gbp()
					close_prices = [acc_calc(close_price, '*', usd_rate) for close_price in close_prices]
					all_prices[token] = close_prices[-1]
					firebase.update_history_prices(token, times, close_prices)

			for (token, times, close_prices) in results:
				if close_prices == [0, 0]: # Skip failed tokens
					continue
				if token == 'USD':
					close_prices = [acc_calc(1, '/', price) for price in close_prices]
				firebase.update_history_prices(token, times, close_prices)
				all_prices[token] = close_prices[-1]
			firebase.commit_batch_write()

		self.__update_user_history(all_prices)

	async def __fetch_kraken_ohlc(self, session: aiohttp.ClientSession, pair: str):
		async with session.get(settings.KRAKEN_OHLC_API, params={'pair': pair, 'interval': settings.HISTORY_INTERVAL}) as response:
			if response.status == 200:
				kraken_results = await response.json()
				if len(kraken_results['error']) > 0:
					return (pair, [timezone.now() - timedelta(minutes=settings.HISTORY_COUNT), timezone.now()], [0, 0])

				results = clean_kraken_pair(kraken_results)[pair]
				try:
					results = results[-(settings.HISTORY_COUNT + 1):] # +1 to get latest one that is not closed yet
				except IndexError:
					pass # Get all results (Capped at 720 by Kraken)

				times = [timezone.datetime.fromtimestamp(result[0]) for result in results]
				close_prices = [float(result[4]) for result in results] # Get close price only

				return (pair, times, close_prices)
			return (pair, timezone.now() - timedelta(minutes=settings.HISTORY_COUNT), [0, 0])

	async def __fetch_gecko_metrics(self, tokens: dict[str, str]):
		query = { 'vs_currency': settings.FIAT, 'ids': ','.join([token for token in tokens]) }
		results = requests.get(settings.COIN_GECKO_API, params=query)

		if results.status_code != 200:
			return {}

		results = results.json()
		metrics = {}
		for result in results:
			metrics[tokens[result['id']]] = {
				'market_cap': result['market_cap'],
				'fully_diluted_valuation': result['fully_diluted_valuation'],
				'total_volume': result['total_volume'],
				'circulating_supply': result['circulating_supply'],
				'total_supply': result['total_supply'],
				'max_supply': result['max_supply'] if result['max_supply'] is not None else -1,
				'all_time_high': result['ath'],
				'all_time_low': result['atl'],
				'all_time_high_time': datetime.fromisoformat(result['ath_date']),
				'all_time_low_time': datetime.fromisoformat(result['atl_date'])
			}

		return metrics

	def __update_user_history(self, prices: dict[str, float]):
		all_user_id = FirebaseUsers().get_all_user_id()
		current_time = timezone.now()
		commit_data = []
		for uid in all_user_id:
			wallet = FirebaseWallet(uid).get_wallet()
			value = 0

			for token in wallet:
				try:
					token_id = token['id']
					total_amount = acc_calc(token.get('amount', 0), '+', token.get('krakenbot_amount', 0))
					total_amount = acc_calc(total_amount, '+', token.get('hold_amount', 0))
					if total_amount > 0:
						value += acc_calc(prices.get(token_id, 0), '*', total_amount)
				except KeyError:
					continue

			commit_data.append({ 'uid': uid, 'time': current_time, 'value': value })

		FirebaseUsers().batch_update_portfolio(commit_data)


class TradeView(APIView):
	def post(self, request: Request):
		try:
			demo_init = request.data.get('demo_init', '')
			livetrade = request.data.get('livetrade', '').upper()
			order = request.data.get('order', '').upper()

			if demo_init == 'demo_init':
				return InitialiseDemoView().post(request)
			elif livetrade != '':
				return LiveTradeView().post(request)
			elif order != '':
				return ManualTradeView().post(request)
			else:
				raise BadRequestException()
		except NotAuthorisedException:
			return Response(status=401)
		except BadRequestException:
			return Response(status=400)
		except NotEnoughTokenException:
			return Response(status=400)


class LiveTradeView(APIView):
	def post(self, request: Request):
		try:
			uid = authenticate_user_jwt(request)
			result = self.livetrade(uid, request)
			return Response(result, status=200)
		except (NotAuthorisedException, NoUserSelectedException):
			return Response(status=401)
		except ValueError:
			return Response(status=400)
		except BadRequestException:
			return Response(status=400)
		except NotEnoughTokenException:
			return Response(status=400)

	def __check_take_profit_stop_loss(self, stop_loss: float, take_profit: float, amount: float):
		try:
			if stop_loss < 0 or stop_loss >= amount:
				raise BadRequestException
			if stop_loss >= take_profit:
				raise BadRequestException
		except TypeError:
			pass

		try:
			if take_profit < 0 or take_profit <= amount:
				raise BadRequestException
		except TypeError:
			pass

	def livetrade(self, uid: str, request: Request):
		trade_type = request.data.get('livetrade', '').upper()
		livetrade_id = request.data.get('livetrade_id', '')
		from_token = request.data.get('from_token', '').upper()
		to_token = request.data.get('to_token', '').upper()
		from_amount = str(request.data.get('from_amount', ''))
		take_profit = str(request.data.get('take_profit', ''))
		stop_loss = str(request.data.get('stop_loss', ''))
		strategy = request.data.get('strategy', '')
		timeframe = request.data.get('timeframe', '')

		take_profit = None if take_profit.strip() == '' else take_profit.strip()
		stop_loss = None if stop_loss.strip() == '' else stop_loss.strip()
		if take_profit is not None:
			take_profit = float(take_profit)
		if stop_loss is not None:
			stop_loss = float(stop_loss)

		match (trade_type):
			case 'RESERVE':
				return self.reserve_livetrade(uid, {
					'strategy': strategy,
					'timeframe': timeframe,
					'from_token': from_token,
					'from_amount': from_amount,
					'to_token': to_token,
					'take_profit': take_profit,
					'stop_loss': stop_loss,
				})

			case 'UPDATE':
				return self.update_livetrade(uid, livetrade_id, take_profit, stop_loss)

			case 'UNRESERVE':
				return self.unreserve_livetrade(uid, livetrade_id)

			case 'SELL':
				return self.sell_livetrade(uid, livetrade_id)

			case _:
				raise BadRequestException()

	def reserve_livetrade(self, uid: str, data: dict):
		strategy = data.get('strategy')
		timeframe = data.get('timeframe')
		from_token = data.get('from_token')
		from_amount = data.get('from_amount')
		to_token = data.get('to_token')
		take_profit = data.get('take_profit')
		stop_loss = data.get('stop_loss')

		if acc_calc(from_amount, '<=', 0):
			raise BadRequestException()

		if timeframe not in ['1h', '4h', '1d']:
			raise BadRequestException()

		if strategy.strip() == '':
			raise BadRequestException()

		self.__check_take_profit_stop_loss(stop_loss, take_profit, float(from_amount))

		try:
			livetrade = FirebaseLiveTrade(uid).create({
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
				'is_active': True,
				'take_profit': take_profit,
				'stop_loss': stop_loss,
			})
			FirebaseWallet(uid).reserve_krakenbot_amount(from_token, from_amount)

			livetrade_id = livetrade['id']
			bot_name = livetrade['name']
			price = MarketView().get_market(convert_from=from_token, convert_to=to_token)[0]
			order = FirebaseOrderBook().create_order(uid, from_token, to_token, price['price_str'], from_amount, bot_name, livetrade_id)

			return { **livetrade, 'order': order }
		except ValueError:
			raise BadRequestException()

	def update_livetrade(self, uid: str, livetrade_id: str, take_profit: float, stop_loss: float):
		firebase_livetrade = FirebaseLiveTrade(uid)
		if not firebase_livetrade.has(livetrade_id):
			raise BadRequestException()
		livetrade = firebase_livetrade.get(livetrade_id)
		amount = livetrade['initial_amount']

		self.__check_take_profit_stop_loss(stop_loss, take_profit, amount)

		if take_profit is not None and stop_loss is not None:
			firebase_livetrade.update_take_profit_stop_loss(livetrade_id, take_profit, stop_loss)
		elif take_profit is not None:
			firebase_livetrade.update_take_profit(livetrade_id, take_profit)
		elif stop_loss is not None:
			firebase_livetrade.update_stop_loss(livetrade_id, stop_loss)

		return firebase_livetrade.get(livetrade_id)

	def unreserve_livetrade(self, uid: str, livetrade_id: str):
		firebase_livetrade = FirebaseLiveTrade(uid)
		if not firebase_livetrade.has(livetrade_id):
			raise BadRequestException()

		livetrade_details = firebase_livetrade.get(livetrade_id)
		cur_token = livetrade_details['cur_token']
		amount = livetrade_details['amount_str']
		status = livetrade_details.get('status')
		order_id = livetrade_details.get('order_id')

		if status == 'ORDER_PLACED':
			FirebaseOrderBook().cancel_order(order_id)

		firebase_livetrade.close(livetrade_id)
		FirebaseWallet(uid).unreserve_krakenbot_amount(cur_token, amount)

		return firebase_livetrade.get(livetrade_id)

	def sell_livetrade(self, uid: str, livetrade_id: str):
		livetrade = self.unreserve_livetrade(uid, livetrade_id)
		fiat = livetrade['fiat']
		cur_token = livetrade['cur_token']
		amount = livetrade['amount_str']

		if cur_token != fiat:
			price = MarketView().get_market(convert_from=cur_token, convert_to=fiat)[0]
			order = FirebaseOrderBook().create_order(uid, cur_token, fiat, price['price_str'], amount)

			return { **livetrade, 'order': order }

		else:
			return livetrade


class ManualTradeView(APIView):
	def post(self, request: Request):
		try:
			uid = authenticate_user_jwt(request)

			from_token = request.data.get('from_token', '').upper()
			to_token = request.data.get('to_token', '').upper()
			amount = str(request.data.get('from_amount', ''))
			order = request.data.get('order', '').upper()
			price = str(request.data.get('order_price', '0'))
			order_id = request.data.get('order_id', '')

			try:
				float(price)
			except ValueError:
				raise BadRequestException()

			match (order):
				case 'ORDER':
					result = self.place_order(uid, from_token, to_token, price, amount)

				case 'CANCEL':
					result = self.cancel_order(uid, order_id)

				case _:
					raise BadRequestException()

			return Response(result, status=200)
		except NotAuthorisedException:
			return Response(status=401)
		except BadRequestException:
			return Response(status=400)
		except NotEnoughTokenException:
			return Response(status=400)

	def place_order(self, uid, from_token, to_token, price, amount, reverse_price = False):
		if acc_calc(price, '<=', 0) or acc_calc(amount, '<=', 0):
			raise BadRequestException()

		if reverse_price:
			price = acc_calc(1, '/', price)
		return FirebaseOrderBook().create_order(uid, from_token, to_token, price, amount)

	def cancel_order(self, uid, order_id):
		firebase_order_book = FirebaseOrderBook()
		if not firebase_order_book.has(order_id) or firebase_order_book.get(order_id).get('uid', None) != uid:
			raise BadRequestException()
		if firebase_order_book.get(order_id).get('created_by', 'USER') != 'USER':
			raise NotAuthorisedException()
		return firebase_order_book.cancel_order(order_id)


class InitialiseDemoView(APIView):
	def post(self, request: Request):
		try:
			uid = authenticate_user_jwt(request)
			FirebaseWallet(uid).demo_init(settings.FIAT, settings.DEMO_AMOUNT)
		except NotAuthorisedException:
			return Response(status=401)


class NewsView(APIView):
	def post(self, request: Request):
		try:
			authenticate_scheduler_oicd(request)
			self.fetch_news()
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)
		except BadRequestException:
			return Response(status=400)
		except ServerErrorException:
			return Response(status=500)

	def fetch_news(self):
		firebase_news = FirebaseNews()

		delete_before_time = timezone.now() - timedelta(days=settings.GNEWS_EXPIRY_DAY)
		firebase_news.delete_all_before(delete_before_time)

		fetch_from_time = timezone.now() - timedelta(days=settings.GNEWS_FETCH_FROM)
		fetch_from_time = fetch_from_time.strftime('%Y-%m-%dT%H:%M:%SZ')

		try:
			(cur_index, query, tag) = firebase_news.fetch_next_query()

			results = requests.get(settings.GNEWS_API, params={
				'apikey': settings.GNEWS_API_KEY,
				'q': query,
				'lang': settings.GNEWS_LANG,
				'from': fetch_from_time,
				'max': settings.GNEWS_MAX_FETCH
			}).json()
			results = self.__parse_gnews(results)

			for result in results:
				firebase_news.upsert(result, tag)

			firebase_news.update_next_query(cur_index + 1)
		except DatabaseIncorrectDataException:
			raise ServerErrorException()

	def __parse_gnews(self, gnews_result: dict):
		articles = gnews_result.get('articles', [])
		results: List[NewsField] = [{
			'time': timezone.datetime.strptime(article['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'),
			'title': article['title'],
			'description': article['description'],
			'content': article['content'],
			'banner_image': article['image'],
			'url': article['url'],
			'source': article['source']['name']
			} for article in articles]
		return results


class AutoLiveTradeView(APIView):
	def post(self, request: Request):
		try:
			authenticate_scheduler_oicd(request)
			timeframe = request.data.get('timeframe', None)
			asyncio.run(self.livetrade(timeframe))
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)

	async def livetrade(self, timeframe: str):
		firebase_token = FirebaseToken()
		all_fiat = firebase_token.filter(is_fiat=True)

		for fiat in all_fiat:
			(buy_signals, sell_signals) = await self.__check_trade(timeframe, fiat['token_id'])
			self.__trade(buy_signals, MarketView().get_market(convert_from=fiat['token_id']), 'Buy')
			self.__trade(sell_signals, MarketView().get_market(convert_to=fiat['token_id']), 'Sell')

	async def __check_trade(self, timeframe: str, fiat: str):
		firebase_livetrade = FirebaseLiveTrade()
		livetrades = firebase_livetrade.filter(timeframe=timeframe, is_active=True, fiat=fiat, status='READY_TO_TRADE')
		if len(livetrades) == 0:
			return ([], [])
		all_livetrade_token = { livetrade['token_id'] for livetrade in livetrades }

		all_tokens = FirebaseToken().filter(is_fiat=False)
		all_tokens = { token['id'] + fiat: token['id'] for token in all_tokens if token['id'] in all_livetrade_token }

		results = await apply_backtest(all_tokens.keys(), [settings.INTERVAL_MAP[timeframe]])
		results = { all_tokens[pair]: value for (pair, value) in results.items() } # To replace pair with just token id, e.g. BTCGBP -> BTC

		trade_decisions = { 'buy': [], 'sell': [] }

		for livetrade in livetrades:
			try:
				strategies = livetrade['strategy'].split(' (')[0] # Remove extra information
				[strategy_1, strategy_2] = strategies.split(' & ')
				decision_1 = get_livetrade_result(results[livetrade['token_id']][str(settings.INTERVAL_MAP[timeframe])], strategy_1)
				decision_2 = get_livetrade_result(results[livetrade['token_id']][str(settings.INTERVAL_MAP[timeframe])], strategy_2)

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

		return (trade_decisions['buy'], trade_decisions['sell'])

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


class UpdateCandlesView(APIView):
	def post(self, request: Request):
		try:
			authenticate_scheduler_oicd(request)
			update_candles()
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)


class CheckOrdersView(APIView):
	def post(self, request: Request):
		try:
			authenticate_scheduler_oicd(request)
			self.check()
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)

	def check(self):
		order_prices = self.__get_orders()
		success_pairs = asyncio.run(self.__check_orders_success(order_prices))
		self.__trade(success_pairs)

	def __get_orders(self):
		order_book = FirebaseOrderBook()
		orders = order_book.filter(status='OPEN')
		token_pair_price = {}
		for order in orders:
			order_id = order['id']
			price = order['price']
			from_token = order['from_token']
			to_token = order['to_token']
			pair = f'{from_token}{to_token}'
			reverse_pair = f'{to_token}{from_token}'
			if pair not in token_pair_price:
				token_pair_price[pair] = { 'data': [], 'reverse': reverse_pair }
			token_pair_price[pair]['data'].append((price, order_id))

		return token_pair_price

	async def __check_orders_success(self, order_prices):
		last_minute = timezone.now() - timedelta(minutes=2)
		since = int(last_minute.timestamp())
		prices = {}
		async with aiohttp.ClientSession() as session:
			tasks = [self.__fetch_kraken_ohlc(session, pair, since) for pair in order_prices]
			reverse_tasks = [self.__fetch_kraken_ohlc(session, order_prices[pair]['reverse'], since, pair) for pair in order_prices]
			results = await asyncio.gather(*tasks)
			reverse_results = await asyncio.gather(*reverse_tasks)
			results = { pair: (high, low) for (pair, high, low) in results if high is not None and low is not None }
			reverse_results = { pair: (acc_calc(1, '/', high), acc_calc(1, '/', low)) for (pair, high, low) in reverse_results if high is not None and low is not None }
			prices = { **results, **reverse_results }

		success_pair = []
		for pair in order_prices:
			values = prices.get(pair)
			if values is None or values[0] is None or values[1] is None:
				log_error(f'Check Orders Failed due to token price not found! ({pair})')
				continue

			(high, low) = values

			for (order_price, order_id) in order_prices[pair]['data']:
				if acc_calc(order_price, '-', low) >= 0 and acc_calc(order_price, '-', high) <= 0:
					success_pair.append(order_id)

		return success_pair

	async def __fetch_kraken_ohlc(self, session: aiohttp.ClientSession, pair: str, since: int, reverse_pair_name: str = None):
		async with session.get(settings.KRAKEN_OHLC_API, params={'pair': pair, 'interval': 1, 'since': since}) as response:
			if response.status == 200:
				kraken_results = await response.json()
				if len(kraken_results['error']) > 0:
					return (pair, None, None) if reverse_pair_name is None else (reverse_pair_name, None, None)

				results = clean_kraken_pair(kraken_results)[pair]
				high = results[0][2]
				low = results[0][3]

				for result in results:
					high = max(high, result[2])
					low = min(low, result[3])

				return (pair, high, low) if reverse_pair_name is None else (reverse_pair_name, high, low)
			return (pair, None, None) if reverse_pair_name is None else (reverse_pair_name, None, None)

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


class CheckLossProfitView(APIView):
	def post(self, request: Request):
		try:
			authenticate_scheduler_oicd(request)
			self.firebase_livetrade = FirebaseLiveTrade()
			self.firebase_order_book = FirebaseOrderBook()
			self.check()
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)

	def check(self):
		prices, take_profit_livetrades, stop_loss_livetrades = self.__get_livetrades_and_prices()

		self.__check_take_profit(prices, take_profit_livetrades)
		self.__check_stop_loss(prices, stop_loss_livetrades)

	def __get_livetrades_and_prices(self):
		take_profit_livetrades = self.firebase_livetrade.filter(is_active=True, has_take_profit=True, taken_profit=False)
		stop_loss_livetrades = self.firebase_livetrade.filter(is_active=True, has_stop_loss=True, stopped_loss=False)

		fiats = FirebaseToken().filter(is_fiat=True, is_active=None)
		fiats = [fiat['token_id'] for fiat in fiats]
		prices = {}
		for fiat in fiats:
			market_prices = MarketView().get_market(convert_to=fiat)
			market_prices = { f'{market_price['token']}{fiat}': market_price['price_str'] for market_price in market_prices }
			prices = { **prices, **market_prices }

		return prices, take_profit_livetrades, stop_loss_livetrades

	def __get_trade_value(self, prices: dict[str, str], livetrade: dict):
		token_id = livetrade['token_id']
		fiat = livetrade['fiat']
		cur_token = livetrade['cur_token']
		price = prices.get(f'{token_id}{fiat}')
		if price is None:
			log_error(f'Check Stop Loss Profit Failed due to token price not found! ({token_id}{fiat})')
			return False

		value = livetrade['amount_str']
		if cur_token == token_id:
			value = acc_calc(value, '*', price, 2)

		return (value, price)

	def __apply_stop(self, livetrade: dict, price: str, stop_type = Literal['stop_loss', 'take_profit']):
		livetrade_id = livetrade['livetrade_id']
		bot_name = livetrade['name']
		uid = livetrade['uid']
		token_id = livetrade['token_id']
		fiat = livetrade['fiat']
		cur_token = livetrade['cur_token']
		order_created = False

		if livetrade.get('order_id') is not None:
			self.firebase_order_book.cancel_order(livetrade['order_id'])

		if cur_token == token_id:
			amount = livetrade['amount_str']
			self.firebase_order_book.create_order(uid, cur_token, fiat, price, amount, bot_name, livetrade_id)
			order_created = True

		if stop_type == 'stop_loss':
			self.firebase_livetrade.stop_loss_pause(livetrade_id)
		elif stop_type == 'take_profit':
			self.firebase_livetrade.taking_profit(livetrade_id)

		if cur_token == fiat:
			LiveTradeView().unreserve_livetrade(uid, livetrade_id)

		return order_created

	def __check_take_profit(self, prices, take_profit_livetrades):
		order_created = 0
		take_profit_set = 0

		for livetrade in take_profit_livetrades:
			try:
				(value, price) = self.__get_trade_value(prices, livetrade)

				if value is False:
					continue

				if acc_calc(value, '-', livetrade['take_profit']) < 0:
					continue

				created = self.__apply_stop(livetrade, price, 'take_profit')
				take_profit_set += 1 if created else 0

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
				(value, price) = self.__get_trade_value(prices, livetrade)

				if value is False:
					continue

				if acc_calc(value, '-', livetrade['stop_loss']) > 0:
					continue

				created = self.__apply_stop(livetrade, price, 'stop_loss')
				stop_loss_set += 1 if created else 0

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


class RecalibrateBotView(APIView):
	def post(self):
		if not settings.DEBUG:
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
				amount = livetrade.get('amount_str', 0)
				wallet[cur_token] = acc_calc(wallet.get(cur_token, 0), '+', amount)

			firebase_wallet = FirebaseWallet(uid)
			all_tokens = [token['id'] for token in firebase_wallet.get_wallet()]
			for token in all_tokens:
				amount = wallet.get(token, 0)
				firebase_wallet.set_bot_amount(token, amount)
		return Response(status=200)
