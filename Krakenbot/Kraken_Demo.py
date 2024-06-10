import requests
import json
from datetime import datetime, timedelta
import time

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
                            'Open': entry[1],
                            'High': entry[2],
                            'Low': entry[3],
                            'Close': entry[4],
                            'Volume': entry[5],
                            'Count': entry[6]
                        })
            return ohlc_data, last_timestamp
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None, None

if __name__ == '__main__':
    last_checked = None
    interval_minutes = 5  # Set this to your desired interval in minutes

    while True:
        current_time = datetime.utcnow()
        # Sleep until the next interval mark
        next_check = (current_time + timedelta(minutes=interval_minutes - (current_time.minute % interval_minutes))).replace(second=0, microsecond=0)
        time_to_sleep = (next_check - current_time).total_seconds()
        print(f"Sleeping for {time_to_sleep} seconds until the next {interval_minutes}-minute mark.")
        time.sleep(time_to_sleep)
        
        ohlc_data, last_timestamp = get_ohlc_data(pair='XBTUSD', interval=interval_minutes, since=last_checked)

        if ohlc_data:
            for data in ohlc_data:
                print(f"Timestamp: {data['Timestamp']}, Open: {data['Open']}, High: {data['High']}, Low: {data['Low']}, Close: {data['Close']}, Volume: {data['Volume']}, Count: {data['Count']}")
            last_checked = last_timestamp

        # Sleep for a short duration before checking again to avoid making too many requests
        time.sleep(60)  # Check every minute after fetching the latest data
