import numpy as np
import pandas as pd
import logging
from itertools import combinations
import TA_functions

# Set up logging
logging.basicConfig(filename='trade_logs.log', level=logging.INFO, format='%(asctime)s - %(message)s')

indicators = [
    TA_functions.use_macd,
    TA_functions.use_sma,
    TA_functions.use_ichimoku,
    TA_functions.use_donchian_channel,
    TA_functions.use_rsi65_25,
    TA_functions.use_rsi66_26,
    TA_functions.use_rsi67_27,
    TA_functions.use_rsi68_28,
    TA_functions.use_rsi69_29,
    TA_functions.use_rsi70_30,
    TA_functions.use_rsi71_31,
    TA_functions.use_rsi72_32,
    TA_functions.use_rsi73_33,
    TA_functions.use_rsi74_34,
    TA_functions.use_rsi75_35,
    TA_functions.use_stochastic_14_3_80_20,
    TA_functions.use_stochastic_14_3_85_15,
    TA_functions.use_stochastic_10_3_80_20,
    TA_functions.use_stochastic_10_3_85_15,
    TA_functions.use_stochastic_21_5_80_20,
    TA_functions.use_stochastic_21_5_85_15
]

# Map indicator functions to their names
indicator_names = {
    TA_functions.use_macd: 'MACD',
    TA_functions.use_sma: 'SMA',
    TA_functions.use_ichimoku: 'Ichimoku',
    TA_functions.use_donchian_channel: 'Donchian',
    TA_functions.use_rsi65_25: 'RSI65',
    TA_functions.use_rsi66_26: 'RSI66',
    TA_functions.use_rsi67_27: 'RSI67',
    TA_functions.use_rsi68_28: 'RSI68',
    TA_functions.use_rsi69_29: 'RSI69',
    TA_functions.use_rsi70_30: 'RSI70',
    TA_functions.use_rsi71_31: 'RSI71',
    TA_functions.use_rsi72_32: 'RSI72',
    TA_functions.use_rsi73_33: 'RSI73',
    TA_functions.use_rsi74_34: 'RSI74',
    TA_functions.use_rsi75_35: 'RSI75',
    TA_functions.use_stochastic_14_3_80_20: 'Stochastic14_3_80_20',
    TA_functions.use_stochastic_14_3_85_15: 'Stochastic14_3_85_15',
    TA_functions.use_stochastic_10_3_80_20: 'Stochastic10_3_80_20',
    TA_functions.use_stochastic_10_3_85_15: 'Stochastic10_3_85_15',
    TA_functions.use_stochastic_21_5_80_20: 'Stochastic21_5_80_20',
    TA_functions.use_stochastic_21_5_85_15: 'Stochastic21_5_85_15'
}

# Create a mapping of indicators to their base types
indicator_base_types = {
    'MACD': 'MACD',
    'SMA': 'SMA',
    'Ichimoku': 'Ichimoku',
    'Donchian': 'Donchian',
    'RSI65': 'RSI',
    'RSI66': 'RSI',
    'RSI67': 'RSI',
    'RSI68': 'RSI',
    'RSI69': 'RSI',
    'RSI70': 'RSI',
    'RSI71': 'RSI',
    'RSI72': 'RSI',
    'RSI73': 'RSI',
    'RSI74': 'RSI',
    'RSI75': 'RSI',
    'Stochastic14_3_80_20': 'Stochastic',
    'Stochastic14_3_85_15': 'Stochastic',
    'Stochastic10_3_80_20': 'Stochastic',
    'Stochastic10_3_85_15': 'Stochastic',
    'Stochastic21_5_80_20': 'Stochastic',
    'Stochastic21_5_85_15': 'Stochastic'
}

# Filter combinations to exclude pairs with the same base type
valid_combinations = [
    (ind1, ind2) for ind1, ind2 in combinations(indicators, 2)
    if indicator_base_types[indicator_names[ind1]] != indicator_base_types[indicator_names[ind2]]
]

# Update the use cases dictionary as needed
use_cases = {
    # Existing use cases
    ('RSI65', 'MACD'): 'Identifying and confirming trend reversals',
    ('RSI66', 'MACD'): 'Identifying and confirming trend reversals',
    ('RSI67', 'MACD'): 'Identifying and confirming trend reversals',
    ('RSI68', 'MACD'): 'Identifying and confirming trend reversals',
    ('RSI69', 'MACD'): 'Identifying and confirming trend reversals',
    ('RSI70', 'MACD'): 'Identifying and confirming trend reversals',
    ('RSI71', 'MACD'): 'Identifying and confirming trend reversals',
    ('RSI72', 'MACD'): 'Identifying and confirming trend reversals',
    ('RSI73', 'MACD'): 'Identifying and confirming trend reversals',
    ('RSI74', 'MACD'): 'Identifying and confirming trend reversals',
    ('RSI75', 'MACD'): 'Identifying and confirming trend reversals',
    ('SMA', 'RSI65'): 'Trend direction and entry/exit timing',
    ('SMA', 'RSI66'): 'Trend direction and entry/exit timing',
    ('SMA', 'RSI67'): 'Trend direction and entry/exit timing',
    ('SMA', 'RSI68'): 'Trend direction and entry/exit timing',
    ('SMA', 'RSI69'): 'Trend direction and entry/exit timing',
    ('SMA', 'RSI70'): 'Trend direction and entry/exit timing',
    ('SMA', 'RSI71'): 'Trend direction and entry/exit timing',
    ('SMA', 'RSI72'): 'Trend direction and entry/exit timing',
    ('SMA', 'RSI73'): 'Trend direction and entry/exit timing',
    ('SMA', 'RSI74'): 'Trend direction and entry/exit timing',
    ('SMA', 'RSI75'): 'Trend direction and entry/exit timing',
    ('Ichimoku', 'MACD'): 'Comprehensive trend and momentum analysis',
    ('Donchian', 'ATR'): 'Breakout confirmation and volatility assessment',
    ('RSI65', 'Donchian'): 'Overbought/oversold conditions and breakout confirmation',
    ('RSI66', 'Donchian'): 'Overbought/oversold conditions and breakout confirmation',
    ('RSI67', 'Donchian'): 'Overbought/oversold conditions and breakout confirmation',
    ('RSI68', 'Donchian'): 'Overbought/oversold conditions and breakout confirmation',
    ('RSI69', 'Donchian'): 'Overbought/oversold conditions and breakout confirmation',
    ('RSI70', 'Donchian'): 'Overbought/oversold conditions and breakout confirmation',
    ('RSI71', 'Donchian'): 'Overbought/oversold conditions and breakout confirmation',
    ('RSI72', 'Donchian'): 'Overbought/oversold conditions and breakout confirmation',
    ('RSI73', 'Donchian'): 'Overbought/oversold conditions and breakout confirmation',
    ('RSI74', 'Donchian'): 'Overbought/oversold conditions and breakout confirmation',
    ('RSI75', 'Donchian'): 'Overbought/oversold conditions and breakout confirmation',
    ('SMA', 'ATR'): 'Trend confirmation and volatility assessment',
    ('Ichimoku', 'RSI65'): 'Trend direction and momentum confirmation',
    ('Ichimoku', 'RSI66'): 'Trend direction and momentum confirmation',
    ('Ichimoku', 'RSI67'): 'Trend direction and momentum confirmation',
    ('Ichimoku', 'RSI68'): 'Trend direction and momentum confirmation',
    ('Ichimoku', 'RSI69'): 'Trend direction and momentum confirmation',
    ('Ichimoku', 'RSI70'): 'Trend direction and momentum confirmation',
    ('Ichimoku', 'RSI71'): 'Trend direction and momentum confirmation',
    ('Ichimoku', 'RSI72'): 'Trend direction and momentum confirmation',
    ('Ichimoku', 'RSI73'): 'Trend direction and momentum confirmation',
    ('Ichimoku', 'RSI74'): 'Trend direction and momentum confirmation',
    ('Ichimoku', 'RSI75'): 'Trend direction and momentum confirmation',
    ('MACD', 'ATR'): 'Momentum and volatility confirmation',
    ('SMA', 'MACD'): 'Trend direction and momentum',
    ('Donchian', 'MACD'): 'Breakout and momentum confirmation',
    ('Ichimoku', 'ATR'): 'Trend and volatility analysis',
    ('Stochastic14_3_80_20', 'MACD'): 'Momentum and trend confirmation',
    ('Stochastic14_3_85_15', 'MACD'): 'Momentum and trend confirmation',
    ('Stochastic10_3_80_20', 'MACD'): 'Momentum and trend confirmation',
    ('Stochastic10_3_85_15', 'MACD'): 'Momentum and trend confirmation',
    ('Stochastic21_5_80_20', 'MACD'): 'Momentum and trend confirmation',
    ('Stochastic21_5_85_15', 'MACD'): 'Momentum and trend confirmation'
    # Additional use cases can be added here
}

def determine_use_case(indicator1, indicator2):
    use_case = use_cases.get((indicator1, indicator2))
    if use_case is None:
        use_case = use_cases.get((indicator2, indicator1))
    return use_case

# Initialize the list to collect all profit DataFrames
profit_dfs = []

# Example list of files to process
filesyr = ['BTCUSDT_data.csv', 'DOGEUSDT_data.csv', 'ETHUSDT_data.csv', 'LINKUSDT_data.csv', 'UNIUSDT_data.csv']
filesyrbtc = ['BTCUSDT_data.csv']
filesyrbtc5m = ['BTCUSDT-5m-2024-05-19.csv']

# Process each file
for file in filesyrbtc:
    df = pd.read_csv(f"./data/{file}")
    coin_name = file[:3]

    # Log the coin being processed
    logging.info(f"Processing Coin: {coin_name}")

    # Create a dictionary to store the profits for the current coin
    coin_profits = {}

    for (indicator_func1, indicator_func2) in valid_combinations:
        trading_frame_1 = indicator_func1(df.copy())  # Ensure to pass a copy to avoid modifying the original df
        trading_frame_2 = indicator_func2(df.copy())  # Ensure to pass a copy to avoid modifying the original df
        trading_data = df.copy()
        trading_data['buy_sell_1'] = trading_frame_1.iloc[:, -1]
        trading_data['buy_sell_2'] = trading_frame_2.iloc[:, -1]

        position = False
        coin = 0
        fiat_amount = 10000
        for idx, row in trading_data.iterrows():
            if (row['buy_sell_1'] == 1) and (row['buy_sell_2'] == 1) and (position == False):
                position = True
                coin = fiat_amount / row['Close']
                fiat_amount = 0

                # Log the trade
                trade_message = f"  BUY: Strategy={indicator_names[indicator_func1]} & {indicator_names[indicator_func2]}, Price={row['Close']}"
                logging.info(trade_message)

            elif ((row['buy_sell_1'] == -1) and (row['buy_sell_2'] == -1)) and (position == True):
                fiat_amount = coin * row['Close']
                coin = 0
                position = False

                # Log the trade
                trade_message = f"  SELL: Strategy={indicator_names[indicator_func1]} & {indicator_names[indicator_func2]}, Price={row['Close']}"
                logging.info(trade_message)

        fiat_amount += coin * trading_data.iloc[-1]['Close']
        coin = 0

        # Determine the strategy name
        strategy_name = f'{indicator_names[indicator_func1]} & {indicator_names[indicator_func2]}'

        # Determine the use case
        use_case = determine_use_case(indicator_names[indicator_func1], indicator_names[indicator_func2])

        # If use case is unknown, log a warning but still include the strategy
        if use_case is None:
            use_case = 'Unknown Use Case'
            logging.warning(f"Unknown use case for strategy {strategy_name}")

        # Store the profit for the current coin and strategy with the use case
        coin_profits[f'{strategy_name} ({use_case})'] = fiat_amount

        # Log the completion of the strategy execution with a new line for clarity
        logging.info(f"Completed Strategy: {strategy_name}, Coin: {coin_name}, Profit: {fiat_amount}, Use Case: {use_case}\n")

    # Convert the coin_profits dictionary to a DataFrame
    coin_profits_df = pd.DataFrame(coin_profits, index=[coin_name])

    # Append the coin profits DataFrame to the list
    profit_dfs.append(coin_profits_df)

# Concatenate all the profit DataFrames into a single DataFrame
coin_profit_df = pd.concat(profit_dfs)

# Determine the best strategy for each coin
coin_profit_df['Recommended Strategy'] = coin_profit_df.idxmax(axis=1)

# Save the trades log to a CSV file
coin_profit_df.to_csv('coin_profit.csv')

print(coin_profit_df)
