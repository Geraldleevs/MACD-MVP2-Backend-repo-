from models.local_firebase_candle import LocalFirebaseCandle
from utils import KRAKEN_CLEAN_PAIRS
from datetime import datetime, timedelta
from os import path
import os
import pandas as pd
import glob

'''
This code is used to load all OHLCVT Data from csv files and upload onto our firebase database 'candles'
The reason of doing this is that Kraken only provide latest 720 candles (Equivalent to 12 hours in 1 min candles)
So if there is any new token added, we need to download the OHLC files from kraken, for a whole OHLC history
Link to download: https://support.kraken.com/hc/en-us/articles/360047124832-Downloadable-historical-OHLCVT-Open-High-Low-Close-Volume-Trades-data

Then, extract the csv files into "./data/Kraken/*.csv"
And run this code to load 1 year worth of data into our own database
So that we can backtest with a whole year of OHLC data in the future easily

This can also be used when we lose track of a token's candle history
Such as having a gap of few days between the OHLC data in our database
Download the csv, and run this file again to load them all

Change the `since` parameter if you do not need a whole year
Because it will cost a lot of document write quota in firebase

This file can only be run by executing
`python -u "update_file_candles_to_firebase.py"
'''

def __main(since: datetime, has_header=False):
	since = since.timestamp()
	files = glob.glob("./data/Kraken/*.csv")
	all_timeframes = os.environ.get('BACKTEST_TIMEFRAME', '').split(';')
	all_timeframes = { all_timeframe.split('->')[0]: all_timeframe.split('->')[1] for all_timeframe in all_timeframes }

	if has_header:
		headers = None
	else:
		# This is header for Kraken OHLCVT, Change if needed
		headers = [
			'Unix_Timestamp',
			'Open',
			'High',
			'Low',
			'Close',
			'Volume',
			'Trades'
		]

	firebase = LocalFirebaseCandle()

	for file in files:
		df = pd.read_csv(file, names=headers)
		df = df[df['Unix_Timestamp'] >= since]
		df.drop(columns=['Volume', 'Trades'])

		[pair, timeframe] = path.basename(file).removesuffix('.csv').split('_')
		timeframe = all_timeframes[timeframe]

		# Clean token names, E.g. XBT -> BTC
		for (clean_pair, replace_with) in KRAKEN_CLEAN_PAIRS:
			if clean_pair in pair:
				pair = pair.replace(clean_pair, replace_with)

		firebase.change_pair(pair, timeframe)
		print(pair, timeframe)
		firebase.save(df)

if __name__ == '__main__':
	# Move all csv files to "./data/Kraken/*.csv" before running

	a_year_before = datetime.now() - timedelta(days=367) # Be aware that this is not timezoned datetime

	__main(a_year_before, has_header=False) # Use this if the csv has no header
	# main(a_year_before, has_header=True) # Use this if csv has headers
