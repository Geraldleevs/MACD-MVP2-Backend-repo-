import aiohttp
import asyncio
import pandas as pd
from datetime import datetime
import time
from dotenv import load_dotenv, find_dotenv
import os

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

async def process_interval(session, pair, interval, output_folder):
    ohlc_data, last_timestamp = await fetch_ohlc_data(session, pair, interval)
    
    if ohlc_data:
        df = pd.DataFrame(ohlc_data)
        
        # Apply technical analysis indicators
        df = apply_ta_indicators(df)
        
        # Remove the last row
        df = df.iloc[:-1]
        '''
        # Ensure the output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Save to CSV
        filename = os.path.join(output_folder, f'{pair}_{interval}min.csv')
        df.to_csv(filename, index=False)'''

async def main():
    pairs = os.environ.get("BACKTEST_PAIR").split(',')
    intervals = [1, 5, 15, 30, 60, 240, 720, 1440]  # Example intervals in minutes
    '''output_folder = "output_csv_files"  # Define the output folder'''

    async with aiohttp.ClientSession() as session:
        tasks = []
        for pair in pairs:
            for interval in intervals:
                tasks.append(process_interval(session, pair, interval, '''output_folder'''))
        
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    start_time = time.time()
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time} seconds")
