from django.conf import settings
from django.core.management.base import BaseCommand

from binance_public_data.download_kline import download_binance


class Command(BaseCommand):
	help = 'Download all Binance OHLC data'

	def add_arguments(self, parser):
		parser.add_argument('--skip_all', action='store_true')

	def handle(self, *args, **kwargs):
		years = settings.KLINE_YEARS
		tokens = settings.KLINE_TOKENS
		intervals = settings.KLINE_INTERVALS
		skip_all = kwargs.get('skip_all', False)

		if tokens is None:
			raise ValueError('KLINE_TOKENS is unspecified')

		if intervals is None:
			raise ValueError('KLINE_INERVALS is unspecified')

		if len(years) == 0 or (len(years) == 1 and years[0] == ''):
			years = None

		msg = '\n'.join(
			[
				'=====================================',
				'',
				'  Download candle data from Binance  ',
				'',
				'=====================================',
				'',
				'(Type "YES" to continue)',
				'',
			]
		)

		self.stdout.write(self.style.SUCCESS(msg))
		if input() != 'YES':
			self.stdout.write(self.style.ERROR('Process aborted!'))
			return

		download_binance(settings.BASE_DIR / 'binance_public_data', tokens, years, intervals, skip_all)
		self.stdout.write(self.style.SUCCESS('\n\nProcess completed!\n'))
