import uuid
from django.utils import timezone
from django.db import models

class BackTestModel(models.Model):
	token_id = models.CharField(max_length=10)
	timeframe = models.CharField(max_length=10)
	strategy = models.TextField(default='')
	profit = models.FloatField(default=0)
	profit_percent = models.FloatField(default=0)
	summary = models.TextField(default='')
	strategy_description = models.TextField(default='')
	updated_on = models.DateTimeField(default=timezone.now)
