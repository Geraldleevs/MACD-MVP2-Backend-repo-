from typing import Literal
from Krakenbot import settings

class FirebaseAnalysis:
	def __init__(self):
		self.__analysis = settings.firebase.collection(u'analysis')

	def fetch_all(self):
		docs = self.__analysis.stream()
		return [doc.to_dict() for doc in docs]

	def fetch_strategy_description(self):
		doc = self.__analysis.document('Strategy').get()
		return doc.to_dict()['text']

	def get_risk(self, token_id, timeframe: Literal['very_short', 'short', 'medium','long'], default = 'Risk'):
		doc = self.__analysis.document(token_id).get()
		if doc.exists:
			return doc.to_dict()[f'{timeframe}_term_risk']
		else:
			return default

	def get_description(self, token_id, timeframe: Literal['very_short', 'short', 'medium','long'], default = 'Summary'):
		doc = self.__analysis.document(token_id).get()
		if doc.exists:
			return doc.to_dict()[f'{timeframe}_term_analysis']
		else:
			return default
