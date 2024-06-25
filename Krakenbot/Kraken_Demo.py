import requests
import pandas as pd
from datetime import datetime

# Import TA calculation functions assuming TA_calculations.py is in the same directory
import TA_calculations
import TA_functions

def get_ohlc_data(pair='XBTGBP', interval=1, since=None):
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

def apply_ta_indicators(df):
    df = TA_functions.use_atr(df)
    df = TA_functions.use_macd(df)
    df = TA_functions.use_sma(df)
    df = TA_functions.use_rsi70_30(df)
    df = TA_functions.use_ichimoku(df)
    df = TA_functions.use_donchian_channel(df)
    df = TA_functions.use_stochastic_14_3_80_20(df)
    return df

def main():
    pair = 'XBTGBP'  # Example pair
    interval = 1  # Example interval in minutes
    since = None  # Fetch all available data

    ohlc_data, last_timestamp = get_ohlc_data(pair, interval, since)
    
    if ohlc_data:
        df = pd.DataFrame(ohlc_data)
        df = apply_ta_indicators(df)
        print(df.tail(1))  # Print the last row with all TA indicators

        # Save the DataFrame to a CSV file
        df.to_csv('ohlc_data_with_ta.csv', index=False)
        print("Data has been saved to ohlc_data_with_ta.csv")
    else:
        print("No data fetched.")

if __name__ == '__main__':
    main()
