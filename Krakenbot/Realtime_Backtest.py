import aiohttp
import asyncio
import pandas as pd
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv, find_dotenv
import os
from typing import List, Dict

# Import TA calculation functions assuming TA_calculations.py is in the same directory
import TA_calculations
import TA_functions

# Load environment variables from .env file
dotenv_path = find_dotenv()
if not dotenv_path:
    raise FileNotFoundError("Could not find .env file")
load_dotenv(dotenv_path)

async def fetch_ohlc_data(session, pair, interval, since=None):
    url = 'https://api.kraken.com/0/public/OHLC'
    params = {
        'pair': pair,
        'interval': interval
    }
    if since:
        params['since'] = since

    async with session.get(url, params=params) as response:
        if response.status == 200:
            data = await response.json()
            if data['error']:
                return None, None
            else:
                result = data['result']
                last_timestamp = int(result['last'])
                ohlc_data = []
                for key in result:
                    if key != 'last':
                        for entry in result[key]:
                            timestamp = int(entry[0])
                            timestamp_str = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                            ohlc_data.append({
                                'Unix_Timestamp': timestamp,
                                'Timestamp': timestamp_str,
                                'Open': float(entry[1]),
                                'High': float(entry[2]),
                                'Low': float(entry[3]),
                                'Close': float(entry[4]),
                                'Volume': float(entry[5]),
                                'Count': float(entry[6])  # Treating 'Count' as float to avoid conversion error
                            })
                return ohlc_data, last_timestamp
        else:
            return None, None

def apply_ta_indicators(df):
    # Apply each indicator and use the 'buy_sell' column directly
    indicator_functions = [
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
    
    for func in indicator_functions:
        df = func(df)
        indicator_name = func.__name__.replace('use_', 'indicator_')
        df[indicator_name] = df['buy_sell']
        df.drop(['buy_sell'], axis=1, inplace=True)
    
    # Combine indicators for each pair of indicators
    df['indicator_rsi_macd'] = df.apply(lambda x: 1 if x['indicator_rsi70_30'] == 1 and x['indicator_macd'] == 1 else 
                                                  -1 if x['indicator_rsi70_30'] == -1 and x['indicator_macd'] == -1 else 0, axis=1)
    df['indicator_sma_ichimoku'] = df.apply(lambda x: 1 if x['indicator_sma'] == 1 and x['indicator_ichimoku'] == 1 else 
                                                   -1 if x['indicator_sma'] == -1 and x['indicator_ichimoku'] == -1 else 0, axis=1)
    df['indicator_donchian_stochastic'] = df.apply(lambda x: 1 if x['indicator_donchian_channel'] == 1 and x['indicator_stochastic_14_3_80_20'] == 1 else 
                                                           -1 if x['indicator_donchian_channel'] == -1 and x['indicator_stochastic_14_3_80_20'] == -1 else 0, axis=1)

    return df

async def process_interval(session, pair, interval, since):
    ohlc_data, last_timestamp = await fetch_ohlc_data(session, pair, interval, since)
    
    if ohlc_data:
        df = pd.DataFrame(ohlc_data)
        
        # Apply technical analysis indicators
        df = apply_ta_indicators(df)
        
        # Remove the last row
        df = df.iloc[:-1]
        
        return df
    return None

async def apply_backtest(pairs: List[str], intervals: List[int], since: datetime) -> Dict[str, Dict[str, pd.DataFrame]]:
    since_timestamp = since.timestamp()
    results = {}

    async with aiohttp.ClientSession() as session:
        tasks = [process_interval(session, pair, interval, since_timestamp) for pair in pairs for interval in intervals]
        
        raw_data = await asyncio.gather(*tasks)

        for i, pair in enumerate(pairs):
            pair_data = {}
            for j, interval in enumerate(intervals):
                df = raw_data[i * len(intervals) + j]
                if df is not None:
                    pair_data[str(interval)] = df
            results[pair] = pair_data
    
    return results

def get_livetrade_result(df: pd.DataFrame, strategy: str) -> int:
    strategy_mapping = {
        'macd': 'indicator_macd',
        'sma': 'indicator_sma',
        'ichimoku': 'indicator_ichimoku',
        'donchian_channel': 'indicator_donchian_channel',
        'rsi65_25': 'indicator_rsi65_25',
        'rsi66_26': 'indicator_rsi66_26',
        'rsi67_27': 'indicator_rsi67_27',
        'rsi68_28': 'indicator_rsi68_28',
        'rsi69_29': 'indicator_rsi69_29',
        'rsi70_30': 'indicator_rsi70_30',
        'rsi71_31': 'indicator_rsi71_31',
        'rsi72_32': 'indicator_rsi72_32',
        'rsi73_33': 'indicator_rsi73_33',
        'rsi74_34': 'indicator_rsi74_34',
        'rsi75_35': 'indicator_rsi75_35',
        'stochastic_14_3_80_20': 'indicator_stochastic_14_3_80_20',
        'stochastic_14_3_85_15': 'indicator_stochastic_14_3_85_15',
        'stochastic_10_3_80_20': 'indicator_stochastic_10_3_80_20',
        'stochastic_10_3_85_15': 'indicator_stochastic_10_3_85_15',
        'stochastic_21_5_80_20': 'indicator_stochastic_21_5_80_20',
        'stochastic_21_5_85_15': 'indicator_stochastic_21_5_85_15',
        'rsi_macd': 'indicator_rsi_macd',
        'sma_ichimoku': 'indicator_sma_ichimoku',
        'donchian_stochastic': 'indicator_donchian_stochastic'
    }

    if strategy in strategy_mapping:
        last_signal = df[strategy_mapping[strategy]].iloc[-1]
    else:
        raise ValueError("Unknown strategy")

    return last_signal

async def main():
    pairs = ['XBTGBP', 'ETHGBP', 'DOGEUSDT']
    intervals = [1, 60, 240, 1440]
    since = datetime.now() - timedelta(days=366)
    results = await apply_backtest(pairs, intervals, since)
    
    # Create output directory if it doesn't exist
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for pair in results:
        for interval in results[pair]:
            df = results[pair][interval]
            df.to_csv(f'{output_dir}/{pair}_{interval}.csv')

if __name__ == '__main__':
    start_time = time.time()
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time} seconds")
