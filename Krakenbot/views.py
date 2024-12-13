from datetime import datetime, timedelta
from itertools import combinations
from random import normalvariate
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
from Krakenbot.backtest import AnalyseBacktest, ApplyBacktest, indicator_names
from Krakenbot.update_candles import main as update_candles
from Krakenbot.utils import acc_calc, authenticate_scheduler_oicd, authenticate_user_jwt, check_take_profit_stop_loss, clean_kraken_pair, log, log_error, log_warning, usd_to_gbp


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

	def __check_request(self, request: Request):
		strategy = request.query_params.get('strategy', '')
		timeframe = request.query_params.get('timeframe', '')
		funds = request.query_params.get('funds', '').strip()
		stop_loss = request.query_params.get('stop_loss', '').strip()
		take_profit = request.query_params.get('take_profit', '').strip()

		if strategy != '' and strategy not in self.ALL_STRATEGIES:
			raise BadRequestException()

		if timeframe != '' and timeframe not in settings.TIMEFRAMES.keys():
			raise BadRequestException()

		try:
			stop_loss = None if stop_loss == '' else float(stop_loss)
			take_profit = None if take_profit == '' else float(take_profit)
			if strategy != '' and float(funds) <= 0:
					raise BadRequestException()
		except ValueError:
			raise BadRequestException()

		if check_take_profit_stop_loss(funds, stop_loss, take_profit) is False:
			raise BadRequestException()


	def get(self, request: Request):
		try:
			get_strategies = request.query_params.get('get_strategies', '').strip().upper()
			if get_strategies == 'GET STRATEGIES':
				return Response(self.ALL_STRATEGIES)

			fiat = request.query_params.get('convert_from', settings.FIAT).strip().upper()
			token_id = request.query_params.get('convert_to', '').strip().upper()
			strategy = request.query_params.get('strategy', '')
			timeframe = request.query_params.get('timeframe', '')
			funds = request.query_params.get('funds', '').strip()
			stop_loss = request.query_params.get('stop_loss', '').strip()
			take_profit = request.query_params.get('take_profit', '').strip()

			self.__check_request(request)
			stop_loss = None if stop_loss == '' else stop_loss
			take_profit = None if take_profit == '' else take_profit

			firebase_token = FirebaseToken()
			fiat_token = firebase_token.filter(fiat, is_fiat=True)
			if len(fiat_token) < 1:
				raise BadRequestException()

			token = firebase_token.filter(token_id)
			if len(token) < 1:
				raise BadRequestException()

			token = token[0]
			history_prices = token.get('history_prices', {}).get('data', [1])
			pair = FirebaseCandle().fetch_pair(token_id)
			fluctuations = FirebaseCandle(pair, '1h').get_fluctuations()

			starting_data = history_prices[-1]
			simulation_data = self.generate_simulated_prices(starting_data, fluctuations, 120)

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
				simulated_ohlc = self.generate_simulated_ohlc(simulation_data, fluctuations)
				decisions = self.simulate_backtest(simulated_ohlc, strategy, timeframe)
				values, actions, stopped_by, stopped_at = self.simulate_result(simulation_data, decisions, funds, stop_loss, take_profit)

				response['funds_values'] = values
				response['bot_actions'] = actions
				response['stopped_by'] = stopped_by
				response['stopped_at'] = stopped_at

			return Response(response, status=200)

		except BadRequestException:
			return Response(status=400)

	def generate_simulated_prices(self, starting_data: float, fluctuations: dict[str, float], length: int = 120):
		simulated_data = [starting_data]
		for _ in range(length - 1):
			new_data = simulated_data[-1] * normalvariate(fluctuations.get('close_mean', 1), fluctuations.get('close_std_dev', 0.001))
			simulated_data.append(new_data)
		return simulated_data

	def generate_simulated_ohlc(self, data: list[float], fluctuations: dict[str, float]):
		simulated_ohlc = []
		for i in range(len(data)):
			if i == 0:
				_open = data[i] / normalvariate(fluctuations.get('close_mean', 1), fluctuations.get('close_std_dev', 0.001))
			else:
				_open = data[i - 1]

			high = _open * normalvariate(fluctuations.get('high_mean', 1.005), fluctuations.get('high_std_dev', 0.001))
			high = max(_open, data[i], high)

			low = _open * normalvariate(fluctuations.get('low_mean', 0.995), fluctuations.get('low_std_dev', 0.001))
			low = min(_open, data[i], low)

			simulated_ohlc.append({ 'Open': _open, 'High': high, 'Low': low, 'Close': data[i] })
		return simulated_ohlc

	def combine_ohlc(self, simulated_ohlc: list[dict[str, float]], interval: int):
		if interval == 1:
			return simulated_ohlc

		i = 0
		ohlc = []

		while i < len(simulated_ohlc):
			highs = [data['High'] for data in simulated_ohlc[i:i + interval]]
			lows = [data['Low'] for data in simulated_ohlc[i:i + interval]]
			ohlc.append({
				'Open': simulated_ohlc[i]['Open'],
				'Close': simulated_ohlc[i + interval - 1]['Close'],
				'High': max(highs),
				'Low': min(lows),
			})
			i += interval

		return ohlc


	def simulate_backtest(self, simulated_ohlc: list[dict[str, float]], strategy: str, timeframe: str):
		interval = settings.INTERVAL_MAP[timeframe] // 60
		simulated_ohlc = self.combine_ohlc(simulated_ohlc, interval)
		simulated_ohlc = pd.DataFrame(simulated_ohlc)

		strategy_1, strategy_2 = strategy.split(' & ')
		backtest_func = { strategy: func for (func, strategy) in indicator_names.items() if strategy in [strategy_1, strategy_2] }
		result_1 = backtest_func[strategy_1](simulated_ohlc)
		result_2 = backtest_func[strategy_2](simulated_ohlc)
		signals = (result_1 == result_2) * result_1

		decisions = []

		empty_decision = [0] * (interval - 1)
		for signal in signals:
			decisions.extend([signal, *empty_decision])

		return decisions

	def check_stop_loss(self, cur_price, cur_funds, bought, stop_loss):
		if stop_loss is None:
			return False
		if bought:
			cur_funds = acc_calc(cur_funds, '*', cur_price)
		if acc_calc(cur_funds, '<=', stop_loss):
			return True
		return False

	def check_take_profit(self, cur_price, cur_funds, bought, take_profit):
		if take_profit is None:
			return False
		if bought:
			cur_funds = acc_calc(cur_funds, '*', cur_price)
		if acc_calc(cur_funds, '>=', take_profit):
			return True
		return False

	def carry_trade(self, data, decision, take_profit, stop_loss, bought, prev_value):
		stop_by = None

		if self.check_stop_loss(data, prev_value, bought, stop_loss):
			if bought:
				value = acc_calc(prev_value, '*', data, 2)
				action = -1
			else:
				value = prev_value
				action = 0
			stop_by = 'stop loss limit'

		elif self.check_take_profit(data, prev_value, bought, take_profit):
			if bought:
				value = acc_calc(prev_value, '*', data, 2)
				action = -1
			else:
				value = prev_value
				action = 0
			stop_by = 'take profit limit'

		elif decision == 1 and not bought:
			value = acc_calc(prev_value, '/', data)
			action = 1
			bought = True

		elif decision == -1 and bought:
			value = acc_calc(prev_value, '*', data, 2)
			action = -1
			bought = False

		else:
			value = prev_value
			action = 0

		return (bought, value, action, stop_by)

	def simulate_result(self, simulation_data: list[float], decisions: list[float], funds: str, stop_loss: str, take_profit: str):
		values = [acc_calc(funds, '/', simulation_data[0])]
		bought = True
		actions = [1]
		stop_by = None
		stopped_at = None

		for (data, decision) in zip(simulation_data[1:], decisions[1:]):
			(bought, value, action, stop_by) = self.carry_trade(data, decision, take_profit, stop_loss, bought, values[-1])

			values.append(value)
			actions.append(action)

			if stop_by is not None:
				stopped_at = len(action)
				break

		actions.extend([0] * (len(decisions) - len(actions)))
		values.extend([values[-1]] * (len(decisions) - len(values)))

		if bought:
			actions[-1] = -1
			values[-1] = acc_calc(values[-1], '*', simulation_data[-1], 2)

		stopped_at = stopped_at if stopped_at is not None else len(decisions) - 1

		return values, actions, stop_by, stopped_at


class BackTestView(APIView):
	def post(self, request: Request):
		try:
			authenticate_scheduler_oicd(request)
			results = self.backtest()
			self.save_database(results)
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)

	def backtest(self):
		firebase_analysis = FirebaseAnalysis()
		results = AnalyseBacktest().run().reset_index().to_numpy()

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
		return results

	def save_database(self, results):
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

		try:
			coin_gecko_ids = { token.get('coingecko_id'): token.get('token_id') for token in firebase_tokens }
			metrics = await self.__fetch_gecko_metrics(coin_gecko_ids)
			for metric in metrics:
				firebase.update(metric, metrics[metric])
		except Exception:
			# Continue even if gecko fails
			pass

		firebase.update_history_prices(settings.FIAT, [timezone.now() - timedelta(days=7), timezone.now()], [1, 1])

		async with aiohttp.ClientSession() as session:
			tasks = [self.__fetch_kraken_ohlc(session, pair) for pair in pairs]
			results = await asyncio.gather(*tasks)
			results = [(pair.replace(settings.FIAT, ''), times, close_prices) for (pair, times, close_prices) in results if close_prices != [0, 0]]
			all_tokens = [token for (token, _, close_prices) in results if close_prices != [0, 0]]
			all_prices = { settings.FIAT: 1 }

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

		try:
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
		except Exception:
			return {}

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

		if check_take_profit_stop_loss(float(from_amount), stop_loss, take_profit) is False:
			raise BadRequestException()

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

		if check_take_profit_stop_loss(amount, stop_loss, take_profit) is False:
			raise BadRequestException()

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
				if price != '':
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
			return Response(status=200)
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
			self.livetrade(timeframe)
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)

	def livetrade(self, timeframe: str):
		firebase_token = FirebaseToken()
		all_fiat = firebase_token.filter(is_fiat=True)

		for fiat in all_fiat:
			(buy_signals, sell_signals) = self.__check_trade(timeframe, fiat['token_id'])
			self.__trade(buy_signals, MarketView().get_market(convert_from=fiat['token_id']), 'Buy', timeframe)
			self.__trade(sell_signals, MarketView().get_market(convert_to=fiat['token_id']), 'Sell', timeframe)

	def __check_trade(self, timeframe: str, fiat: str):
		firebase_livetrade = FirebaseLiveTrade()
		livetrades = [
			*firebase_livetrade.filter(timeframe=timeframe, is_active=True, fiat=fiat, status='READY_TO_TRADE'),
			*firebase_livetrade.filter(timeframe=timeframe, is_active=True, fiat=fiat, status='ORDER_PLACED'),
		]
		if len(livetrades) == 0:
			return ([], [])
		all_livetrade_token = { livetrade['token_id'] for livetrade in livetrades }

		all_tokens = FirebaseToken().filter(is_fiat=False)
		all_tokens = { token['id'] + fiat: token['id'] for token in all_tokens if token['id'] in all_livetrade_token }

		results =  ApplyBacktest().run(list(all_tokens.keys()), settings.INTERVAL_MAP[timeframe])
		results = { all_tokens[pair]: value for (pair, value) in results.items() } # To replace pair with just token id, e.g. BTCGBP -> BTC

		trade_decisions = { 'buy': [], 'sell': [] }

		for livetrade in livetrades:
			try:
				strategies = livetrade['strategy'].split(' (')[0] # Remove extra information
				[strategy_1, strategy_2] = strategies.split(' & ')
				decision_1 = ApplyBacktest.get_livetrade_result(results[livetrade['token_id']], strategy_1)
				decision_2 = ApplyBacktest.get_livetrade_result(results[livetrade['token_id']], strategy_2)

				if decision_1 == decision_2 == -1 and livetrade['cur_token'] == livetrade['token_id']:
					trade_decisions['sell'].append(livetrade)
				elif decision_1 == decision_2 == 1 and livetrade['cur_token'] != livetrade['token_id']:
					trade_decisions['buy'].append(livetrade)
			except (KeyError, ValueError, IndexError):
				log_warning(
					f"Livetrade Fails due to Unknown Strategy " \
					f"Bot: {livetrade.get('livetrade_id', 'ID Not Found')} {timeframe} " \
					f"Strategy: {livetrade.get('strategy', 'Strategy Not Found')}"
				)

		return (trade_decisions['buy'], trade_decisions['sell'])

	def __cancel_order(self, order_id: str, timeframe: str, price: str):
		firebase_order_book = FirebaseOrderBook()

		try:
			order = firebase_order_book.get(order_id)
			if (timezone.now() - order['created_time']).seconds < min(5 * settings.INTERVAL_MAP[timeframe] * 60, 24 * 60 * 60):
				# If last order created within 5 unit (5min / 5h / 20h) or 1 day, dont change it
				return False
			if acc_calc(order['price_str'], '==', price):
				# If same price, skip
				return False
			firebase_order_book.cancel_order(order_id)
		except BadRequestException:
			# If BadRequest, the order is already cancelled
			pass

		return True

	def __trade(self, trade_decisions: list[dict], market_prices: list[dict[str, str | float]], trade_type: str, timeframe: str):
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
				status = decision['status']
				order_id = decision.get('order_id')
				price = prices[decision['token_id']]

				if status == 'ORDER_PLACED':
					order_cancelled = self.__cancel_order(order_id, timeframe, price)
					if order_cancelled is False:
						continue

				firebase_order_book.create_order(uid, from_token, to_token, price, from_amount, bot_name, bot_id)
				trade_count += 1
			except KeyError:
				log_warning(
					f"Livetrade Trading Fails due to Invalid Fields " \
					f"[Bot {decision.get('livetrade_id')}] " \
					f"[UID {decision.get('uid')}] " \
					f"From: {decision.get('amount', 'No Amount')} {decision.get('cur_token', 'No Token Found')}, " \
					f"Price: {prices.get(decision.get('token_id', ''), 'Price Not Found!')}"
				)

			except NotEnoughTokenException:
				log_warning(
					f"Livetrade Trading Fails due to Not Enough Token " \
					f"[Bot {decision.get('livetrade_id')}] " \
					f"[UID {decision.get('uid')}] " \
					f"From: {decision.get('amount')} {decision.get('cur_token')}, " \
					f"Price: {prices[decision['token_id']]}"
				)

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
				log_warning(
					f"Order Fails due to Invalid Fields " \
					f"[Order {order_details.get('id')}] " \
					f"[UID {order_details.get('uid')}] " \
					f"From: {order_details.get('volume')} {order_details.get('from_token')}, " \
					f"To: {str(to_amount)} {order_details.get('to_token')}"
				)
			except NotEnoughTokenException:
				order_details = order_book.get(success_pair)
				to_amount = acc_calc(order_details.get('volume', '0'), '*', order_details.get('price_str', '0'))
				log_warning(
					f"Order Fails due to Not Enough Token " \
					f"[Order {order_details.get('id')}] " \
					f"[UID {order_details.get('uid')}] " \
					f"From: {order_details.get('volume')} {order_details.get('from_token')}, " \
					f"To: {str(to_amount)} {order_details.get('to_token')}"
				)

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
				log_warning(
					f"Take Profit Fails due to Invalid Fields " \
					f"[Bot {livetrade.get('livetrade_id')}] " \
					f"[UID {livetrade.get('uid')}] " \
					f"Take Profit: {livetrade.get('take_profit')}"
				)

			except NotEnoughTokenException:
				log_warning(
					f"Take Profit Fails due to Not Enough Token " \
					f"[Bot {livetrade.get('livetrade_id')}] " \
					f"[UID {livetrade.get('uid')}] " \
					f"Take Profit: {livetrade.get('take_profit')}"
				)

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
				log_warning(
					f"Stop Loss Fails due to Invalid Fields " \
					f"[Bot {livetrade.get('livetrade_id')}] " \
					f"[UID {livetrade.get('uid')}] " \
					f"Stop Loss: {livetrade.get('stop_loss')}"
				)

			except NotEnoughTokenException:
				log_warning(
					f"Stop Loss Fails due to Not Enough Token " \
					f"[Bot {livetrade.get('livetrade_id')}] " \
					f"[UID {livetrade.get('uid')}] " \
					f"Stop Loss: {livetrade.get('stop_loss')}"
				)

		log(f'Stop Loss Set: {stop_loss_set}; Order Created: {order_created}')


class CalculateFluctuationsView(APIView):
	def post(self, request):
		try:
			authenticate_scheduler_oicd(request)
			candles = self.get_candles()
			fluctuations = self.calculate_fluctuations(candles)
			self.save_fluctuations(fluctuations)
			return Response(status=200)
		except NotAuthorisedException:
			return Response(status=401)

	def get_candles(self):
		firebase = FirebaseCandle()
		all_pairs = firebase.fetch_pairs()
		results = {}

		for pair in all_pairs:
			firebase.change_pair(pair, '1h')
			candles = firebase.fetch_all()
			if candles is not None:
				results[pair] = candles

		return results

	def calculate_fluctuations(self, candles: dict[str, pd.DataFrame]):
		results = {}
		for pair in candles:
			high = candles[pair]['High'].to_numpy()
			low = candles[pair]['Low'].to_numpy()
			close = candles[pair]['Close'].to_numpy()
			_open = candles[pair]['Open'].to_numpy()

			high_diff = high / _open
			high_mean = high_diff.mean()
			high_std_dev = high_diff.std()

			low_diff = low / _open
			low_mean = low_diff.mean()
			low_std_dev = low_diff.std()

			close_diff = close / _open
			close_mean = close_diff.mean()
			close_std_dev = close_diff.std()

			results[pair] = {
				'high_mean': high_mean,
				'high_std_dev': high_std_dev,
				'low_mean': low_mean,
				'low_std_dev': low_std_dev,
				'close_mean': close_mean,
				'close_std_dev': close_std_dev,
			}
		return results

	def save_fluctuations(self, fluctuations: dict[str, float]):
		for pair in fluctuations:
			firebase = FirebaseCandle(pair, '1h')
			firebase.save_fluctuations(**fluctuations[pair])


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


## Scheduled Processes to be called in different interval
## Grouped to make them call in sequence, avoid race condition

## Check Stop Loss > AutoLiveTrade > Check Orders
## > Update Price > News
## > Update Candles > Backtest

## Update Price and News called before backtest to reduce wait time

class ScheduledView(APIView):
	def post(self, request):
		try:
			authenticate_scheduler_oicd(request)
		except NotAuthorisedException:
			return Response(status=401)

		now       = timezone.now()
		hourly    = now.minute == 0
		quarterly = now.hour % 4 == 0 and hourly
		daily     = now.hour == 0 and hourly

		error = []
		completed_task = []

		(completed_task, error) = self.schedule_run(lambda: CheckLossProfitView().post(request),
																								'Check Loss Profit',
																								completed_task,
																								error)

		(completed_task, error) = self.schedule_run(lambda: AutoLiveTradeView().livetrade('1min'),
																								'Auto Livetrade (1min)',
																								completed_task,
																								error)

		if hourly:
			(completed_task, error) = self.schedule_run(lambda: AutoLiveTradeView().livetrade('1h'),
																									'Auto Livetrade (1h)',
																									completed_task,
																									error)

		if quarterly:
			(completed_task, error) = self.schedule_run(lambda: AutoLiveTradeView().livetrade('4h'),
																									'Auto Livetrade (4h)',
																									completed_task,
																									error)

		if daily:
			(completed_task, error) = self.schedule_run(lambda: AutoLiveTradeView().livetrade('1d'),
																									'Auto Livetrade (1d)',
																									completed_task,
																									error)

		(completed_task, error) = self.schedule_run(lambda: CheckOrdersView().post(request),
																								'Check Orders',
																								completed_task,
																								error)

		if hourly:
			(completed_task, error) = self.schedule_run(lambda: UpdateHistoryPricesView().post(request),
																									'Update History Prices',
																									completed_task,
																									error,
																									True)

			(completed_task, error) = self.schedule_run(lambda: NewsView().post(request),
																									'Fetch News',
																									completed_task,
																									error)

		if daily:
			(completed_task, error) = self.schedule_run(lambda: UpdateCandlesView().post(request),
																									'Update Candles',
																									completed_task,
																									error)

			(completed_task, error) = self.schedule_run(lambda: BackTestView().post(request),
																									'Backtest',
																									completed_task,
																									error)

		log(f'Completed Task: [{", ".join(completed_task)}]')

		if len(error) > 0:
			log_error(error)
			return Response(status=500)

		return Response(status=200)


	def schedule_run(self, function, title, completed_task, error, retry = False):
		try:
			function()
			completed_task.append(title)
		except Exception as e:
			error.append(str(e))
			if retry:
				(completed_task, error) = self.schedule_run(function, title, completed_task, error)

		return (completed_task, error)
