from django.db import models


class TimeframeChoice(models.TextChoices):
	min_1 = '1min', '1min'
	min_5 = '5min', '5min'
	min_15 = '15min', '15min'
	min_30 = '30min', '30min'
	hr_1 = '1h', '1h'
	hr_4 = '4h', '4h'
	hr_6 = '6h', '6h'
	d_1 = '1d', '1d'


class KLine(models.Model):
	symbol = models.CharField(max_length=10, verbose_name='Symbol')
	from_token = models.CharField(max_length=10, verbose_name='From token')
	to_token = models.CharField(max_length=10, verbose_name='To token')

	year = models.PositiveIntegerField(verbose_name='Year')
	month = models.PositiveIntegerField(verbose_name='Month')

	open_time = models.PositiveBigIntegerField(verbose_name='Open unix timestamp')
	timeframe = models.TextField(max_length=20, choices=TimeframeChoice, verbose_name='Timeframe')

	open = models.FloatField(null=True, verbose_name='Open price')
	high = models.FloatField(null=True, verbose_name='High price')
	low = models.FloatField(null=True, verbose_name='Low price')
	close = models.FloatField(null=True, verbose_name='Close price')

	volume = models.FloatField(null=True, verbose_name='Volume')

	class Meta:
		indexes = [
			models.Index(fields=['year']),
			models.Index(fields=['month']),
			models.Index(fields=['symbol']),
			models.Index(fields=['timeframe']),
		]
