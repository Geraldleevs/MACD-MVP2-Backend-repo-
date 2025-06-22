import calendar
import math
from datetime import datetime, timedelta
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from api_v2.firebase import FirebaseCandle, Platform

BINANCE_DATA_DIR: Path = settings.BINANCE_DATA_DIR


def get_duration(start_time: datetime):
	now = datetime.now()
	diff = now - start_time
	return int(diff.total_seconds())


class Command(BaseCommand):
	help = 'Import all Binance OHLC data onto Firebase'
	start_time: datetime
	import_symbols: list[str] = []
	import_intervals: list[str] = []
	symbol_maps: dict[dict[str, str]] = {}
	limit: int
	imported_days: int
	limit_hit: bool

	def import_ohlc(self, file: Path, last: int, interval_int: int, rows_per_day: int):
		df = pd.read_csv(file, compression='zip', header=None)
		df = df.iloc[:, 0:6]
		df.columns = ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume']

		if df.iloc[0, 0] > 100000000000000:
			df['Open Time'] = df['Open Time'] / 1000
		elif df.iloc[0, 0] < 100000000000:
			df['Open Time'] = df['Open Time'] * 1000

		df_start_time = datetime.fromtimestamp(df.iloc[0, 0] / 1000)
		num_days = calendar.monthrange(df_start_time.year, df_start_time.month)[1]
		df_start_time = datetime(year=df_start_time.year, month=df_start_time.month, day=1)
		df_end_time = df_start_time + timedelta(days=num_days)
		start_timestamp = int(df_start_time.timestamp() * 1000)
		end_timestamp = int(df_end_time.timestamp() * 1000)

		all_time = list(range(start_timestamp, end_timestamp, interval_int))
		full_df = pd.DataFrame({'Open Time': all_time})
		full_df = full_df.merge(df, how='left', on='Open Time')
		full_df = full_df.replace(np.nan, None)

		assert len(full_df) == rows_per_day * num_days
		return full_df

	def import_interval_folder(self, interval_folder: Path, symbol: str, from_token: str, to_token: str):
		interval = interval_folder.stem
		if interval not in self.import_intervals:
			return

		self.stdout.write(f'  Importing {symbol} [{interval}]... [{get_duration(self.start_time):d}s]')

		firebase = FirebaseCandle(symbol, interval, Platform.BINANCE)
		firebase.save(symbol, from_token, to_token)

		last = firebase.fetch_last()
		if len(last) < 1:
			last = None
		else:
			last = last[-1]['Open Time']

		interval_int = settings.INTERVAL_MAP[interval] * 60 * 1000
		rows_per_day = round(60 * 24 / settings.INTERVAL_MAP[interval])
		df = []
		for file in sorted(interval_folder.glob('*')):
			df.append(self.import_ohlc(file, last, interval_int, rows_per_day))

		if all([d is None for d in df]):
			self.stdout.write('    No data found!')
			return

		df = pd.concat(df).reset_index(drop=True)
		first_valid = df['Open'].first_valid_index()
		last_valid = df['Open'].last_valid_index()
		df = df.iloc[first_valid : last_valid + 1, :]

		if len(df) == 0:
			self.stdout.write('    No data found!')
			return

		if last is not None:
			df = df[df['Open Time'] > last]

		if len(df) == 0:
			self.stdout.write('    All data is imported! Skipping...')
			return

		max_upload_limit = FirebaseCandle.MAX_UPLOAD_LIMIT - (FirebaseCandle.MAX_UPLOAD_LIMIT % rows_per_day)

		self.stdout.write(f'    {len(df)} candle found ({len(df) // rows_per_day} days)!')
		for _, group in df.groupby(np.arange(len(df)) // max_upload_limit):
			firebase.save_ohlc(group)

			num_days = len(group) // rows_per_day
			self.imported_days += num_days
			self.stdout.write(f'    - Imported {num_days} days... [{get_duration(self.start_time):d}s]')

			if self.imported_days >= self.limit:
				self.limit_hit = True
				return

	def import_folders(self, symbol_folder: Path):
		symbol = symbol_folder.stem
		if symbol not in self.import_symbols:
			self.stdout.write(f'Skipping {symbol} (Not included in ENV)... [{get_duration(self.start_time):d}s]')
			return

		self.stdout.write(self.style.SUCCESS(f'Importing {symbol}... [{get_duration(self.start_time):d}s]'))

		from_token = self.symbol_maps[symbol]['from']
		to_token = self.symbol_maps[symbol]['to']
		for interval_folder in sorted(symbol_folder.glob('*')):
			self.import_interval_folder(interval_folder, symbol, from_token, to_token)
			if self.limit_hit:
				return

	def add_arguments(self, parser):
		parser.add_argument('--limit', type=int)

	def handle(self, *args, **kwargs):
		self.limit = kwargs.get('limit')
		self.imported_days = 0
		self.limit_hit = False

		if self.limit is not None:
			if self.limit < 0:
				self.stdout.write(self.style.ERROR(f'Invalid limit {self.limit}!'))
			self.stdout.write(self.style.WARNING(f'Current session is limited to {self.limit} records!\n'))
		else:
			self.limit = math.inf

		tokens = settings.KLINE_TOKENS
		import_intervals = [settings.KLINE_INTERVALS[0]]  # Only import the smallest unit

		if tokens is None:
			raise ValueError('KLINE_TOKENS is unspecified')

		if import_intervals is None:
			raise ValueError('KLINE_INERVALS is unspecified')

		msg = '\n'.join(
			[
				'====================================================',
				'',
				'  Importing candle data from Binance onto Firebase  ',
				'',
				'====================================================',
				'',
				'(Type "YES" to continue)',
				'',
			]
		)

		self.stdout.write(self.style.SUCCESS(msg))
		if input() != 'YES':
			self.stdout.write(self.style.ERROR('Process aborted!'))
			return

		self.stdout.write(self.style.SUCCESS('Pairing tokens...'))
		symbol_folders = sorted(BINANCE_DATA_DIR.glob('*'))
		symbols = [folder.stem for folder in symbol_folders]
		symbols = '["' + '","'.join(symbols) + '"]'
		symbol_maps = requests.get(f'https://api.binance.com/api/v3/exchangeInfo?symbols={symbols}').json()['symbols']
		symbol_maps = {
			symbol['symbol']: {
				'from': symbol['baseAsset'],
				'to': symbol['quoteAsset'],
			}
			for symbol in symbol_maps
		}

		self.start_time = datetime.now()
		self.import_intervals = import_intervals
		self.import_symbols = [f'{a}{b}' for a, b in permutations(tokens, 2)]
		self.symbol_maps = symbol_maps

		for symbol_folder in symbol_folders:
			self.import_folders(symbol_folder)
			if self.limit_hit:
				self.stdout.write(self.style.SUCCESS('Import limit hit!'))
				break

		self.stdout.write(self.style.SUCCESS(f'Total days uploaded: {self.imported_days}'))
		self.stdout.write(self.style.SUCCESS(f'Import completed! [{get_duration(self.start_time):d}s]'))
