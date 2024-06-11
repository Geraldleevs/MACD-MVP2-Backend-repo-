from Krakenbot.MVP_Backtest import main as backtest

class Recommendation:
	def __init__(self, token_id = '', timeframe = ''):
		self.token_id = token_id
		self.timeframe = timeframe

	def recommend(self):
		result = backtest(self.token_id, self.timeframe).reset_index().to_numpy()
		result = [{'token': value[0], 'strategy': value[1], 'profit': value[2], 'profit_percent': value[3]} for value in result]
		return result
