from rest_framework import serializers

class BackTestSerializer(serializers.Serializer):
	token_id = serializers.CharField()
	timeframe = serializers.CharField()
	strategy = serializers.CharField(default='')
	profit = serializers.FloatField(default=0)
	profit_percent = serializers.FloatField(default=0)
	summary = serializers.CharField(default='')
	strategy_description = serializers.CharField(default='')
	updated_on = serializers.DateTimeField()
