from datetime import datetime
from itertools import permutations, product
from pathlib import Path

import pandas as pd

from binance_public_data.enums import MONTHS, YEARS
from binance_public_data.utility import download_file, get_all_symbols, get_path


def download(
	interval: str,
	year: str,
	month: str,
	symbol: str,
	download_path: Path,
	not_exist_data: list[str],
	near_not_exist_data: list[str],
	skip_all: bool,
	had_data: bool,
):
	trading_type = 'spot'
	path = get_path(trading_type, 'klines', 'monthly', symbol, interval)
	file_name = f'{symbol.upper()}-{interval}-{year}-{month:02d}.zip'

	if download_path is not None and (download_path / path / file_name).exists():
		return True

	if file_name in not_exist_data:
		return False

	if skip_all and file_name in near_not_exist_data:
		return False

	result = download_file(path, file_name)

	if result is False:
		if file_name not in near_not_exist_data:
			with open(download_path / 'near_binance_data_not_exists.txt', 'a+') as file:
				file.write(file_name + '\n')

		if had_data is False:
			with open(download_path / 'binance_data_not_exists.txt', 'a+') as file:
				file.write(file_name + '\n')
		return False

	return True


def filter_time(x, now, binance_start):
	time = datetime(year=int(x[0]), month=int(x[1]), day=1)
	return time < now and time >= binance_start


def download_monthly_klines(
	symbols: list[str],
	intervals: list[str],
	years: list[str],
	months: list[str],
	download_path: Path,
	not_exist_data: list[str],
	near_not_exist_data: list[str],
	skip_all: bool,
):
	num_symbols = len(symbols)
	print(f'Found {num_symbols} symbols')

	binance_start = datetime(year=2017, month=7, day=1)
	now = datetime.now()
	now = datetime(year=now.year, month=now.month, day=1)
	for index, symbol in enumerate(symbols):
		print(f'[{index + 1}/{num_symbols}] - start download monthly {symbol} klines ')
		for interval in intervals:
			had_data = False
			combinations = product(years, months)
			combinations = filter(lambda x: filter_time(x, now, binance_start), combinations)

			for year, month in combinations:
				has_data = download(
					interval,
					year,
					month,
					symbol,
					download_path,
					not_exist_data,
					near_not_exist_data,
					skip_all,
					had_data,
				)
				had_data = had_data or has_data


def download_binance(
	download_path: Path,
	tokens=['BTC', 'GBP'],
	years: list[str] = None,
	intervals=['1h'],
	skip_all=False,
):
	trading_type = 'spot'
	print('Fetching all symbols from exchange...')

	symbols = [f'{a}{b}' for a, b in permutations(tokens, 2)]
	all_symbols = get_all_symbols(trading_type)
	filtered_symbols = list(filter(lambda x: x in symbols, all_symbols))

	if years is None:
		years = YEARS

	try:
		not_exist_data = pd.read_csv(download_path / 'binance_data_not_exists.txt', header=None)
		not_exist_data = not_exist_data[0].to_list()
	except (FileNotFoundError, pd.errors.EmptyDataError):
		not_exist_data = []

	try:
		near_not_exist_data = pd.read_csv(download_path / 'near_binance_data_not_exists.txt', header=None)
		near_not_exist_data = near_not_exist_data[0].to_list()
	except (FileNotFoundError, pd.errors.EmptyDataError):
		near_not_exist_data = []

	print(f'Filtered symbols: {", ".join(filtered_symbols)}')
	download_monthly_klines(
		filtered_symbols,
		intervals,
		years,
		MONTHS,
		download_path,
		not_exist_data,
		near_not_exist_data,
		skip_all,
	)
