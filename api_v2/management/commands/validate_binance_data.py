from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

BINANCE_DATA_DIR: Path = settings.BINANCE_DATA_DIR


class Command(BaseCommand):
	batch_size = 1e6
	help = 'Validate and Remove invalid Binance OHLC data'

	def handle(self, *args, **kwargs):
		removed_files = []
		for symbol_folder in sorted(BINANCE_DATA_DIR.glob('*')):
			self.stdout.write(self.style.SUCCESS(f'===== Checking {symbol_folder.stem} ====='))
			for interval_folder in sorted(symbol_folder.glob('*')):
				for file in sorted(interval_folder.glob('*')):
					try:
						self.stdout.write(self.style.SUCCESS(f'Checking "{interval_folder.stem}/{file.stem}"...'))
						pd.read_csv(file, compression='zip', header=None)
					except UnicodeDecodeError:
						removed_files.append(f'{interval_folder.stem}/{file.stem}')
						file.unlink()
						self.stdout.write(self.style.ERROR(f'Removing corrupted data {file}!'))

		if len(removed_files) > 0:
			self.stdout.write(self.style.SUCCESS('Removed files:\n' + '\n'.join(removed_files)))
		self.stdout.write(self.style.SUCCESS('Checked all data!'))
