# from django.contrib import admin
from django.urls import path
import Krakenbot.views as views

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('api/market', views.MarketView.as_view(), name='market'),
    path('api/backtest', views.BackTestView.as_view(), name='backtest'),
    path('api/trade', views.TradeView.as_view(), name='trade'),
]
