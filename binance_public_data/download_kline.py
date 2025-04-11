from itertools import product
from multiprocessing import Pool
from pathlib import Path

from binance_public_data.enums import MONTHS
from binance_public_data.utility import download_file, get_all_symbols, get_path


def multidownload(inputs: list[str]):
	trading_type = 'spot'
	interval = inputs[0]
	year = inputs[1]
	month = inputs[2]
	symbol = inputs[3]
	path = get_path(trading_type, 'klines', 'monthly', symbol, interval)
	file_name = f'{symbol.upper()}-{interval}-{year}-{month:02d}.zip'
	full_file = f'./data/spot/monthly/klines/{symbol}/{interval}/{file_name}'
	if Path(full_file).exists():
		print(f'{full_file} already exists, skipping...')
	download_file(path, file_name)


def download_monthly_klines(
	symbols: list[str],
	intervals: list[str],
	years: list[str],
	months: list[str],
):
	num_symbols = len(symbols)
	print(f'Found {num_symbols} symbols')

	for index, symbol in enumerate(symbols):
		print(f'[{index + 1}/{num_symbols}] - start download monthly {symbol} klines ')
		combinations = list(product(intervals, years, months, [symbol]))

		with Pool(2) as pool:
			pool.map(multidownload, combinations)


def download_binance(symbols: list[str] = ['BTCGBP'], years: list[str] = ['2023'], intervals: list[str] = ['1h']):
	trading_type = 'spot'
	print('Fetching all symbols from exchange...')
	all_symbols = get_all_symbols(trading_type)

	symbols = list(filter(lambda x: x in all_symbols, symbols))
	print(f'Filtered symbols: {", ".join(symbols)}')
	download_monthly_klines(symbols, intervals, years, MONTHS)
