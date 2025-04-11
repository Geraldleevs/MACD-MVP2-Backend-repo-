import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

from binance_public_data.enums import BASE_URL


def get_destination_dir(file_url, folder=None):
	store_directory = os.environ.get('STORE_DIRECTORY')
	if folder:
		store_directory = folder
	if not store_directory:
		store_directory = os.path.dirname(os.path.realpath(__file__))
	return os.path.join(store_directory, file_url)


def get_download_url(file_url):
	return '{}{}'.format(BASE_URL, file_url)


def get_all_symbols(type):
	if type == 'um':
		response = urllib.request.urlopen('https://fapi.binance.com/fapi/v1/exchangeInfo').read()
	elif type == 'cm':
		response = urllib.request.urlopen('https://dapi.binance.com/dapi/v1/exchangeInfo').read()
	else:
		response = urllib.request.urlopen('https://api.binance.com/api/v3/exchangeInfo').read()
	return list(map(lambda symbol: symbol['symbol'], json.loads(response)['symbols']))


def download_file(base_path, file_name, date_range=None, folder=None):
	download_path = '{}{}'.format(base_path, file_name)
	if folder:
		base_path = os.path.join(folder, base_path)
	if date_range:
		date_range = date_range.replace(' ', '_')
		base_path = os.path.join(base_path, date_range)
	save_path = get_destination_dir(os.path.join(base_path, file_name), folder)

	if os.path.exists(save_path):
		print('\nfile already exists! {}'.format(save_path))
		return

	# make the directory
	if not os.path.exists(base_path):
		Path(get_destination_dir(base_path)).mkdir(parents=True, exist_ok=True)

	try:
		download_url = get_download_url(download_path)
		dl_file = urllib.request.urlopen(download_url)
		length = dl_file.getheader('content-length')
		if length:
			length = int(length)
			blocksize = max(4096, length // 100)

		with open(save_path, 'wb') as out_file:
			dl_progress = 0
			print('\nFile Download: {}'.format(save_path))
			while True:
				buf = dl_file.read(blocksize)
				if not buf:
					break
				dl_progress += len(buf)
				out_file.write(buf)
				done = int(50 * dl_progress / length)
				sys.stdout.write('\r[%s%s]' % ('#' * done, '.' * (50 - done)))
				sys.stdout.flush()

	except urllib.error.HTTPError:
		print('\nFile not found: {}'.format(download_url))
		pass


def convert_to_date_object(d):
	year, month, day = [int(x) for x in d.split('-')]
	date_obj = date(year, month, day)
	return date_obj


def get_path(trading_type, market_data_type, time_period, symbol, interval=None):
	trading_type_path = 'data/spot'
	if trading_type != 'spot':
		trading_type_path = f'data/futures/{trading_type}'
	if interval is not None:
		path = f'{trading_type_path}/{time_period}/{market_data_type}/{symbol.upper()}/{interval}/'
	else:
		path = f'{trading_type_path}/{time_period}/{market_data_type}/{symbol.upper()}/'
	return path
