from Krakenbot.MVP_Backtest import main as backtest
from Krakenbot_app.models import BackTestModel
from django.utils import timezone

class BackTest:
	def backtest(self):
		results = backtest().reset_index().to_numpy()
		now = timezone.now()
		results = [{'token_id': value[0].split(' | ')[0],
							'timeframe': value[0].split(' | ')[1],
							'strategy': value[1],
							'profit': value[2],
							'profit_percent': value[3],
							'summary': 'Summary',
							'strategy_description': 'Strategy Description',
							'updated_on': now
							} for value in results]

		for result in results:
			BackTestModel.objects.update_or_create(token_id=result['token_id'], timeframe=result['timeframe'], defaults={**result}, create_defaults={**result})
