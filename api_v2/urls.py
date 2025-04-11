from django.urls import path

from api_v2 import views

urlpatterns = [
	path('technical-indicators', views.TechnicalIndicators.as_view(), name='get-technical-indicators'),
	path('backtest-templates', views.BacktestTemplates.as_view(), name='get-backtest-templates'),
	path('backtest-symbols', views.BacktestSymbols.as_view(), name='get-backtest-symbols'),
	path('backtest-timeframes', views.BacktestTimeframes.as_view(), name='get-backtest-timeframes'),
	path('ohlc-time', views.OhlcDataTime.as_view(), name='get-ohlc-time'),
	path('ohlc-data', views.OhlcData.as_view(), name='get-ohlc-data'),
	path('indicators', views.RunIndicators.as_view(), name='analyse-indicators'),
	path('backtest', views.RunBacktest.as_view(), name='run-backtest'),
]
