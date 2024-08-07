import asyncio
import os

try:
    from Krakenbot.models.firebase_candle import FirebaseCandle
except ModuleNotFoundError:
    from models.firebase_candle import FirebaseCandle

async def __get_candle(pair: str, timeframe: str):
		firebase = FirebaseCandle(pair, timeframe)
		candles = firebase.fetch_all()
		token_id = firebase.fetch_cur_token()

		if candles is not None and token_id is not None:
				return { 'pair': pair, 'timeframe': timeframe, 'candles': candles, 'token_id': token_id }
		return None

async def get_candles():
    firebase = FirebaseCandle()
    all_pairs = firebase.fetch_pairs()
    all_timeframes = os.environ.get('BACKTEST_TIMEFRAME', '').split(';')
    all_timeframes = [timeframe.split('->')[1] for timeframe in all_timeframes]

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(__get_candle(pair, timeframe)) for pair in all_pairs for timeframe in all_timeframes]
        results = await asyncio.gather(*tasks)
        return [result for result in results if result is not None]

def main():
    results = asyncio.run(get_candles())
    return results

if __name__ == '__main__':
    results = main()
    print("Number of Pair/Timeframe:", len(results))
