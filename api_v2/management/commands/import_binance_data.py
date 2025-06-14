import calendar
from datetime import datetime, timedelta
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from api_v2.models import KLine

BINANCE_DATA_DIR: Path = settings.BINANCE_DATA_DIR


def get_duration(start_time: datetime):
	now = datetime.now()
	diff = now - start_time
	return int(diff.total_seconds())


class Command(BaseCommand):
	batch_size = 1e6
	help = 'Import all Binance OHLC data'

	def add_arguments(self, parser):
		parser.add_argument('--drop_all', action='store_true')

	def handle(self, *args, **kwargs):
		tokens = settings.KLINE_TOKENS
		import_intervals = settings.KLINE_INTERVALS

		if tokens is None:
			raise ValueError('KLINE_TOKENS is unspecified')

		if import_intervals is None:
			raise ValueError('KLINE_INERVALS is unspecified')

		import_symbols = [f'{a}{b}' for a, b in permutations(tokens, 2)]

		drop_all = kwargs['drop_all']
		if drop_all:
			msg = '\n'.join(
				[
					'=====================================',
					'',
					'  Removing all existing candle data  ',
					'',
					'=====================================',
					'',
					'Are you sure you want to drop all existing candle data?',
					'(Type "YES" to continue)',
					'',
				]
			)
		else:
			msg = '\n'.join(
				[
					'======================================',
					'',
					'  Importing candle data from Binance  ',
					'',
					'======================================',
					'',
					'(Type "YES" to continue)',
					'',
				]
			)

		self.stdout.write(self.style.SUCCESS(msg))
		if input() != 'YES':
			self.stdout.write(self.style.ERROR('Process aborted!'))
			return

		if drop_all:
			self.stdout.write(self.style.SUCCESS('Removing existing data...'))
			cursor = connection.cursor()
			cursor.execute('DELETE FROM api_v2_kline;')
			cursor.close()

		self.stdout.write(self.style.SUCCESS('Pairing tokens...'))
		symbol_folders = list(sorted(BINANCE_DATA_DIR.glob('*')))
		symbols = [folder.stem for folder in symbol_folders]
		symbol_maps = requests.get(
			'https://api.binance.com/api/v3/exchangeInfo?symbols=["' + '","'.join(symbols) + '"]'
		).json()['symbols']
		symbol_maps = {
			symbol['symbol']: {
				'from': symbol['baseAsset'],
				'to': symbol['quoteAsset'],
			}
			for symbol in symbol_maps
		}

		start_time = datetime.now()
		data = []
		for symbol_folder in symbol_folders:
			symbol = symbol_folder.stem
			if symbol not in import_symbols:
				self.stdout.write(
					self.style.SUCCESS(f'Skipping {symbol} (Not included in ENV)... [{get_duration(start_time):d}s]')
				)
				continue

			self.stdout.write(self.style.SUCCESS(f'Importing {symbol}... [{get_duration(start_time):d}s]'))

			from_token = symbol_maps[symbol]['from']
			to_token = symbol_maps[symbol]['to']
			for interval_folder in sorted(symbol_folder.glob('*')):
				interval = interval_folder.stem
				if interval not in import_intervals:
					continue

				self.stdout.write(
					self.style.SUCCESS(f'Importing {symbol} [{interval}]... [{get_duration(start_time):d}s]')
				)

				interval_int = settings.INTERVAL_MAP[interval] * 60 * 1000
				rows_per_day = round(60 * 24 / settings.INTERVAL_MAP[interval])
				for file in sorted(interval_folder.glob('*')):
					self.stdout.write(
						self.style.SUCCESS(
							f'Importing {symbol} [{interval}] - {file.stem}... [{get_duration(start_time):d}s]'
						)
					)

					file_parts = file.stem.split('-')
					year = int(file_parts[-2])
					month = int(file_parts[-1])

					existings = KLine.objects.filter(
						timeframe=interval,
						from_token=from_token,
						to_token=to_token,
						year=year,
						month=month,
					)
					if existings.count() > 0:
						self.stdout.write(
							self.style.SUCCESS(
								f'Skipping {file.stem} [Imported in database]... [{get_duration(start_time):d}s]'
							)
						)
						continue

					df = pd.read_csv(file, compression='zip', header=None)
					df = df.iloc[:, 0:6]
					df.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume']

					if df.iloc[0, 0] > 100000000000000:
						df['open_time'] = df['open_time'] / 1000
					elif df.iloc[0, 0] < 100000000000:
						df['open_time'] = df['open_time'] * 1000

					df_start_time = datetime.fromtimestamp(df.iloc[0, 0] / 1000)
					num_days = calendar.monthrange(df_start_time.year, df_start_time.month)[1]
					df_start_time = datetime(year=df_start_time.year, month=df_start_time.month, day=1)
					df_end_time = df_start_time + timedelta(days=num_days)
					start_timestamp = int(df_start_time.timestamp() * 1000)
					end_timestamp = int(df_end_time.timestamp() * 1000)

					all_time = list(range(start_timestamp, end_timestamp, interval_int))
					full_df = pd.DataFrame({'open_time': all_time})
					full_df = full_df.merge(df, how='left', on='open_time')
					full_df = full_df.replace(np.nan, None)

					assert len(full_df) == rows_per_day * num_days

					file_data = [
						KLine(
							**row.to_dict(),
							timeframe=interval,
							symbol=symbol,
							from_token=from_token,
							to_token=to_token,
							year=year,
							month=month,
						)
						for _, row in full_df.iterrows()
					]
					data.extend(file_data)

			if len(data) > self.batch_size:
				self.stdout.write(
					self.style.SUCCESS(f'Writing to {len(data)} rows database... [{get_duration(start_time):d}s]')
				)
				KLine.objects.bulk_create(data)
				data = []

		if len(data) > 0:
			self.stdout.write(
				self.style.SUCCESS(f'Writing to {len(data)} rows database... [{get_duration(start_time):d}s]')
			)
			KLine.objects.bulk_create(data)

		self.stdout.write(self.style.SUCCESS(f'Import completed! [{get_duration(start_time):d}s]'))
