import numpy as np
import pandas as pd
import logging
from itertools import combinations
import TA_functions

# Function to set up logging for each coin file
def setup_logging(coin_name):
    logger = logging.getLogger(coin_name)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(f'{coin_name}_trade_logs.log')
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

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

# Define use cases and recommended timeframes
use_cases = {
    ('RSI', 'MACD'): ('Identifying and confirming trend reversals', '1H'),
    ('SMA', 'RSI'): ('Trend direction and entry/exit timing', '1D'),
    ('Ichimoku', 'MACD'): ('Comprehensive trend and momentum analysis', '4H'),
    ('Donchian', 'ATR'): ('Breakout confirmation and volatility assessment', '1D'),
    ('RSI', 'Donchian'): ('Overbought/oversold conditions and breakout confirmation', '1H'),
    ('SMA', 'ATR'): ('Trend confirmation and volatility assessment', '1D'),
    ('Ichimoku', 'RSI'): ('Trend direction and momentum confirmation', '4H'),
    ('MACD', 'ATR'): ('Momentum and volatility confirmation', '1H'),
    ('SMA', 'MACD'): ('Trend direction and momentum', '1D'),
    ('Donchian', 'MACD'): ('Breakout and momentum confirmation', '1H'),
    ('Ichimoku', 'ATR'): ('Trend and volatility analysis', '4H'),
    ('Stochastic', 'MACD'): ('Momentum and trend confirmation', '1H')
    # Additional use cases can be added here
}

# Function to determine the base type of an indicator
def get_base_type(indicator_name):
    if 'RSI' in indicator_name:
        return 'RSI'
    elif 'Stochastic' in indicator_name:
        return 'Stochastic'
    else:
        return indicator_name

# Function to determine the use case and timeframe
def determine_use_case(indicator1, indicator2):
    base_type1 = get_base_type(indicator1)
    base_type2 = get_base_type(indicator2)
    use_case = use_cases.get((base_type1, base_type2))
    if use_case is None:
        use_case = use_cases.get((base_type2, base_type1))
    if use_case is None:
        use_case = ('Unknown Use Case', 'Unknown Timeframe')
    return use_case

# Initialize the list to collect all profit DataFrames
profit_dfs = []

# Example list of files to process
files = [
    'Concatenated-BTCUSDT-1h-2023-4.csv',
    'Concatenated-ETHUSDT-1h-2023-4.csv',
    # Add other file names as needed
]

# Process each file
for file in files:
    df = pd.read_csv(f"./data/{file}")
    coin_name = file.split('.')[0]  # Use the file name without extension as the coin name

    # Set up logging for the current coin
    logger = setup_logging(coin_name)

    # Log the coin being processed
    logger.info(f"Processing Coin: {coin_name}")

    # Create a dictionary to store the profits for the current coin
    coin_profits = {}

    # Calculate trading signals for all indicators once
    trading_signals = {name: func(df) for func, name in indicator_names.items()}

    # Generate combinations of indicators, avoiding comparisons of the same type
    indicator_combinations = [
        (name1, name2) for name1, name2 in combinations(indicator_names.values(), 2)
        if get_base_type(name1) != get_base_type(name2)
    ]

    for (name1, name2) in indicator_combinations:
        trading_data = df.copy()
        trading_data['buy_sell_1'] = trading_signals[name1].iloc[:, -1]
        trading_data['buy_sell_2'] = trading_signals[name2].iloc[:, -1]

        # Vectorized buy/sell logic
        buy_signals = (trading_data['buy_sell_1'] == 1) & (trading_data['buy_sell_2'] == 1)
        sell_signals = (trading_data['buy_sell_1'] == -1) & (trading_data['buy_sell_2'] == -1)

        positions = np.where(buy_signals, 1, np.where(sell_signals, -1, 0))
        positions = pd.Series(positions).ffill().fillna(0).values

        # Calculate coin holdings and fiat amount
        coin_holdings = 0
        fiat_amount = 10000
        position = False

        for i in range(len(positions)):
            if positions[i] == 1 and not position:
                coin_holdings = fiat_amount / trading_data['Close'].iloc[i]
                fiat_amount = 0
                position = True
                trade_message = f"  BUY: Strategy={name1} & {name2}, Price={trading_data['Close'].iloc[i]}"
                logger.info(trade_message)
            elif positions[i] == -1 and position:
                fiat_amount = coin_holdings * trading_data['Close'].iloc[i]
                coin_holdings = 0
                position = False
                trade_message = f"  SELL: Strategy={name1} & {name2}, Price={trading_data['Close'].iloc[i]}"
                logger.info(trade_message)
        
        # Final value if still holding coins
        if coin_holdings > 0:
            fiat_amount = coin_holdings * trading_data['Close'].iloc[-1]
            coin_holdings = 0

        strategy_name = f'{name1} & {name2}'
        use_case, timeframe = determine_use_case(name1, name2)
        
        if use_case == 'Unknown Use Case':
            logger.warning(f"Unknown use case for strategy {strategy_name}")

        coin_profits[f'{strategy_name} ({use_case}, {timeframe})'] = fiat_amount
        logger.info(f"Completed Strategy: {strategy_name}, Coin: {coin_name}, Profit: {fiat_amount}, Use Case: {use_case}, Timeframe: {timeframe}\n")

    coin_profits_df = pd.DataFrame(coin_profits, index=[coin_name])
    profit_dfs.append(coin_profits_df)

# Concatenate all the profit DataFrames into a single DataFrame
coin_profit_df = pd.concat(profit_dfs)

# Determine the best strategy for each coin
coin_profit_df['Recommended Strategy'] = coin_profit_df.idxmax(axis=1)

# Add a column with the profit of the recommended strategy
coin_profit_df['Profit of Recommended Strategy'] = coin_profit_df.apply(
    lambda row: row[row['Recommended Strategy']], axis=1
)

# Calculate the percentage increase for each coin
initial_investment = 10000
coin_profit_df['Percentage Increase'] = ((coin_profit_df['Profit of Recommended Strategy'] - initial_investment) / initial_investment) * 100

# Assuming coin_profit_df is already created as per the code provided
# Keep only the first and last two columns
coin_profit_df = coin_profit_df.iloc[:, [-3, -2, -1]]

# Save the modified DataFrame to a CSV file
coin_profit_df.to_csv('coin_profit_recommended.csv')

print(coin_profit_df)
