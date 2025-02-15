from datetime import datetime
from itertools import combinations
import aiohttp
import asyncio
import logging
import numpy as np
import pandas as pd
import time

from numba import njit

from Krakenbot.utils import clean_kraken_pair

try:
	from Krakenbot.MVP_Backtest import dev_print, setup_performance_logging, indicator_names, evaluate_strategy, determine_use_case
	from Krakenbot.update_candles import main as update_candles
	from Krakenbot.get_candles import main as get_candles
except ModuleNotFoundError:
	from MVP_Backtest import dev_print, setup_performance_logging, indicator_names, evaluate_strategy, determine_use_case
	from update_candles import main as update_candles
	from get_candles import main as get_candles


class AnalyseBacktest:
	def __init__(self, no_print=True, update_candle=False):
		self.no_print = no_print
		self.update_candle = update_candle

	@staticmethod
	@njit(cache=True, fastmath=True)
	def analysis(close_data: list[np.float64], trading_signals_1: list[np.int8], trading_signals_2: list[np.int8]):
		# Calculate coin holdings and fiat amount
		coin_holdings = 0
		fiat_amount = 10000
		bought = False

		signals = (trading_signals_1 == trading_signals_2) * trading_signals_1
		for i in range(signals.shape[0]):
			if not bought and signals[i] == 1:
				coin_holdings = fiat_amount / close_data[i]
				fiat_amount = 0
				bought = True
			elif bought and signals[i] == -1:
				fiat_amount = coin_holdings * close_data[i]
				coin_holdings = 0
				bought = False

		# Final value if still holding coins
		fiat_amount += coin_holdings * close_data[-1]

		return fiat_amount

	def analyse_backtest(self, df: pd.DataFrame, token_id: str, data_timeframe: str, performance_logger: logging.Logger | None = None):
		# Calculate trading signals for all indicators once
		trading_signals = { name: func(df) for func, name in indicator_names.items() }
		best_strategy = { 'Strategy': '', 'Profit': 0, 'Percentage': 0 }
		initial_investment = 10000
		close_prices = df['Close'].to_numpy()

		# Generate combinations of indicators, avoiding comparisons of the same type
		for name1, name2 in combinations(indicator_names.values(), 2):
			fiat_amount = self.analysis(
				close_prices.astype(np.float64),
				trading_signals[name1].astype(np.int8),
				trading_signals[name2].astype(np.int8)
			)

			strategy_name = f'{name1} & {name2}'
			use_case, timeframe = determine_use_case(name1, name2)

			# Evaluate the strategy performance
			if performance_logger is not None:
				strategy_returns = df['Close'].pct_change().dropna()
				performance_metrics = evaluate_strategy(strategy_returns, strategy_name)

				coin_name = f'{token_id}-{data_timeframe}'
				for key, value in performance_metrics.items():
					performance_logger.info(f"{coin_name},{strategy_name},{key},{value}")

			if fiat_amount > best_strategy['Profit']:
				best_strategy = {
					'Strategy': f'{strategy_name} ({use_case}, {timeframe})',
					'Profit': fiat_amount,
					'Percentage': (fiat_amount - initial_investment) / initial_investment * 100
				}

		return {
			'Recommended Strategy': best_strategy['Strategy'],
			'Profit of Recommended Strategy': best_strategy['Profit'],
			'Percentage Increase': best_strategy['Percentage']
		}

	def run(self):
		start_time = time.time()
		if self.update_candle:
			update_candles()
		candles = get_candles()

		if len(candles) < 1:
			return pd.DataFrame([])

		# Set up logging for performance metrics
		performance_logger = None
		if not self.no_print:
			performance_logger = setup_performance_logging()

		best_strategies = []
		df_ids = []

		# Process each file
		for candle in candles:
			token_id = candle['token_id']
			fiat = candle['fiat']
			timeframe = candle['timeframe']
			best_strategies.append(self.analyse_backtest(candle['candles'], token_id, timeframe, performance_logger))
			backtest_id = f'{fiat}:{token_id} | {timeframe}'
			dev_print(f"Time to process {backtest_id}: {time.time() - start_time} seconds", self.no_print)
			df_ids.append(backtest_id)

		dev_print(f"Total runtime: {time.time() - start_time} seconds", self.no_print)
		coin_profit_df = pd.DataFrame(best_strategies, index=df_ids)
		return coin_profit_df


class ApplyBacktest:
	async def fetch_ohlc_data(self, session: aiohttp.ClientSession, pair: str, interval: int, since: int = None):
		url = 'https://api.kraken.com/0/public/OHLC'
		params = {
			'pair': pair,
			'interval': interval
		}
		if since:
			params['since'] = since

		async with session.get(url, params=params) as response:
			if response.status != 200:
				return (pair, None)

			data = await response.json()
			if data['error']:
				return (pair, None)

			result = clean_kraken_pair(data)[pair]
			ohlc_data = []

			for entry in result:
				timestamp = int(entry[0])
				timestamp_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
				ohlc_data.append({
						'Unix_Timestamp': timestamp,
						'Timestamp': timestamp_str,
						'Open': float(entry[1]),
						'High': float(entry[2]),
						'Low': float(entry[3]),
						'Close': float(entry[4]),
						'Volume': float(entry[5]),
				})

			return (pair, ohlc_data)

	async def apply_ta(self, session, pair, interval, since_timestamp):
		(pair, ohlc_data) = await self.fetch_ohlc_data(session, pair, interval, since_timestamp)

		if ohlc_data:
			df = pd.DataFrame(ohlc_data)
			indicators = { name: func(df)[-1] for func, name in indicator_names.items() }
			return { pair: indicators }
		return None

	async def apply_backtest(self, pairs: list[str], interval: int, since: datetime = None) -> dict[str, dict[str, pd.DataFrame]]:
		since_timestamp = since.timestamp() if since is not None else None

		async with aiohttp.ClientSession() as session:
			tasks = [self.apply_ta(session, pair, interval, since_timestamp) for pair in pairs]
			raw_data = await asyncio.gather(*tasks)

		results = { key: data[key] for data in raw_data for key in data if data is not None }
		return results

	@staticmethod
	def get_livetrade_result(result: dict[str, int], strategy: str) -> int:
		old_strategy_map = {
			'RSI70': 'RSI70_30',
			'RSI71': 'RSI71_31',
			'RSI72': 'RSI72_32',
			'RSI73': 'RSI73_33',
			'RSI74': 'RSI74_34',
			'RSI75': 'RSI75_35'
		}
		if strategy in old_strategy_map:
			strategy = old_strategy_map[strategy]
		return result[strategy]

	def run(self, pairs: list[str], interval: int, since: datetime = None) -> dict[str, dict[str, pd.DataFrame]]:
		return asyncio.run(self.apply_backtest(pairs, interval, since))

if __name__ == '__main__':
	prompt = input('Do you want to analyse backtest for the best strategy? (y/N)')
	if prompt == 'y':
		result = AnalyseBacktest(no_print=False, update_candle=True).run()
		result.to_csv('coin_profit_recommended.csv')
		print(result)

	prompt = input('Do you want to run apply TA to get decision? (y/N)')
	if prompt == 'y':
		pairs = ['BTCGBP', 'ETHGBP', 'DOGEUSD']
		result = ApplyBacktest().run(pairs, 60)
		print(result)
