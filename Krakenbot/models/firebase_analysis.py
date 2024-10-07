from typing import Literal, TypedDict

try:
	from Krakenbot import settings
except ModuleNotFoundError:
	from local_settings import settings

class AnalysisField(TypedDict):
	goal_length: str
	risk: str
	summary: str
	analysis: str
	technical_analysis: str

class FirebaseAnalysis:
	def __init__(self):
		self.__analysis = settings.firebase.collection(u'analysis')

	def save(self, token_id: str, analysis: list[AnalysisField]):
		doc = self.__analysis.document(token_id)

		analysis = {
			data['goal_length'].lower(): {
				'risk': data['risk'].lower(),
				'summary': data['summary'],
				'analysis': data['analysis'],
				'technical_analysis': data['technical_analysis']
			} for data in analysis}

		data = { 'token_id': token_id, 'analysis': analysis }

		if doc.get().exists:
			doc.update(data)
		else:
			doc.set(data)

	def fetch_all(self):
		docs = self.__analysis.stream()
		return [doc.to_dict() for doc in docs]

	def fetch_strategy_description(self):
		doc = self.__analysis.document('Strategy').get()
		return doc.to_dict()['text']

	def get_risk(self, token_id, timeframe: Literal['very_short', 'short', 'medium','long'], default = 'Risk'):
		doc = self.__analysis.document(token_id).get()
		if doc.exists:
			try:
				return doc.to_dict()['analysis'][timeframe]['risk']
			except KeyError:
				pass
		return default

	def get_analysis(self, token_id, timeframe: Literal['very_short', 'short', 'medium','long'], default = 'Summary'):
		doc = self.__analysis.document(token_id).get()
		if doc.exists:
			try:
				analysis = doc.to_dict()['analysis'][timeframe]
				return {
					'analysis': analysis['analysis'],
					'summary': analysis['summary'],
					'technical_analysis': analysis['technical_analysis']
				}
			except KeyError:
				pass
		return {
			'analysis': default,
			'summary': default,
			'technical_analysis': default
		}
