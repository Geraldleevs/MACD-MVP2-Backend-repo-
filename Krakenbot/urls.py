# from django.contrib import admin
from django.urls import path
import Krakenbot.views as views

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('api/market', views.MarketView.as_view(), name='market'),
    path('api/backtest', views.BackTestView.as_view(), name='backtest'),
    path('api/update-history-prices', views.UpdateHistoryPricesView.as_view(), name='update history prices'),
    path('api/auto-livetrade', views.AutoLiveTradeView.as_view(), name='auto livetrade'),
    path('api/trade', views.TradeView.as_view(), name='trade'),
    path('api/news', views.NewsView.as_view(), name='news'),
    path('api/update-candles', views.UpdateCandlesView.as_view(), name='update candles'),
]
