import requests
import json
from datetime import datetime, timedelta
import time
import pandas as pd
import numpy as np
from itertools import combinations

from TA_calculations import *
from TA_functions import *

def get_ohlc_data(pair='XBTUSD', interval=5, since=None):
    url = 'https://api.kraken.com/0/public/OHLC'
    params = {
        'pair': pair,
        'interval': interval
    }
    if since:
        params['since'] = since

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data['error']:
            print("Error:", data['error'])
            return None, None
        else:
            result = data['result']
            last_timestamp = result['last']
            ohlc_data = []
            for key in result:
                if key != 'last':
                    for entry in result[key]:
                        timestamp = datetime.utcfromtimestamp(entry[0]).strftime('%Y-%m-%d %H:%M:%S')
                        ohlc_data.append({
                            'Timestamp': timestamp,
                            'Open': float(entry[1]),
                            'High': float(entry[2]),
                            'Low': float(entry[3]),
                            'Close': float(entry[4]),
                            'Volume': float(entry[5]),
                            'Count': float(entry[6])  # Treating 'Count' as float to avoid conversion error
                        })
            return ohlc_data, last_timestamp
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None, None

def apply_trading_strategy(df, indicators, min_data_points=50):
    if 'atr' in indicators:
        df = use_atr(df)
        df.rename(columns={'buy_sell': 'buy_sell_atr'}, inplace=True)
    if 'macd' in indicators:
        df = use_macd(df)
        df.rename(columns={'buy_sell': 'buy_sell_macd'}, inplace=True)
    if 'sma' in indicators:
        df = use_sma(df)
        df.rename(columns={'buy_sell': 'buy_sell_sma'}, inplace=True)
    if 'rsi' in indicators:
        df = use_rsi70_30(df)
        df.rename(columns={'buy_sell': 'buy_sell_rsi'}, inplace=True)
    if 'ichimoku' in indicators:
        df = use_ichimoku(df)
        df.rename(columns={'buy_sell': 'buy_sell_ichimoku'}, inplace=True)
    if 'donchian' in indicators:
        df = use_donchian_channel(df)
        df.rename(columns={'buy_sell': 'buy_sell_donchian'}, inplace=True)
    if 'stochastic' in indicators:
        df = use_stochastic_14_3_80_20(df)
        df.rename(columns={'buy_sell': 'buy_sell_stochastic'}, inplace=True)

    # Combine signals from the selected indicators
    signal_columns = [f'buy_sell_{indicator}' for indicator in indicators]
    df['combined_signal'] = df[signal_columns].sum(axis=1)
    
    # Generate final buy/sell signal based on combined signals
    df['buy_sell'] = 0
    df.loc[df['combined_signal'] > 0, 'buy_sell'] = 1
    df.loc[df['combined_signal'] < 0, 'buy_sell'] = -1
    
    # Drop the combined_signal column but keep the TA values
    df.drop('combined_signal', axis=1, inplace=True)
    
    return df

def execute_trade(trade_type, balance, position_size, price):
    if trade_type == 'buy':
        balance['btc'] += position_size
        balance['usd'] -= position_size * price
    elif trade_type == 'sell':
        balance['btc'] -= position_size
        balance['usd'] += position_size * price
    return balance

if __name__ == '__main__':
    last_checked = None
    interval_minutes = 1  # Set this to your desired interval in minutes

    # Initialize fake balance
    balance = {'usd': 10000, 'btc': 0}
    position_size = 0.01  # Size of each trade in BTC
    trade_history = []

    # List of all indicators
    indicators_list = ['atr', 'macd', 'sma', 'rsi', 'ichimoku', 'donchian', 'stochastic']

    # Generate all possible pairs of indicators
    indicator_pairs = list(combinations(indicators_list, 2))

    # Combine individual indicators and pairs for selection
    all_combinations = [(indicator,) for indicator in indicators_list] + indicator_pairs

    # User selects indicator pair or individual indicator
    print("Select an indicator or pair of indicators to use:")
    for i, combo in enumerate(all_combinations):
        print(f"{i + 1}: {combo}")

    selected_combo_index = int(input("Enter the number of the selected combination: ")) - 1
    selected_indicators = all_combinations[selected_combo_index]

    df = pd.DataFrame()  # Initialize an empty DataFrame to store all data

    while True:
        current_time = datetime.utcnow()
        # Sleep until the next interval mark
        next_check = (current_time + timedelta(minutes=interval_minutes - (current_time.minute % interval_minutes))).replace(second=0, microsecond=0)
        time_to_sleep = (next_check - current_time).total_seconds()
        print(f"Sleeping for {time_to_sleep} seconds until the next {interval_minutes}-minute mark.")
        time.sleep(time_to_sleep)
        
        ohlc_data, last_timestamp = get_ohlc_data(pair='XBTUSD', interval=interval_minutes, since=last_checked)

        if ohlc_data:
            new_df = pd.DataFrame(ohlc_data)
            new_df.reset_index(drop=True, inplace=True)  # Ensure the new DataFrame index is unique

            # Concatenate new data with the existing data and drop duplicates based on 'Timestamp'
            df.reset_index(drop=True, inplace=True)
            new_df.reset_index(drop=True, inplace=True)
            df = pd.concat([df, new_df]).drop_duplicates(subset='Timestamp').reset_index(drop=True)

            # Identify and print duplicate rows based on 'Timestamp'
            duplicate_rows = df[df.duplicated(subset='Timestamp', keep=False)]
            if not duplicate_rows.empty:
                print("Duplicate rows based on 'Timestamp':")
                print(duplicate_rows)

            # Check if the DataFrame is empty after concatenation
            if df.empty:
                print("DataFrame is empty after concatenation.")
                continue

            # Check if 'Close' column exists
            if 'Close' not in df.columns:
                print("Column 'Close' not found in DataFrame.")
                continue

            # Keep only the last 50 rows to ensure indices remain unique
            df = df.tail(50).reset_index(drop=True)

            # Debugging: print the indices to ensure they are unique
            print(f"\nIndices after concatenation: {df.index}")

            # Debugging: print the closing prices
            print(f"\nClosing Prices:\n{df['Close'].tolist()}")
            
            df = apply_trading_strategy(df, selected_indicators)
            
            latest_data = df.iloc[-1]
            latest_signal = latest_data['buy_sell']
            latest_close = latest_data['Close']
            
            # Display TA values and signals
            print(f"\nTimestamp: {latest_data['Timestamp']}")
            print(f"Close: {latest_close}")
            for indicator in selected_indicators:
                print(f"{indicator.upper()}:")
                indicator_cols = [col for col in latest_data.index if indicator in col]
                print(latest_data[indicator_cols].dropna())  # Drop NaN values for display
            print(f"Signal: {'Buy' if latest_signal == 1 else 'Sell' if latest_signal == -1 else 'Hold'}\n")
            
            if latest_signal == 1:  # Buy signal
                balance = execute_trade('buy', balance, position_size, latest_close)
                trade_history.append({
                    'Timestamp': latest_data['Timestamp'],
                    'Type': 'Buy',
                    'Price': latest_close,
                    'Position Size': position_size,
                    'Balance': balance.copy()
                })
                print(f"Executed Buy at {latest_close}")
            elif latest_signal == -1:  # Sell signal
                balance = execute_trade('sell', balance, position_size, latest_close)
                trade_history.append({
                    'Timestamp': latest_data['Timestamp'],
                    'Type': 'Sell',
                    'Price': latest_close,
                    'Position Size': position_size,
                    'Balance': balance.copy()
                })
                print(f"Executed Sell at {latest_close}")

            print(f"Balance: USD {balance['usd']}, BTC {balance['btc']}")
            last_checked = last_timestamp

        else:
            print("No new data fetched.")

        # Sleep for a short duration before checking again to avoid making too many requests
        time.sleep(60)  # Check every minute after fetching the latest data
