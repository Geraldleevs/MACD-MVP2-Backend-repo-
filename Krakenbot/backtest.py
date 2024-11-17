from itertools import combinations
import logging
import numpy as np
import pandas as pd
import time

from numba import njit

try:
	from Krakenbot.MVP_Backtest import dev_print, setup_performance_logging, indicator_names, evaluate_strategy, determine_use_case
	from Krakenbot.update_candles import main as update_candles
	from Krakenbot.get_candles import main as get_candles
except ModuleNotFoundError:
	from MVP_Backtest import dev_print, setup_performance_logging, indicator_names, evaluate_strategy, determine_use_case
	from update_candles import main as update_candles
	from get_candles import main as get_candles


@njit(cache=True, fastmath=True)
def analysis(close_data: list[np.float64], trading_signals_1: list[np.int8], trading_signals_2: list[np.int8]):
	# Calculate coin holdings and fiat amount
	coin_holdings = 0
	fiat_amount = 10000
	bought = False

	signals = (trading_signals_1 == trading_signals_2) * trading_signals_1
	for i in range(len(signals)):
		if signals[i] == 0:
			continue

		if signals[i] == 1 and not bought:
			coin_holdings = fiat_amount / close_data[i]
			fiat_amount = 0
			bought = True
		elif signals[i] == -1 and bought:
			fiat_amount = coin_holdings * close_data[i]
			coin_holdings = 0
			bought = False

	# Final value if still holding coins
	fiat_amount += coin_holdings * close_data[-1]

	return fiat_amount

def backtest(df: pd.DataFrame, token_id: str, data_timeframe: str, performance_logger: logging.Logger | None = None):
	# Calculate trading signals for all indicators once
	trading_signals = {name: func(df) for func, name in indicator_names.items()}
	best_strategy = { 'Strategy': '', 'Profit': 0, 'Percentage': 0 }
	initial_investment = 10000
	close_prices = df['Close'].to_numpy()

	# Generate combinations of indicators, avoiding comparisons of the same type
	for name1, name2 in combinations(indicator_names.values(), 2):
		fiat_amount = analysis(
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

def main(no_print=True, update_candle=False):
	start_time = time.time()
	if update_candle:
		update_candles()
	candles = get_candles()

	if len(candles) < 1:
		return pd.DataFrame([])

	# Set up logging for performance metrics
	performance_logger = None
	if not no_print:
		performance_logger = setup_performance_logging()

	best_strategies = []
	df_ids = []

	# Process each file
	for candle in candles:
		token_id = candle['token_id']
		fiat = candle['fiat']
		timeframe = candle['timeframe']
		best_strategies.append(backtest(candle['candles'], token_id, timeframe, performance_logger))
		backtest_id = f'{fiat}:{token_id} | {timeframe}'
		dev_print(f"Time to process {backtest_id}: {time.time() - start_time} seconds", no_print)
		df_ids.append(backtest_id)

	dev_print(f"Total runtime: {time.time() - start_time} seconds", no_print)
	coin_profit_df = pd.DataFrame(best_strategies, index=df_ids)
	return coin_profit_df

if __name__ == '__main__':
	result = main(no_print=False, update_candle=True)
	result.to_csv('coin_profit_recommended.csv')
	print(result)
