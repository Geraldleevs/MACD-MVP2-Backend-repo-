import asyncio
from datetime import datetime, timedelta
import os
import aiohttp
import pandas as pd

try:
    from Krakenbot.models.firebase_candle import FirebaseCandle
    from Krakenbot.utils import clean_kraken_pair
except ModuleNotFoundError:
    from models.firebase_candle import FirebaseCandle
    from utils import clean_kraken_pair

async def __fetch_and_save_candles(pair: str, timeframe: dict, session: aiohttp.ClientSession):
    KRAKEN_OHLC_API = 'https://api.kraken.com/0/public/OHLC'
    firebase = FirebaseCandle(pair, timeframe['label'])
    last = firebase.fetch_last()
    last = last[0]['Unix_Timestamp'] if len(last) > 0 else 1

    async with session.get(KRAKEN_OHLC_API, params={ 'pair': pair, 'interval': timeframe['duration'], 'since': last - 1 }) as response:
        if response.status == 200:
            results = await response.json()
            if len(results['error']) > 0:
                return

            results = clean_kraken_pair(results)[pair]
            results = [{
                'Unix_Timestamp': result[0],
                'Open': float(result[1]),
                'High': float(result[2]),
                'Low': float(result[3]),
                'Close': float(result[4])
            } for result in results]
            results = pd.DataFrame(results)
            firebase.save(results)

            a_year_before = datetime.now() - timedelta(days=367)
            firebase.remove_older_than(date=a_year_before)

async def update_candles():
    firebase = FirebaseCandle()
    all_pairs = firebase.fetch_pairs()
    all_timeframes = os.environ.get('BACKTEST_TIMEFRAME', '').split(';')
    all_timeframes = [{ 'duration': int(timeframe.split('->')[0]), 'label': timeframe.split('->')[1] } for timeframe in all_timeframes]

    async with aiohttp.ClientSession() as session:
        tasks = [__fetch_and_save_candles(pair, timeframe, session) for pair in all_pairs for timeframe in all_timeframes]
        await asyncio.gather(*tasks)

def main():
    asyncio.run(update_candles())

if __name__ == '__main__':
    main()
