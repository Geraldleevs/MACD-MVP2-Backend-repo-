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
