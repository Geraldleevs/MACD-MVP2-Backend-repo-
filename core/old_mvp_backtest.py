import numpy as np
import talib


# Define indicator functions using TA-Lib
def use_macd(df):
	macd, macdsignal, _ = talib.MACD(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
	return np.where(macd > macdsignal, 1, -1)


def use_sma(df):
	sma = talib.SMA(df['Close'], timeperiod=30)
	return np.where(df['Close'] > sma, 1, -1)


def use_ema(df):
	ema = talib.EMA(df['Close'], timeperiod=30)
	return np.where(df['Close'] > ema, 1, -1)


def use_adx(df):
	adx = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=14)
	return np.where(adx > 25, 1, -1)


def use_aroon(df):
	aroon_up, aroon_down = talib.AROON(df['High'], df['Low'], timeperiod=14)
	return np.where(aroon_up > aroon_down, 1, -1)


def use_rsi(df, overbought, oversold):
	rsi = talib.RSI(df['Close'], timeperiod=14)
	return np.where(rsi > overbought, -1, np.where(rsi < oversold, 1, 0))


def use_stochastic(df, k_period, d_period, overbought, oversold):
	slowk, _ = talib.STOCH(
		df['High'], df['Low'], df['Close'], fastk_period=k_period, slowk_period=3, slowd_period=d_period
	)
	return np.where(slowk > overbought, -1, np.where(slowk < oversold, 1, 0))


def use_mfi(df):
	if 'Volume' in df.columns:
		mfi = talib.MFI(df['High'], df['Low'], df['Close'], df['Volume'], timeperiod=14)
		return np.where(mfi > 80, -1, np.where(mfi < 20, 1, 0))
	else:
		return np.zeros(len(df))


def use_obv(df):
	if 'Volume' in df.columns:
		obv = talib.OBV(df['Close'], df['Volume'])
		return np.where(obv > obv.shift(1), 1, -1)
	else:
		return np.zeros(len(df))


def use_atr(df):
	atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
	return np.where(atr > atr.shift(1), 1, -1)


def use_bbands(df):
	upperband, _, lowerband = talib.BBANDS(df['Close'], timeperiod=20)
	return np.where(df['Close'] > upperband, -1, np.where(df['Close'] < lowerband, 1, 0))


def use_ad(df):
	if 'Volume' in df.columns:
		ad = talib.AD(df['High'], df['Low'], df['Close'], df['Volume'])
		return np.where(ad > ad.shift(1), 1, -1)
	else:
		return np.zeros(len(df))


def use_ichimoku(df):
	tenkan_sen = (df['High'].rolling(window=9).max() + df['Low'].rolling(window=9).min()) / 2
	kijun_sen = (df['High'].rolling(window=26).max() + df['Low'].rolling(window=26).min()) / 2
	return np.where(tenkan_sen > kijun_sen, 1, -1)


def use_aroonosc(df):
	aroonosc = talib.AROONOSC(df['High'], df['Low'], timeperiod=14)
	return np.where(aroonosc > 0, 1, -1)


def use_dema(df):
	dema = talib.DEMA(df['Close'], timeperiod=30)
	return np.where(df['Close'] > dema, 1, -1)


def use_tema(df):
	tema = talib.TEMA(df['Close'], timeperiod=30)
	return np.where(df['Close'] > tema, 1, -1)


def use_momentum(df):
	mom = talib.MOM(df['Close'], timeperiod=10)
	return np.where(mom > 0, 1, -1)


def use_donchian_channel(df):
	upper_band = df['High'].rolling(window=20).max()
	lower_band = df['Low'].rolling(window=20).min()
	return np.where(df['Close'] > upper_band, 1, np.where(df['Close'] < lower_band, -1, 0))


def use_williams_r(df):
	willr = talib.WILLR(df['High'], df['Low'], df['Close'], timeperiod=14)
	return np.where(willr < -80, 1, np.where(willr > -20, -1, 0))


def use_cci(df):
	cci = talib.CCI(df['High'], df['Low'], df['Close'], timeperiod=14)
	return np.where(cci > 100, -1, np.where(cci < -100, 1, 0))


# Define candlestick pattern functions using TA-Lib with print statements
def use_cdl2crows(df):
	pattern = talib.CDL2CROWS(df['Open'], df['High'], df['Low'], df['Close'])
	return np.where(pattern != 0, np.sign(pattern), 0)


def use_cdl3blackcrows(df):
	pattern = talib.CDL3BLACKCROWS(df['Open'], df['High'], df['Low'], df['Close'])
	return np.where(pattern != 0, np.sign(pattern), 0)


def use_cdl3inside(df):
	pattern = talib.CDL3INSIDE(df['Open'], df['High'], df['Low'], df['Close'])
	return np.where(pattern != 0, np.sign(pattern), 0)


# Additional momentum indicator functions
def use_adxr(df):
	adxr = talib.ADXR(df['High'], df['Low'], df['Close'], timeperiod=14)
	return np.where(adxr > 25, 1, -1)


def use_apo(df):
	apo = talib.APO(df['Close'], fastperiod=12, slowperiod=26)
	return np.where(apo > 0, 1, -1)


def use_bop(df):
	bop = talib.BOP(df['Open'], df['High'], df['Low'], df['Close'])
	return np.where(bop > 0, 1, -1)


def use_cmo(df):
	cmo = talib.CMO(df['Close'], timeperiod=14)
	return np.where(cmo > 0, 1, -1)


def use_dx(df):
	dx = talib.DX(df['High'], df['Low'], df['Close'], timeperiod=14)
	return np.where(dx > 25, 1, -1)


def use_macdext(df):
	macd, macdsignal, _ = talib.MACDEXT(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
	return np.where(macd > macdsignal, 1, -1)


def use_macdfix(df):
	macd, macdsignal, _ = talib.MACDFIX(df['Close'], signalperiod=9)
	return np.where(macd > macdsignal, 1, -1)


def use_minus_di(df):
	minus_di = talib.MINUS_DI(df['High'], df['Low'], df['Close'], timeperiod=14)
	return np.where(minus_di > 25, 1, -1)


def use_minus_dm(df):
	minus_dm = talib.MINUS_DM(df['High'], df['Low'], timeperiod=14)
	return np.where(minus_dm > 0, 1, -1)


def use_plus_di(df):
	plus_di = talib.PLUS_DI(df['High'], df['Low'], df['Close'], timeperiod=14)
	return np.where(plus_di > 25, 1, -1)


def use_plus_dm(df):
	plus_dm = talib.PLUS_DM(df['High'], df['Low'], timeperiod=14)
	return np.where(plus_dm > 0, 1, -1)


def use_ppo(df):
	ppo = talib.PPO(df['Close'], fastperiod=12, slowperiod=26)
	return np.where(ppo > 0, 1, -1)


def use_roc(df):
	roc = talib.ROC(df['Close'], timeperiod=10)
	return np.where(roc > 0, 1, -1)


def use_rocp(df):
	rocp = talib.ROCP(df['Close'], timeperiod=10)
	return np.where(rocp > 0, 1, -1)


def use_rocr(df):
	rocr = talib.ROCR(df['Close'], timeperiod=10)
	return np.where(rocr > 0, 1, -1)


def use_rocr100(df):
	rocr100 = talib.ROCR100(df['Close'], timeperiod=10)
	return np.where(rocr100 > 100, 1, -1)


def use_stochf(df):
	fastk, fastd = talib.STOCHF(df['High'], df['Low'], df['Close'], fastk_period=14, fastd_period=3)
	return np.where(fastk > fastd, 1, -1)


def use_stochrsi(df):
	fastk, fastd = talib.STOCHRSI(df['Close'], timeperiod=14, fastk_period=14, fastd_period=3)
	return np.where(fastk > fastd, 1, -1)


def use_trix(df):
	trix = talib.TRIX(df['Close'], timeperiod=30)
	return np.where(trix > 0, 1, -1)


def use_ultosc(df):
	ultosc = talib.ULTOSC(df['High'], df['Low'], df['Close'], timeperiod1=7, timeperiod2=14, timeperiod3=28)
	return np.where(ultosc > 50, 1, -1)


# Overlap Studies
def use_ht_trendline(df):
	ht_trendline = talib.HT_TRENDLINE(df['Close'])
	return np.where(df['Close'] > ht_trendline, 1, -1)


def use_kama(df):
	kama = talib.KAMA(df['Close'], timeperiod=30)
	return np.where(df['Close'] > kama, 1, -1)


def use_ma(df):
	ma = talib.MA(df['Close'], timeperiod=30)
	return np.where(df['Close'] > ma, 1, -1)


def use_mama(df):
	mama, fama = talib.MAMA(df['Close'])
	return np.where(mama > fama, 1, -1)


def use_mavp(df):
	mavp = talib.MAVP(df['Close'], df['High'], minperiod=2, maxperiod=30)
	return np.where(df['Close'] > mavp, 1, -1)


def use_midpoint(df):
	midpoint = talib.MIDPOINT(df['Close'], timeperiod=14)
	return np.where(df['Close'] > midpoint, 1, -1)


def use_midprice(df):
	midprice = talib.MIDPRICE(df['High'], df['Low'], timeperiod=14)
	return np.where(df['Close'] > midprice, 1, -1)


def use_sar(df):
	sar = talib.SAR(df['High'], df['Low'], acceleration=0.02, maximum=0.2)
	return np.where(df['Close'] > sar, 1, -1)


def use_sarext(df):
	sarext = talib.SAREXT(df['High'], df['Low'])
	return np.where(df['Close'] > sarext, 1, -1)


def use_t3(df):
	t3 = talib.T3(df['Close'], timeperiod=30)
	return np.where(df['Close'] > t3, 1, -1)


def use_trima(df):
	trima = talib.TRIMA(df['Close'], timeperiod=30)
	return np.where(df['Close'] > trima, 1, -1)


def use_wma(df):
	wma = talib.WMA(df['Close'], timeperiod=30)
	return np.where(df['Close'] > wma, 1, -1)
