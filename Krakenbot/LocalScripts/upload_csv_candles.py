import sys
import os
import pandas as pd
import glob
from pathlib import Path
from datetime import datetime, timedelta

# If run directly, other folders' package can't be imported due to path issue
# Set the path to parent path ('./MachD/Krakenbot) instead of current path
if __name__ == '__main__':
	file = Path(__file__).resolve()
	sys.path.append(str(file.parents[1]))

from models.firebase import FirebaseCandle

def __main():
	# Change These Accordingly
	input_dir = '.\\Krakenbot\\LocalScripts\\data\\'
	timeframe_dir = '1' # Set to '*' if you want to upload all timeframe, be aware of latest_to_commit for each timeframe
	a_year_before = int((datetime.now() - timedelta(days=367)).timestamp())
	latest_to_commit = 1723075200 # int(datetime(2024, 8, 8).timestamp())

	# =================================================
	#   Do not need to change from this line onwards
	# =================================================
	all_timeframes = os.environ.get('BACKTEST_TIMEFRAME', '').split(';')
	all_timeframes = { timeframe.split('->')[0]: timeframe.split('->')[1] for timeframe in all_timeframes}

	for dir in glob.glob(input_dir + timeframe_dir):
		timeframe = dir.split('\\')[-1]

		for file in glob.glob(dir + '\\*.csv'):
			pair = file.split('\\')[-1].split('_')[0]
			print(f'Processing {file}...')
			firebase = FirebaseCandle(pair, all_timeframes[timeframe])

			data = pd.read_csv(file)
			data = data[(data['Unix_Timestamp'] >= a_year_before) &
							(data['Unix_Timestamp'] <= latest_to_commit)]
			firebase.save(data, overwrite=False, batch_save=False) # Set batch_save to True if data is small

if __name__ == '__main__':
	__main()
	print('Done')
