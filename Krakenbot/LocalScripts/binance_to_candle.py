import pandas as pd
import glob

# Edit These Data As Needed (Do not commit unless needed)
# Be aware that binance is using ms form of timestamp instead of sec
first_timestamp = 1691452800000

latest_timestamp = {
	'1m': 1723075140000,
	'1h': 1723071600000,
	'4h': 1723060800000,
	'1d': 1722988800000
}

# Change this only if you have a different interval, default 1 min, 1 hour, 4 hours and 1 day
expected_length = {
	'1m': (latest_timestamp['1m'] - first_timestamp) / (60 * 1000), # divide by the length of the interval in milliseconds E.g. 1 min = 60,000 ms
	'1h': (latest_timestamp['1h'] - first_timestamp) / (60 * 60 * 1000),
	'4h': (latest_timestamp['4h'] - first_timestamp) / (4 * 60 * 60 * 1000),
	'1d': (latest_timestamp['1d'] - first_timestamp) / (24 * 60 * 60 * 1000)
}

btc_to_gbp_csv = 'Bitfinex_BTCGBP_1h.csv'
btc_to_gbp_date_column = 'date'
btc_to_gbp_timestamp_column = '' # If do not have timestamp, or timestamp is corrupted, set this to ''
btc_to_gbp_price_column = 'close'

btc_to_other_csv = './Binance Concatenated Data/1m/BTCUSDT.csv' # One full concatenated OHLC csv from BTC to any other token
btc_to_other_timestamp_column = 'open_time'
btc_to_other_price_column = 'Close'

other_token_name = 'USDT'
new_fiat_name = 'GBP'

# Organise your csv files and folders as
# '.\\Dir\\[timeframe]\\[token_name]\\[token_name][other_token]-.....csv
# E.g: .\\Binance Data\\1d\\BTC\\BTCUSDT-1d-2023-08.csv (Should be exactly same csv filename downloaded from binance)
input_dir = '.\\Binance Data\\'
output_dir = ".\\Parsed-GBP\\"
not_parsing_tokens = ['1INCH', 'ARB'] # Tokens that do not need to convert to GBP

# The CSV file headers, this is set for Binance already
headers = ["open_time", "Open", "High", "Low", "Close", "Volume", "Close_time", "Quote_volume", "Count", "Taker_buy_volume", "Taker_buy_quote_volume", "Ignore"]
select_columns = ["open_time", "Open", "High", "Low", "Close"] # Only get OHLC, can get other columns if needed
new_column_names = ['Unix_Timestamp', 'Open', 'High', 'Low', 'Close'] # Change this only if you added other columns

# ============================================================
#    Don't need to change any code from this line onwards
# ============================================================
time_column_name = 'Unix_Timestamp' # For sorting
open_column_name = 'Open'
high_column_name = 'High'
low_column_name = 'Low'
close_column_name = 'Close'

def __get_other_to_gbp_rate():
	btc_gbp_1h = pd.read_csv(btc_to_gbp_csv)
	global btc_to_gbp_timestamp_column
	if btc_to_gbp_timestamp_column == '':
		btc_to_gbp_timestamp_column = 'time'
		btc_gbp_1h[btc_to_gbp_date_column] = pd.to_datetime(btc_gbp_1h[btc_to_gbp_date_column])
		btc_gbp_1h[btc_to_gbp_timestamp_column] = btc_gbp_1h[btc_to_gbp_date_column].apply(lambda x: int(x.timestamp()) * 1000 )
	btc_gbp_1h = btc_gbp_1h[[btc_to_gbp_timestamp_column, btc_to_gbp_price_column]]
	btc_gbp_1h.columns = [time_column_name, 'btc_gbp_close']
	btc_gbp_1h = btc_gbp_1h[btc_gbp_1h[time_column_name] >= first_timestamp]

	btc_usdt_1h = pd.read_csv(btc_to_other_csv)
	btc_usdt_1h = btc_usdt_1h[[btc_to_other_timestamp_column, btc_to_other_price_column]]
	btc_usdt_1h.columns = [time_column_name, 'btc_other_close']
	btc_usdt_1h = btc_usdt_1h[btc_usdt_1h[time_column_name] >= first_timestamp]

	btc_gbp_usdt_1h = btc_usdt_1h.merge(btc_gbp_1h, on=time_column_name, how='left')
	btc_gbp_usdt_1h['other_gbp_close'] = btc_gbp_usdt_1h['btc_gbp_close'] / btc_gbp_usdt_1h['btc_other_close']
	usdt_gbp = btc_gbp_usdt_1h[[time_column_name, 'other_gbp_close']]
	usdt_gbp = usdt_gbp.ffill()

	return usdt_gbp


def __combine_all_csv_in_folder(dir: str):
	print(f'Processing {dir}')
	data = pd.DataFrame(columns=headers)
	for file in glob.glob(dir + '\\*'):
		pair_name = file.split('\\')[-1].removesuffix('.csv').split('-')[0]
		token_name = pair_name.removesuffix(other_token_name)
		df = pd.read_csv(file, names=headers)
		data = pd.concat([data, df])

	return (data, pair_name, token_name)


def __check_data_accuracy(data: pd.DataFrame, pair_name: str, timeframe: str):
	if data.iloc[0, 0] > first_timestamp:
		print(f'{pair_name}_{timeframe}: First data is later than expected')

	if data.iloc[-1, 0] < latest_timestamp[timeframe]:
		print(f'{pair_name}_{timeframe}: Last data is earlier than expected')

	if len(data) < expected_length[timeframe]:
		print(f'{pair_name}_{timeframe}: Has less row than expected, {len(data)} given, {expected_length[timeframe]} expected')


def main():
	other_to_gbp = __get_other_to_gbp_rate()

	for dir in glob.glob(input_dir + '*'):
		timeframe = dir.split('\\')[-1]

		for subdir in glob.glob(dir + '\\*'):
			(data, pair_name, token_name) = __combine_all_csv_in_folder(subdir)
			data = data[select_columns]
			data.columns = new_column_names
			data = data[data[time_column_name] >= first_timestamp]
			output_file_name = pair_name + f'_{timeframe}.csv'

			if token_name not in not_parsing_tokens:
				data = data.merge(other_to_gbp, on=time_column_name)
				data[open_column_name] = data[open_column_name] * data['other_gbp_close']
				data[high_column_name] = data[high_column_name] * data['other_gbp_close']
				data[low_column_name] = data[low_column_name] * data['other_gbp_close']
				data[close_column_name] = data[close_column_name] * data['other_gbp_close']
				data = data[new_column_names]
				data = data.sort_values(by=time_column_name)
				output_file_name = token_name + new_fiat_name + f'_{timeframe}.csv'

			__check_data_accuracy(data, pair_name, timeframe)

			# Convert ms timestamp to sec timestamp
			data[time_column_name] = data[time_column_name] // 1000

			data.to_csv(output_dir + timeframe + '\\' + output_file_name, index=False)

	print('Done')

if __name__ == "__main__":
	main()
