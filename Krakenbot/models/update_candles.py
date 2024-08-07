from Krakenbot.utils import authenticate_scheduler_oicd
from rest_framework.request import Request
from Krakenbot.update_candles import main as update_candles
import asyncio

class UpdateCandles:
	KRAKEN_OHLC_API = 'https://api.kraken.com/0/public/OHLC'

	def update(self, request: Request):
		authenticate_scheduler_oicd(request)
		asyncio.run(update_candles())
