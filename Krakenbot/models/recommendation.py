from Krakenbot.serializers.backtest import BackTestSerializer
from Krakenbot_app.models import BackTestModel

class Recommendation:
	def __init__(self, token_id = '', timeframe = ''):
		self.token_id = token_id
		self.timeframe = timeframe

	def recommend(self):
		filters = {}
		if self.token_id:
			filters['token_id'] = self.token_id

		if self.timeframe:
			filters['timeframe'] = self.timeframe

		results = BackTestModel.objects.filter(**filters).order_by('token_id', 'timeframe')
		return BackTestSerializer(results, many=True).data
