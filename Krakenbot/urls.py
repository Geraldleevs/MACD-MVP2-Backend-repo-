# from django.contrib import admin
from django.urls import path
import Krakenbot.views as views

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('api/market', views.MarketView.as_view(), name='market'),
    path('api/simulation', views.SimulationView.as_view(), name='simulation'),
    path('api/backtest', views.BackTestView.as_view(), name='backtest'),
    path('api/update-history-prices', views.UpdateHistoryPricesView.as_view(), name='update history prices'),
    path('api/trade', views.TradeView.as_view(), name='trade'),
    path('api/livetrade', views.LiveTradeView.as_view(), name='create / update / close livetrade'),
    path('api/order', views.ManualTradeView.as_view(), name='create order'),
    path('api/initialise-demo', views.InitialiseDemoView.as_view(), name='initialise demo amount'),
    path('api/news', views.NewsView.as_view(), name='news'),
    path('api/auto-livetrade', views.AutoLiveTradeView.as_view(), name='auto livetrade'),
    path('api/update-candles', views.UpdateCandlesView.as_view(), name='update candles'),
    path('api/check-orders', views.CheckOrdersView.as_view(), name='check and operate orders'),
    path('api/check-lossprofit', views.CheckLossProfitView.as_view(), name='check stop loss and take profit'),
    path('api/calculate-fluctuations', views.CalculateFluctuationsView.as_view(), name='calculate tokens fluctuations'),
    path('api/recalibrate-bot', views.RecalibrateBotView.as_view(), name='recalibrate bot amount'),
]
