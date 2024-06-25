import aiohttp
import asyncio
import pandas as pd
from datetime import datetime

# Import TA calculation functions assuming TA_calculations.py is in the same directory
import TA_calculations
import TA_functions

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
                print(f"Error for {pair} at {interval} minutes interval:", data['error'])
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
            print(f"Failed to fetch data for {pair} at {interval} minutes interval. Status code: {response.status}")
            return None, None

def apply_ta_indicators(df):
    df = TA_functions.use_atr(df)
    df['signal_atr'] = df['buy_sell'].apply(lambda x: 1 if x == 'buy' else -1 if x == 'sell' else 0)
    
    df = TA_functions.use_macd(df)
    df['signal_macd'] = df['buy_sell'].apply(lambda x: 1 if x == 'buy' else -1 if x == 'sell' else 0)
    
    df = TA_functions.use_sma(df)
    df['signal_sma'] = df['buy_sell'].apply(lambda x: 1 if x == 'buy' else -1 if x == 'sell' else 0)
    
    df = TA_functions.use_rsi70_30(df)
    df['signal_rsi'] = df['buy_sell'].apply(lambda x: 1 if x == 'buy' else -1 if x == 'sell' else 0)
    
    df = TA_functions.use_ichimoku(df)
    df['signal_ichimoku'] = df['buy_sell'].apply(lambda x: 1 if x == 'buy' else -1 if x == 'sell' else 0)
    
    df = TA_functions.use_donchian_channel(df)
    df['signal_donchian'] = df['buy_sell'].apply(lambda x: 1 if x == 'buy' else -1 if x == 'sell' else 0)
    
    df = TA_functions.use_stochastic_14_3_80_20(df)
    df['signal_stochastic'] = df['buy_sell'].apply(lambda x: 1 if x == 'buy' else -1 if x == 'sell' else 0)
    
    # Combine signals
    df['combined_signal'] = (df['signal_atr'] + df['signal_macd'] + df['signal_sma'] + 
                             df['signal_rsi'] + df['signal_ichimoku'] + df['signal_donchian'] + 
                             df['signal_stochastic'])
    
    df['buy_sell'] = df['combined_signal'].apply(lambda x: 'buy' if x > 0 else 'sell' if x < 0 else 'hold')

    return df

async def process_interval(session, pair, interval):
    ohlc_data, last_timestamp = await fetch_ohlc_data(session, pair, interval)
    
    if ohlc_data:
        df = pd.DataFrame(ohlc_data)
        
        # Apply technical analysis indicators
        df = apply_ta_indicators(df)
        
        # Remove the last row
        df = df.iloc[:-1]
        
        # Save the DataFrame to a CSV file
        filename = f'ohlc_data_with_ta_{pair}_{interval}min.csv'
        df.to_csv(filename, index=False)
        print(f"Data has been saved to {filename}")
        
        # Print the last row with all TA indicators
        print(f"Last row with TA indicators for {pair} at {interval} minutes interval:")
        print(df.tail(1))

        # Print the last timestamp in Unix format (UTC)
        last_timestamp_str = datetime.utcfromtimestamp(last_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Last timestamp fetched for {pair} at {interval} minutes interval (UTC):", last_timestamp_str)
    else:
        print(f"No data fetched for {pair} at {interval} minutes interval.")

async def main():
    pairs = ['XBTGBP', 'ETHGBP']  # Example pairs
    intervals = [1, 15, 60, 240, 1440]  # Example intervals in minutes

    async with aiohttp.ClientSession() as session:
        tasks = []
        for pair in pairs:
            for interval in intervals:
                print(f"Processing {pair} at {interval} minutes interval")
                tasks.append(process_interval(session, pair, interval))
        
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
