import numpy as np
import pandas as pd
import logging
from itertools import combinations
import TA_functions

# Read BTCUSDT data file
df = pd.read_csv('data/BTCUSDT_data.csv')
# Drop unnamed and index columns
df.drop(["Unnamed: 0", "index"], axis=1, inplace=True)

# Set up logging
logging.basicConfig(filename='trade_logs.log', level=logging.INFO, format='%(asctime)s - %(message)s')

indicators = [
    TA_functions.use_macd,
    TA_functions.use_sma,
    TA_functions.use_ichimoku,
    TA_functions.use_donchian_channel,
    # TA_functions.use_atr,
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
    TA_functions.use_atr: 'ATR',
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
    ('Ichimoku', 'ATR'): 'Trend direction and volatility confirmation',
    ('RSI65', 'ATR'): 'Overbought/oversold conditions and volatility',
    ('RSI66', 'ATR'): 'Overbought/oversold conditions and volatility',
    ('RSI67', 'ATR'): 'Overbought/oversold conditions and volatility',
    ('RSI68', 'ATR'): 'Overbought/oversold conditions and volatility',
    ('RSI69', 'ATR'): 'Overbought/oversold conditions and volatility',
    ('RSI70', 'ATR'): 'Overbought/oversold conditions and volatility',
    ('RSI71', 'ATR'): 'Overbought/oversold conditions and volatility',
    ('RSI72', 'ATR'): 'Overbought/oversold conditions and volatility',
    ('RSI73', 'ATR'): 'Overbought/oversold conditions and volatility',
    ('RSI74', 'ATR'): 'Overbought/oversold conditions and volatility',
    ('RSI75', 'ATR'): 'Overbought/oversold conditions and volatility',
    ('Ichimoku', 'SMA'): 'Comprehensive trend analysis',
    ('Donchian', 'RSI65'): 'Breakout confirmation and overbought/oversold conditions',
    ('Donchian', 'RSI66'): 'Breakout confirmation and overbought/oversold conditions',
    ('Donchian', 'RSI67'): 'Breakout confirmation and overbought/oversold conditions',
    ('Donchian', 'RSI68'): 'Breakout confirmation and overbought/oversold conditions',
    ('Donchian', 'RSI69'): 'Breakout confirmation and overbought/oversold conditions',
    ('Donchian', 'RSI70'): 'Breakout confirmation and overbought/oversold conditions',
    ('Donchian', 'RSI71'): 'Breakout confirmation and overbought/oversold conditions',
    ('Donchian', 'RSI72'): 'Breakout confirmation and overbought/oversold conditions',
    ('Donchian', 'RSI73'): 'Breakout confirmation and overbought/oversold conditions',
    ('Donchian', 'RSI74'): 'Breakout confirmation and overbought/oversold conditions',
    ('Donchian', 'RSI75'): 'Breakout confirmation and overbought/oversold conditions',
    ('SMA', 'Ichimoku'): 'Trend confirmation and comprehensive trend analysis',
    ('Stochastic14_3_80_20', 'MACD'): 'Momentum and trend reversal confirmation',
    ('Stochastic14_3_85_15', 'MACD'): 'Momentum and trend reversal confirmation',
    ('Stochastic10_3_80_20', 'MACD'): 'Momentum and trend reversal confirmation',
    ('Stochastic10_3_85_15', 'MACD'): 'Momentum and trend reversal confirmation',
    ('Stochastic21_5_80_20', 'MACD'): 'Momentum and trend reversal confirmation',
    ('Stochastic21_5_85_15', 'MACD'): 'Momentum and trend reversal confirmation',
    # Add other use cases as needed
}

# Function to determine the use case
def determine_use_case(indicator_1, indicator_2):
    # Check if indicators are in the known indicators list
    if indicator_1 not in indicator_names.values() or indicator_2 not in indicator_names.values():
        return None  # Or return 'Unknown Use Case' or any other appropriate response

    # Iterate over use cases to find a match
    for (ind_1, ind_2), use_case in use_cases.items():
        if (ind_1 in indicator_1 and ind_2 in indicator_2) or (ind_1 in indicator_2 and ind_2 in indicator_1):
            return use_case
    return 'Unknown Use Case'

# Initialize the list to collect all profit DataFrames
profit_dfs = []

# Example list of files to process
filesyrbtc = ['BTCUSDT_data.csv']

# Process each file
for file in filesyrbtc:
    df = pd.read_csv(f"./data/{file}")
    coin_name = file[:3]
    
    # Log the coin being processed
    logging.info(f"Processing Coin: {coin_name}")
    
    # Create a dictionary to store the profits for the current coin
    coin_profits = {}
    
    for (indicator_func1, indicator_func2) in combinations(indicators, 2):
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

        # Check if use_case is None, indicating an unknown use case, skip if it is
        if use_case is None:
            logging.warning(f"Skipping strategy {strategy_name} due to unknown use case.")
            continue

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
