import json
import sys


def log_warning(message):
	"""Google Cloud Log Warning"""
	log(message, 'WARNING')


def log_error(message):
	"""Google Cloud Log Error"""
	log(message, 'ERROR')


def log(message, severity='INFO'):
	"""Google Cloud Log"""
	entry = {'severity': severity, 'component': 'arbitrary-property', 'message': message}

	print(json.dumps(entry))
	sys.stdout.flush()


KRAKEN_CLEAN_PAIRS = [
	('XETC', 'ETC'),
	('XETH', 'ETH'),
	('XLTC', 'LTC'),
	('XMLN', 'MLN'),
	('XREP', 'REP'),
	('XXBT', 'BTC'),
	('XBT', 'BTC'),
	('XXDG', 'XDG'),
	('XDG', 'DOGE'),
	('XXLM', 'XLM'),
	('XXMR', 'XMR'),
	('XXRP', 'XRP'),
	('XZEC', 'ZEC'),
	('ZAUD', 'AUD'),
	('ZEUR', 'EUR'),
	('ZGBP', 'GBP'),
	('ZUSD', 'USD'),
	('ZCAD', 'CAD'),
	('ZJPY', 'JPY'),
]


def clean_kraken_pair(kraken_result) -> dict[str, any]:
	"""
	Parse Kraken Pairs into standard token names, (e.g. `XXBT -> BTC` ; `ZGBP -> GBP`)

	Returns:
		kraken_result:
		`kraken_result['result']`, with cleaned token pairs' name
		`{ 'BTCGBP': Any, 'ETHGBP': Any, 'BTCDOGE': Any, ... }`
	"""
	results = {}

	for pair, result in kraken_result['result'].items():
		for clean_pair, replace_with in KRAKEN_CLEAN_PAIRS:
			if clean_pair in pair:
				pair = pair.replace(clean_pair, replace_with)

		results[pair] = result

	return results
