from django.conf import settings
from django.core.management.base import BaseCommand

from binance_public_data.download_kline import download_binance


class Command(BaseCommand):
	help = 'Download all Binance OHLC data'

	def handle(self, *args, **kwargs):
		years = settings.KLINE_YEARS
		pairs = settings.KLINE_SYMBOLS
		intervals = settings.KLINE_INTERVALS
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

		download_binance(pairs, years, intervals)
		self.stdout.write(self.style.SUCCESS('\n\nProcess completed!\n'))
