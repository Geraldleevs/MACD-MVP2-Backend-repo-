# from django.contrib import admin
from django.urls import path
import Krakenbot.views as views
import Krakenbot.views_v2 as views_v2

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
    path('api/scheduled-processes', views.ScheduledView.as_view(), name='scheduled processes'),

    path('api/v2/favourite-tokens', views_v2.FavouriteTokens.as_view(), name='favourite tokens'),
    path('api/v2/market-list',      views_v2.MarketList.as_view(), name='market list'),
    path('api/v2/market-pairs',     views_v2.MarketPairs.as_view(), name='market pairs'),
    path('api/v2/user-activities',  views_v2.UserActivities.as_view(), name='user activities'),
    path('api/v2/user-assets',      views_v2.UserAssets.as_view(), name='user assets'),
    path('api/v2/user-dashboard',   views_v2.UserDashboard.as_view(), name='user dashboard'),
    path('api/v2/user-portfolio',   views_v2.UserPortfolio.as_view(), name='user portfolio'),
    path('api/v2/user-profile',     views_v2.UserProfile.as_view(), name='user profile'),
    path('api/v2/user-wallet-value',views_v2.UserWalletValue.as_view(), name='user wallet value'),
]
