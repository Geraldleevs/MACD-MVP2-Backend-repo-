import inspect
import re

import numpy as np
import pandas as pd
import talib


class TechnicalAnalysis:
	"""Core functions for technical analysis

	Attributes:
		`options`:
			All technical analysis options. E.g.
			`{'sma': {'name': 'SMA - Simple Moving Average', 'params': {'timeperiod': 30 }}}`
	"""

	options = {}

	def __init__(self):
		members = inspect.getmembers(self, predicate=inspect.ismethod)
		TAs = filter(lambda x: not x[0].startswith('_'), members)

		options = {}
		for ta, fn in TAs:
			docs = fn.__doc__.replace('\n', '').replace('\t', '')
			limits = None
			param_limits = []

			limits = docs.split(';LIMIT:')
			if len(limits) > 1:
				for typing in limits[1].split(';')[0].split(','):
					if ' IN ' not in typing:
						validation = re.split(' (<|>|>=|<=|==|!=) ', typing)
						var = validation[0].strip()
						op = validation[1]
						value = float(validation[2])
						param_limits.append({'variable': var, 'operation': op, 'value': value})
					else:
						validation = typing.split(' IN ')
						var = validation[0].strip()
						value = validation[1]
						value = value.removeprefix('[').removesuffix(']')
						value = value.replace("'", '').replace('"', '')
						value = value.split('|')
						param_limits.append({'variable': var, 'operation': 'IN', 'value': value})

			name = docs.split(';')[0]
			param_list = [p for p in inspect.signature(fn).parameters.values() if p.name != 'df']
			params = {p.name: p.default if p.default is not inspect._empty else None for p in param_list}

			if 'source' in params:
				param_limits.append(
					{
						'variable': 'source',
						'operation': 'IN',
						'value': ['Open', 'High', 'Low', 'Close'],
					}
				)

			options[ta] = {'name': name, 'params': params, 'limits': param_limits}

		self.options = options

	def _macd(self, df: pd.DataFrame, source='Close', fastperiod=12, slowperiod=26, signalperiod=9):
		macd, macdsignal, _ = talib.MACD(
			df[source],
			fastperiod=fastperiod,
			slowperiod=slowperiod,
			signalperiod=signalperiod,
		)
		return macd, macdsignal

	def macd(self, df: pd.DataFrame, source='Close', fastperiod=12, slowperiod=26, signalperiod=9):
		"""MACD - Moving Average Convergence/Divergence;LIMIT:fastperiod >= 2,slowperiod >= 2,signalperiod >= 1"""
		macd = self._macd(df, source=source, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)[0]
		return macd

	def macdsignal(self, df: pd.DataFrame, source='Close', fastperiod=12, slowperiod=26, signalperiod=9):
		"""MACD (Signal) - Moving Average Convergence/Divergence (Signal);LIMIT:fastperiod >= 2,slowperiod >= 2,signalperiod >= 1"""
		macdsignal = self._macd(
			df,
			source=source,
			fastperiod=fastperiod,
			slowperiod=slowperiod,
			signalperiod=signalperiod,
		)[1]
		return macdsignal

	def sma(self, df: pd.DataFrame, source='Close', timeperiod=30):
		"""SMA - Simple Moving Average;LIMIT:timeperiod >= 2"""
		sma = talib.SMA(df[source], timeperiod=timeperiod)
		return sma

	def ema(self, df: pd.DataFrame, source='Close', timeperiod=30):
		"""EMA - Exponential Moving Average;LIMIT:timeperiod >= 2"""
		ema = talib.EMA(df[source], timeperiod=timeperiod)
		return ema

	def adx(self, df: pd.DataFrame, timeperiod=14):
		"""ADX - Average Directional Movement Index;LIMIT:timeperiod >= 2"""
		adx = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=timeperiod)
		return adx

	def _aroon(self, df: pd.DataFrame, timeperiod=14):
		aroon_up, aroon_down = talib.AROON(df['High'], df['Low'], timeperiod=timeperiod)
		return aroon_up, aroon_down

	def aroon_up(self, df: pd.DataFrame, timeperiod=14):
		"""Aroon Up;LIMIT:timeperiod >= 2"""
		aroon_up = self._aroon(df, timeperiod=timeperiod)[0]
		return aroon_up

	def aroon_down(self, df: pd.DataFrame, timeperiod=14):
		"""Aroon Down;LIMIT:timeperiod >= 2"""
		aroon_down = self._aroon(df, timeperiod=timeperiod)[1]
		return aroon_down

	def rsi(self, df: pd.DataFrame, source='Close', timeperiod=14):
		"""RSI - Relative Strength Index;LIMIT:timeperiod >= 2"""
		rsi = talib.RSI(df[source], timeperiod=timeperiod)
		return rsi

	def _stoch(self, df: pd.DataFrame, fastk_period=5, slowk_period=3, slowd_period=3):
		slowk, slowd = talib.STOCH(
			df['High'],
			df['Low'],
			df['Close'],
			fastk_period=fastk_period,
			slowk_period=slowk_period,
			slowd_period=slowd_period,
		)
		return slowk, slowd

	def stoch_slowk(self, df: pd.DataFrame, fastk_period=5, slowk_period=3, slowd_period=3):
		"""Stochastic Oscillator (Slow K);LIMIT:fastk_period >= 1,slowk_period >= 1,slowd_period >= 1"""
		slowk = self._stoch(df, fastk_period=fastk_period, slowk_period=slowk_period, slowd_period=slowd_period)[0]
		return slowk

	def stoch_slowd(self, df: pd.DataFrame, fastk_period=5, slowk_period=3, slowd_period=3):
		"""Stochastic Oscillator (Slow D);LIMIT:fastk_period >= 1,slowk_period >= 1,slowd_period >= 1"""
		slowd = self._stoch(df, fastk_period=fastk_period, slowk_period=slowk_period, slowd_period=slowd_period)[1]
		return slowd

	def mfi(self, df: pd.DataFrame, timeperiod=14):
		"""MFI - Money Flow Index;LIMIT:timeperiod >= 2"""
		mfi = talib.MFI(df['High'], df['Low'], df['Close'], df['Volume'], timeperiod=timeperiod)
		return mfi

	def obv(self, df: pd.DataFrame, shift=0):
		"""OBV - On Balance Volume"""
		obv = talib.OBV(df['Close'], df['Volume'])
		return obv.shift(shift)

	def atr(self, df: pd.DataFrame, timeperiod=14, shift=0):
		"""ATR - Average True Range;LIMIT:timeperiod >= 1"""
		atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=timeperiod)
		return atr.shift(shift)

	def _bbands(self, df: pd.DataFrame, source='Close', timeperiod=20, nbdevup=2, nbdevdn=2):
		upperband, _, lowerband = talib.BBANDS(df[source], timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn)
		return upperband, lowerband

	def bbands_upper(self, df: pd.DataFrame, source='Close', timeperiod=20, nbdevup=2, nbdevdn=2):
		"""Bollinger Bands (Upper Band);LIMIT:timeperiod >= 2"""
		upperband = self._bbands(df, source=source, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn)[0]
		return upperband

	def bbands_lower(self, df: pd.DataFrame, source='Close', timeperiod=20, nbdevup=2, nbdevdn=2):
		"""Bollinger Bands (Lower Band);LIMIT:timeperiod >= 2"""
		lowerband = self._bbands(df, source=source, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn)[1]
		return lowerband

	def ad(self, df: pd.DataFrame, shift=0):
		"""Chaikin A/D Line"""
		ad = talib.AD(df['High'], df['Low'], df['Close'], df['Volume'])
		return ad.shift(shift)

	def tenkan_sen(self, df: pd.DataFrame):
		"""Tenkan-sen"""
		tenkan_sen = (df['High'].rolling(window=9).max() + df['Low'].rolling(window=9).min()) / 2
		return tenkan_sen

	def kijun_sen(self, df: pd.DataFrame):
		"""Kijun-sen"""
		kijun_sen = (df['High'].rolling(window=26).max() + df['Low'].rolling(window=26).min()) / 2
		return kijun_sen

	def senkou_span_a(self, df: pd.DataFrame):
		"""Senkou Span A"""
		tenkan_sen = self.tenkan_sen(df)
		kijun_sen = self.kijun_sen(df)
		senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
		return senkou_span_a

	def senkou_span_b(self, df: pd.DataFrame):
		"""Senkou Span B"""
		senkou_span_b = ((df['High'].rolling(window=52).max() + df['Low'].rolling(window=52).min()) / 2).shift(26)
		return senkou_span_b

	def chikou_span(self, df: pd.DataFrame):
		"""Chikou Span"""
		chikou_span = df['Close'].shift(-26)
		return chikou_span

	def aroonosc(self, df: pd.DataFrame, timeperiod=14):
		"""Aroon Oscillator;LIMIT:timeperiod >= 2"""
		aroonosc = talib.AROONOSC(df['High'], df['Low'], timeperiod=timeperiod)
		return aroonosc

	def dema(self, df: pd.DataFrame, source='Close', timeperiod=30):
		"""DEMA - Double Exponential Moving Average;LIMIT:timeperiod >= 2"""
		dema = talib.DEMA(df[source], timeperiod=timeperiod)
		return dema

	def tema(self, df: pd.DataFrame, source='Close', timeperiod=30):
		"""TEMA - Triple Exponential Moving Average;LIMIT:timeperiod >= 2"""
		tema = talib.TEMA(df[source], timeperiod=timeperiod)
		return tema

	def mom(self, df: pd.DataFrame, source='Close', timeperiod=10):
		"""Momentum;LIMIT:timeperiod >= 1"""
		mom = talib.MOM(df[source], timeperiod=timeperiod)
		return mom

	def donchian_upper(self, df: pd.DataFrame):
		"""Donchian Channels (Upper band)"""
		upper_band = df['High'].rolling(window=20).max()
		return upper_band

	def donchian_lower(self, df: pd.DataFrame):
		"""Donchian Channels (Lower band)"""
		lower_band = df['Low'].rolling(window=20).min()
		return lower_band

	def willr(self, df: pd.DataFrame, timeperiod=14):
		"""Williams' %R;LIMIT:timeperiod >= 2"""
		willr = talib.WILLR(df['High'], df['Low'], df['Close'], timeperiod=timeperiod)
		return willr

	def cci(self, df: pd.DataFrame, timeperiod=14):
		"""CCI - Commodity Channel Index;LIMIT:timeperiod >= 2"""
		cci = talib.CCI(df['High'], df['Low'], df['Close'], timeperiod=timeperiod)
		return cci

	def cdl2crows(self, df: pd.DataFrame):
		"""Two Crows"""
		pattern = talib.CDL2CROWS(df['Open'], df['High'], df['Low'], df['Close'])
		return pattern

	def cdl3blackcrows(self, df: pd.DataFrame):
		"""Three Black Crows"""
		pattern = talib.CDL3BLACKCROWS(df['Open'], df['High'], df['Low'], df['Close'])
		return pattern

	def cdl3inside(self, df: pd.DataFrame):
		"""Three Inside Up/Down"""
		pattern = talib.CDL3INSIDE(df['Open'], df['High'], df['Low'], df['Close'])
		return pattern

	def adxr(self, df: pd.DataFrame, timeperiod=14):
		"""ADXR - Average Directional Movement Index Rating;LIMIT:timeperiod >= 2"""
		adxr = talib.ADXR(df['High'], df['Low'], df['Close'], timeperiod=timeperiod)
		return adxr

	def apo(self, df: pd.DataFrame, source='Close', fastperiod=12, timeperiod=26):
		"""APO - Absolute Price Oscillator;LIMIT:fastperiod >= 2,timeperiod >= 2"""
		apo = talib.APO(df[source], fastperiod=fastperiod, slowperiod=timeperiod)
		return apo

	def bop(self, df: pd.DataFrame):
		"""BOP - Balance of Power"""
		bop = talib.BOP(df['Open'], df['High'], df['Low'], df['Close'])
		return bop

	def cmo(self, df: pd.DataFrame, source='Close', timeperiod=14):
		"""CMO - Chande Momentum Oscillator;LIMIT:timeperiod >= 2"""
		cmo = talib.CMO(df[source], timeperiod=timeperiod)
		return cmo

	def dx(self, df: pd.DataFrame, timeperiod=14):
		"""DX - Directional Movement Index;LIMIT:timeperiod >= 2"""
		dx = talib.DX(df['High'], df['Low'], df['Close'], timeperiod=timeperiod)
		return dx

	def _macdext(self, df: pd.DataFrame, source='Close', fastperiod=12, slowperiod=26, signalperiod=9):
		macd, macdsignal, _ = talib.MACDEXT(
			df[source],
			fastperiod=fastperiod,
			slowperiod=slowperiod,
			signalperiod=signalperiod,
		)
		return macd, macdsignal

	def macdext(self, df: pd.DataFrame, source='Close', fastperiod=12, slowperiod=26, signalperiod=9):
		"""MACDext - MACD with controllable MA type;LIMIT:fastperiod >= 2,slowperiod >= 2,signalperiod >= 1"""
		macd = self._macdext(
			df,
			source=source,
			fastperiod=fastperiod,
			slowperiod=slowperiod,
			signalperiod=signalperiod,
		)[0]
		return macd

	def macdext_signal(self, df: pd.DataFrame, source='Close', fastperiod=12, slowperiod=26, signalperiod=9):
		"""MACDext (Signal) - MACD with controllable MA type (Signal);LIMIT:fastperiod >= 2,slowperiod >= 2,signalperiod >= 1"""
		macdsignal = self._macdext(
			df,
			source=source,
			fastperiod=fastperiod,
			slowperiod=slowperiod,
			signalperiod=signalperiod,
		)[1]
		return macdsignal

	def _macdfix(self, df: pd.DataFrame, source='Close', signalperiod=9):
		macd, macdsignal, _ = talib.MACDFIX(df[source], signalperiod=signalperiod)
		return macd, macdsignal

	def macdfix(self, df: pd.DataFrame, source='Close', signalperiod=9):
		"""MACD-Fixed - Moving Average Convergence/Divergence Fix 12/26;LIMIT:signalperiod >= 1"""
		macd = self._macdfix(df, source=source, signalperiod=signalperiod)[0]
		return macd

	def macdfix_signal(self, df: pd.DataFrame, source='Close', signalperiod=9):
		"""MACD-Fixed (signal) - Moving Average Convergence/Divergence Fix 12/26 (Signal);LIMIT:signalperiod >= 1"""
		macdsignal = self._macdfix(df, source=source, signalperiod=signalperiod)[1]
		return macdsignal

	def minus_di(self, df: pd.DataFrame, timeperiod=14):
		"-DI - Minus Directional Indicator;LIMIT:timeperiod >= 1"
		minus_di = talib.MINUS_DI(df['High'], df['Low'], df['Close'], timeperiod=timeperiod)
		return minus_di

	def minus_dm(self, df: pd.DataFrame, timeperiod=14):
		"""-DM - Minus Directional Movement;LIMIT:timeperiod >= 1"""
		minus_dm = talib.MINUS_DM(df['High'], df['Low'], timeperiod=timeperiod)
		return minus_dm

	def plus_di(self, df: pd.DataFrame, timeperiod=14):
		"""+DI - Plus Directional Indicator;LIMIT:timeperiod >= 1"""
		plus_di = talib.PLUS_DI(df['High'], df['Low'], df['Close'], timeperiod=timeperiod)
		return plus_di

	def plus_dm(self, df: pd.DataFrame, timeperiod=14):
		"""+DM - Plus Directional Movement;LIMIT:timeperiod >= 1"""
		plus_dm = talib.PLUS_DM(df['High'], df['Low'], timeperiod=timeperiod)
		return plus_dm

	def ppo(self, df: pd.DataFrame, source='Close', fastperiod=12, slowperiod=26):
		"""PPO - Percentage Price Oscillator;LIMIT:fastperiod >= 2,slowperiod >= 2"""
		ppo = talib.PPO(df[source], fastperiod=fastperiod, slowperiod=slowperiod)
		return ppo

	def roc(self, df: pd.DataFrame, source='Close', timeperiod=10):
		"""ROC - Rate of Change;LIMIT:timeperiod >= 1"""
		roc = talib.ROC(df[source], timeperiod=timeperiod)
		return roc

	def rocp(self, df: pd.DataFrame, source='Close', timeperiod=10):
		"""ROCP - Rate of Change Percentage;LIMIT:timeperiod >= 1"""
		rocp = talib.ROCP(df[source], timeperiod=timeperiod)
		return rocp

	def rocr(self, df: pd.DataFrame, source='Close', timeperiod=10):
		"""ROCR - Rate of Change Ratio;LIMIT:timeperiod >= 1"""
		rocr = talib.ROCR(df[source], timeperiod=timeperiod)
		return rocr

	def rocr100(self, df: pd.DataFrame, source='Close', timeperiod=10):
		"""ROCR100 - Rate of Change Ratio (100 Scale);LIMIT:timeperiod >= 1"""
		rocr100 = talib.ROCR100(df[source], timeperiod=timeperiod)
		return rocr100

	def _stochf(self, df: pd.DataFrame, fastk_period=14, fastd_period=3):
		fastk, fastd = talib.STOCHF(
			df['High'],
			df['Low'],
			df['Close'],
			fastk_period=fastk_period,
			fastd_period=fastd_period,
		)
		return fastk, fastd

	def stochf_fastk(self, df: pd.DataFrame, fastk_period=14, fastd_period=3):
		"""Stochastic Fast (Fast K);LIMIT:fastk_period >= 1,fastd_period >= 1"""
		fastk = self._stochf(df, fastk_period=fastk_period, fastd_period=fastd_period)[0]
		return fastk

	def stochf_fastd(self, df: pd.DataFrame, fastk_period=14, fastd_period=3):
		"""Stochastic Fast (Fast D);LIMIT:fastk_period >= 1,fastd_period >= 1"""
		fastd = self._stochf(df, fastk_period=fastk_period, fastd_period=fastd_period)[1]
		return fastd

	def _stochrsi(self, df: pd.DataFrame, source='Close', timeperiod=14, fastk_period=14, fastd_period=3):
		fastk, fastd = talib.STOCHRSI(
			df[source],
			timeperiod=timeperiod,
			fastk_period=fastk_period,
			fastd_period=fastd_period,
		)
		return fastk, fastd

	def stochrsi_fastk(self, df: pd.DataFrame, source='Close', timeperiod=14, fastk_period=14, fastd_period=3):
		"""Stochastic Relative Strength Index (Fast K);LIMIT:timeperiod >= 2,fastk_period >= 1,fastd_period >= 1"""
		fastk = self._stochrsi(
			df,
			source=source,
			timeperiod=timeperiod,
			fastk_period=fastk_period,
			fastd_period=fastd_period,
		)[0]
		return fastk

	def stochrsi_fastd(self, df: pd.DataFrame, source='Close', timeperiod=14, fastk_period=14, fastd_period=3):
		"""Stochastic Relative Strength Index (Fast D);LIMIT:timeperiod >= 2,fastk_period >= 1,fastd_period >= 1"""
		fastd = self._stochrsi(
			df,
			source=source,
			timeperiod=timeperiod,
			fastk_period=fastk_period,
			fastd_period=fastd_period,
		)[1]
		return fastd

	def trix(self, df: pd.DataFrame, source='Close', timeperiod=30):
		"""TRIX - Triple Smoothed Exponential Moving Average;LIMIT:timeperiod >= 1"""
		trix = talib.TRIX(df[source], timeperiod=timeperiod)
		return trix

	def ultosc(self, df: pd.DataFrame, timeperiod1=7, timeperiod2=14, timeperiod3=28):
		"""UltOsc - Ultimate Oscillato;LIMIT:timeperiod1 >= 1,timeperiod2 >= 1,timeperiod3 >= 1"""
		ultosc = talib.ULTOSC(
			df['High'],
			df['Low'],
			df['Close'],
			timeperiod1=timeperiod1,
			timeperiod2=timeperiod2,
			timeperiod3=timeperiod3,
		)
		return ultosc

	def ht_trendline(self, df: pd.DataFrame, source='Close'):
		"""HT Trendline - Hilbert Transform - Instantaneous Trendline"""
		ht_trendline = talib.HT_TRENDLINE(df[source])
		return ht_trendline

	def kama(self, df: pd.DataFrame, source='Close', timeperiod=30):
		"""KAMA - Kaufman Adaptive Moving Average;LIMIT:timeperiod >= 2"""
		kama = talib.KAMA(df[source], timeperiod=timeperiod)
		return kama

	def ma(self, df: pd.DataFrame, source='Close', timeperiod=30):
		"""MA - All Moving Average;LIMIT:timeperiod >= 1"""
		ma = talib.MA(df[source], timeperiod=timeperiod)
		return ma

	def _mama(self, df: pd.DataFrame, source='Close', fastlimit=0.5, slowlimit=0.05):
		mama, fama = talib.MAMA(df[source], fastlimit=fastlimit, slowlimit=slowlimit)
		return mama, fama

	def mama_fast(self, df: pd.DataFrame, source='Close', fastlimit=0.5, slowlimit=0.05):
		"""MAMA - MESA Adaptive Moving Average (MAMA);LIMIT:fastlimit > 0,fastlimit < 1,slowlimit > 0,slowlimit < 1"""
		mama = self._mama(df, source=source, fastlimit=fastlimit, slowlimit=slowlimit)[0]
		return mama

	def mama_slow(self, df: pd.DataFrame, source='Close', fastlimit=0.5, slowlimit=0.05):
		"""MAMA - MESA Adaptive Moving Average (FAMA);LIMIT:fastlimit > 0,fastlimit < 1,slowlimit > 0,slowlimit < 1"""
		fama = self._mama(df, source=source, fastlimit=fastlimit, slowlimit=slowlimit)[1]
		return fama

	def mavp(self, df: pd.DataFrame, source='Close', periods='High', minperiod=2, maxperiod=30):
		"""MAVP - Moving Average with Variable Period;LIMIT:minperiod > 2,maxperiod > 2,periods IN ['Open'|'High'|'Low'|'Close']"""
		mavp = talib.MAVP(df[source], df[periods], minperiod=minperiod, maxperiod=maxperiod)
		return mavp

	def midpoint(self, df: pd.DataFrame, source='Close', timeperiod=14):
		"""MidPoint over period;LIMIT:timeperiod >= 2"""
		midpoint = talib.MIDPOINT(df[source], timeperiod=timeperiod)
		return midpoint

	def midprice(self, df: pd.DataFrame, timeperiod=14):
		"""Midpoint Price over period;LIMIT:timeperiod >= 2"""
		midprice = talib.MIDPRICE(df['High'], df['Low'], timeperiod=timeperiod)
		return midprice

	def psar(self, df: pd.DataFrame, acceleration=0.02, maximum=0.2):
		"""PSAR - Parabolic Stop and Reverse;LIMIT:acceleration >= 0,maximum >= 0"""
		psar = talib.SAR(df['High'], df['Low'], acceleration=acceleration, maximum=maximum)
		return psar

	def sarext(
		self,
		df: pd.DataFrame,
		startvalue=0,
		offsetonreverse=0,
		accelerationinitlong=0,
		accelerationlong=0,
		accelerationmaxlong=0,
		accelerationinitshort=0,
		accelerationshort=0,
		accelerationmaxshort=0,
	):
		"""SAR - Parabolic SAR (Extended);
		LIMIT:offsetonreverse >= 0,
		accelerationinitlong >= 0,
		accelerationlong >= 0,
		accelerationmaxlong >= 0,
		accelerationinitshort >= 0,
		accelerationshort >= 0,
		accelerationmaxshort >= 0"""
		sarext = talib.SAREXT(
			df['High'],
			df['Low'],
			startvalue=startvalue,
			offsetonreverse=offsetonreverse,
			accelerationinitlong=accelerationinitlong,
			accelerationlong=accelerationlong,
			accelerationmaxlong=accelerationmaxlong,
			accelerationinitshort=accelerationinitshort,
			accelerationshort=accelerationshort,
			accelerationmaxshort=accelerationmaxshort,
		)
		return sarext

	def t3(self, df: pd.DataFrame, source='Close', timeperiod=30, vfactor=0.7):
		"""T3 - Triple Exponential Moving Average;LIMIT:timeperiod >= 2,vfactor >= 0,vfactor <= 1"""
		t3 = talib.T3(df[source], timeperiod=timeperiod, vfactor=vfactor)
		return t3

	def trima(self, df: pd.DataFrame, source='Close', timeperiod=30):
		"""TRIMA - Triangular Moving Average;LIMIT:timeperiod >= 2"""
		trima = talib.TRIMA(df[source], timeperiod=timeperiod)
		return trima

	def wma(self, df: pd.DataFrame, source='Close', timeperiod=30):
		"""WMA - Weighted Moving Average;LIMIT:timeperiod >= 2"""
		wma = talib.WMA(df[source], timeperiod=timeperiod)
		return wma


class TechnicalAnalysisTemplate:
	"""Technical Analysis Templates

	Attributes:
		`templates`:
			All technical analysis templates. E.g.
			`{'sma': {'description': 'Buy: Close > SMA;Sell: Close <= SMA', 'function': def (df: pd.DataFrame): ndarray}}`
	"""

	templates = {}

	def __init__(self, TA=TechnicalAnalysis()):
		self.TA = TA

		members = inspect.getmembers(self, predicate=inspect.ismethod)
		TAs = filter(lambda x: not x[0].startswith('_'), members)

		templates = {}
		for ta, fn in TAs:
			desc = fn.__doc__
			templates[ta] = {'description': desc, 'function': fn}

		self.templates = templates

	def macd(self, df: pd.DataFrame):
		"""Buy: MACD > MACD Signal;Sell: MACD <= MACD Signal"""
		macd = self.TA.macd(
			df,
		)
		macdsignal = self.TA.macdsignal(df)
		return np.where(macd > macdsignal, 1, -1)

	def sma(self, df: pd.DataFrame):
		"""Buy: Close > SMA;Sell: Close <= SMA"""
		sma = self.TA.sma(df)
		return np.where(df['Close'] > sma, 1, -1)

	def ema(self, df: pd.DataFrame):
		"""Buy: Close > EMA;Sell: Close <= EMA"""
		ema = self.TA.ema(df)
		return np.where(df['Close'] > ema, 1, -1)

	def adx(self, df: pd.DataFrame):
		"""Buy: ADX > 25;Sell: ADX <= 25"""
		adx = self.TA.adx(df)
		return np.where(adx > 25, 1, -1)

	def aroon(self, df: pd.DataFrame):
		"""Buy: Aroon Up > Aroon Down;Sell: Aroon Up <= Aroon Down"""
		aroon_up = self.TA.aroon_up(df)
		aroon_down = self.TA.aroon_down(df)
		return np.where(aroon_up > aroon_down, 1, -1)

	def _rsi(self, df: pd.DataFrame, overbought: float, oversold: float):
		"""Buy: RSI < oversold;Sell: RSI > overbought"""
		rsi = self.TA.rsi(df)
		return np.where(rsi > overbought, -1, np.where(rsi < oversold, 1, 0))

	def rsi_70_30(self, df: pd.DataFrame):
		"""Buy: RSI < 30;Sell: RSI > 70"""
		return self._rsi(df, 70, 30)

	def rsi_71_31(self, df: pd.DataFrame):
		"""Buy: RSI < 31;Sell: RSI > 71"""
		return self._rsi(df, 71, 31)

	def rsi_72_32(self, df: pd.DataFrame):
		"""Buy: RSI < 32;Sell: RSI > 72"""
		return self._rsi(df, 72, 32)

	def rsi_73_33(self, df: pd.DataFrame):
		"""Buy: RSI < 33;Sell: RSI > 73"""
		return self._rsi(df, 73, 33)

	def rsi_74_34(self, df: pd.DataFrame):
		"""Buy: RSI < 34;Sell: RSI > 74"""
		return self._rsi(df, 74, 34)

	def rsi_75_35(self, df: pd.DataFrame):
		"""Buy: RSI < 35;Sell: RSI > 75"""
		return self._rsi(df, 75, 35)

	def _stoch(self, df: pd.DataFrame, k_period: float, d_period: float, overbought: float, oversold: float):
		"""Buy: Stoch Slow K < oversold;Sell: Stoch Slow K > overbought;(Fast K Period = k_period, Slow D Period = d_period)"""
		slowk = self.TA.stoch_slowk(df, fastk_period=k_period, slowd_period=d_period)
		return np.where(slowk > overbought, -1, np.where(slowk < oversold, 1, 0))

	def stoch_14_3_80_20(self, df: pd.DataFrame):
		"""Buy: Stoch Slow K < 20;Sell: Stoch Slow K > 80;(Fast K Period = 14, Slow D Period = 3)"""
		return self._stoch(df, 14, 3, 80, 20)

	def stoch_14_3_85_15(self, df: pd.DataFrame):
		"""Buy: Stoch Slow K < 15;Sell: Stoch Slow K > 85;(Fast K Period = 14, Slow D Period = 3)"""
		return self._stoch(df, 14, 3, 85, 15)

	def stoch_10_3_80_20(self, df: pd.DataFrame):
		"""Buy: Stoch Slow K < 20;Sell: Stoch Slow K > 80;(Fast K Period = 10, Slow D Period = 3)"""
		return self._stoch(df, 10, 3, 80, 20)

	def stoch_10_3_85_15(self, df: pd.DataFrame):
		"""Buy: Stoch Slow K < 15;Sell: Stoch Slow K > 85;(Fast K Period = 10, Slow D Period = 3)"""
		return self._stoch(df, 10, 3, 85, 15)

	def stoch_21_5_80_20(self, df: pd.DataFrame):
		"""Buy: Stoch Slow K < 20;Sell: Stoch Slow K > 80;(Fast K Period = 21, Slow D Period = 5)"""
		return self._stoch(df, 21, 5, 80, 20)

	def stoch_21_5_85_15(self, df: pd.DataFrame):
		"""Buy: Stoch Slow K < 15;Sell: Stoch Slow K > 85;(Fast K Period = 21, Slow D Period = 5)"""
		return self._stoch(df, 21, 5, 85, 15)

	def mfi(self, df: pd.DataFrame):
		"""Buy: MFI < 20;Sell: MFI > 80"""
		mfi = self.TA.mfi(df)
		return np.where(mfi > 80, -1, np.where(mfi < 20, 1, 0))

	def obv(self, df: pd.DataFrame):
		"""Buy: OBV (Shift 0) > OBV (Shift 1);Sell: OBV (Shift 0) <= OBV (Shift 1)"""
		obv0 = self.TA.obv(df)
		obv1 = self.TA.obv(df, shift=1)
		return np.where(obv0 > obv1, 1, -1)

	def atr(self, df: pd.DataFrame):
		"""Buy: ATR (Shift 0) > ATR (Shift 1);Sell: ATR (Shift 0) <= ATR (Shift 1)"""
		atr0 = self.TA.atr(df)
		atr1 = self.TA.atr(df, shift=1)
		return np.where(atr0 > atr1, 1, -1)

	def bbands(self, df: pd.DataFrame):
		"""Buy: Close < BBand Lower;Sell: Close > BBand Upper"""
		upperband = self.TA.bbands_upper(df)
		lowerband = self.TA.bbands_lower(df)
		return np.where(df['Close'] > upperband, -1, np.where(df['Close'] < lowerband, 1, 0))

	def ad(self, df: pd.DataFrame):
		"""Buy: AD (Shift 0) > AD (Shift 1);Sell: AD (Shift 0) <= AD (Shift 1)"""
		ad0 = self.TA.ad(df)
		ad1 = self.TA.ad(df, shift=1)
		return np.where(ad0 > ad1, 1, -1)

	def ichimoku(self, df: pd.DataFrame):
		"""Buy: Tenkan-sen > Kijun-sen;Sell: Tenkan-sen <= Kijun-sen"""
		tenkan_sen = self.TA.tenkan_sen(df)
		kijun_sen = self.TA.kijun_sen(df)
		return np.where(tenkan_sen > kijun_sen, 1, -1)

	def aroonosc(self, df: pd.DataFrame):
		"""Buy: Aroon OSC > 0;Sell: Aroon OSC <= 0"""
		aroonosc = self.TA.aroonosc(df)
		return np.where(aroonosc > 0, 1, -1)

	def dema(self, df: pd.DataFrame):
		"""Buy: Close > DEMA;Sell: Close <= DEMA"""
		dema = self.TA.dema(df)
		return np.where(df['Close'] > dema, 1, -1)

	def tema(self, df: pd.DataFrame):
		"""Buy: Close > TEMA;Sell: Close <= TEMA"""
		tema = self.TA.tema(df)
		return np.where(df['Close'] > tema, 1, -1)

	def mom(self, df: pd.DataFrame):
		"""Buy: Momentum > 0;Sell: Momentum <= 0"""
		mom = self.TA.mom(df)
		return np.where(mom > 0, 1, -1)

	def donchian(self, df: pd.DataFrame):
		"""Buy: Close > Donchian Upper;Sell: Close < Donchian Lower"""
		upperband = self.TA.donchian_upper(df)
		lowerband = self.TA.donchian_lower(df)
		return np.where(df['Close'] > upperband, 1, np.where(df['Close'] < lowerband, -1, 0))

	def willr(self, df: pd.DataFrame):
		"""Buy: Will R < -80;Sell: Will R > -20"""
		willr = self.TA.willr(df)
		return np.where(willr < -80, 1, np.where(willr > -20, -1, 0))

	def cci(self, df: pd.DataFrame):
		"""Buy: CCI < -100;Sell: CCI > 100"""
		cci = self.TA.cci(df)
		return np.where(cci > 100, -1, np.where(cci < -100, 1, 0))

	def cdl2crows(self, df: pd.DataFrame):
		"""Buy: Two Crows > 0;Sell: Two Crows < 0"""
		pattern = self.TA.cdl2crows(df)
		return np.where(pattern != 0, np.sign(pattern), 0)

	def cdl3blackcrows(self, df: pd.DataFrame):
		"""Buy: Three Black Crows > 0;Sell: Three Black Crows < 0"""
		pattern = self.TA.cdl3blackcrows(df)
		return np.where(pattern != 0, np.sign(pattern), 0)

	def cdl3inside(self, df: pd.DataFrame):
		"""Buy: Three Inside Up/Down > 0;Sell: Three Inside Up/Down < 0"""
		pattern = self.TA.cdl3inside(df)
		return np.where(pattern != 0, np.sign(pattern), 0)

	def adxr(self, df: pd.DataFrame):
		"""Buy: ADXR > 25;Sell: ADXR <= 25"""
		adxr = self.TA.adxr(df)
		return np.where(adxr > 25, 1, -1)

	def apo(self, df: pd.DataFrame):
		"""Buy: APO > 0;Sell: APO <= 0"""
		apo = self.TA.apo(df)
		return np.where(apo > 0, 1, -1)

	def bop(self, df: pd.DataFrame):
		"""Buy: BOP > 0;Sell: BOP <= 0"""
		bop = self.TA.bop(df)
		return np.where(bop > 0, 1, -1)

	def cmo(self, df: pd.DataFrame):
		"""Buy: CMO > 0;Sell: CMO <= 0"""
		cmo = self.TA.cmo(df)
		return np.where(cmo > 0, 1, -1)

	def dx(self, df: pd.DataFrame):
		"""Buy: DX > 25;Sell: DX <= 25"""
		dx = self.TA.dx(df)
		return np.where(dx > 25, 1, -1)

	def macdext(self, df: pd.DataFrame):
		"""Buy: MACDext > MACDext Signal;Sell: MACDext <= MACDext Signal"""
		macd = self.TA.macdext(df)
		macdsignal = self.TA.macdext_signal(df)
		return np.where(macd > macdsignal, 1, -1)

	def macdfix(self, df: pd.DataFrame):
		"""Buy: MACD-Fixed > MACD-Fixed Signal;Sell: MACD-Fixed <= MACD-Fixed Signal"""
		macd = self.TA.macdfix(df)
		macdsignal = self.TA.macdfix_signal(df)
		return np.where(macd > macdsignal, 1, -1)

	def minus_di(self, df: pd.DataFrame):
		"""Buy: -DI > 25;Sell: -DI <= 25"""
		minus_di = self.TA.minus_di(df)
		return np.where(minus_di > 25, 1, -1)

	def minus_dm(self, df: pd.DataFrame):
		"""Buy: -DM > 0;Sell: -DM <= 0"""
		minus_dm = self.TA.minus_dm(df)
		return np.where(minus_dm > 0, 1, -1)

	def plus_di(self, df: pd.DataFrame):
		"""Buy: +DI > 25;Sell: +DI <= 25"""
		plus_di = self.TA.plus_di(df)
		return np.where(plus_di > 25, 1, -1)

	def plus_dm(self, df: pd.DataFrame):
		"""Buy: +DM > 0;Sell: +DM <= 0"""
		plus_dm = self.TA.plus_dm(df)
		return np.where(plus_dm > 0, 1, -1)

	def ppo(self, df: pd.DataFrame):
		"""Buy: PPO > 0;Sell: PPO <= 0"""
		ppo = self.TA.ppo(df)
		return np.where(ppo > 0, 1, -1)

	def roc(self, df: pd.DataFrame):
		"""Buy: ROC > 0;Sell: ROC <= 0"""
		roc = self.TA.roc(df)
		return np.where(roc > 0, 1, -1)

	def rocp(self, df: pd.DataFrame):
		"""Buy: ROCP > 0;Sell: ROCP <= 0"""
		rocp = self.TA.rocp(df)
		return np.where(rocp > 0, 1, -1)

	def rocr(self, df: pd.DataFrame):
		"""Buy: ROCR > 0;Sell: ROCR <= 0"""
		rocr = self.TA.rocr(df)
		return np.where(rocr > 0, 1, -1)

	def rocr100(self, df: pd.DataFrame):
		"""Buy: ROCR100 > 100;Sell: ROCR100 <= 100"""
		rocr100 = self.TA.rocr100(df)
		return np.where(rocr100 > 100, 1, -1)

	def stochf(self, df: pd.DataFrame):
		"""Buy: STOCHF Fast K > STOCHF Fast D;Sell: STOCHF Fast K <= STOCHF Fast D"""
		fastk = self.TA.stochf_fastk(df)
		fastd = self.TA.stochf_fastd(df)
		return np.where(fastk > fastd, 1, -1)

	def stochrsi(self, df: pd.DataFrame):
		"""Buy: STOCHRSI Fast K > STOCHRSI Fast D;Sell: STOCHRSI Fast K <= STOCHRSI Fast D"""
		fastk = self.TA.stochrsi_fastk(df)
		fastd = self.TA.stochrsi_fastd(df)
		return np.where(fastk > fastd, 1, -1)

	def trix(self, df: pd.DataFrame):
		"""Buy: TRIX > 0;Sell: TRIX <= 0"""
		trix = self.TA.trix(df)
		return np.where(trix > 0, 1, -1)

	def ultosc(self, df: pd.DataFrame):
		"""Buy: UltOsc > 50;Sell: UltOsc <= 50"""
		ultosc = self.TA.ultosc(df)
		return np.where(ultosc > 50, 1, -1)

	def ht_trendline(self, df: pd.DataFrame):
		"""Buy: Close > HT TRENDLINE;Sell: Close <= HT TRENDLINE"""
		ht_trendline = self.TA.ht_trendline(df)
		return np.where(df['Close'] > ht_trendline, 1, -1)

	def kama(self, df: pd.DataFrame):
		"""Buy: Close > KAMA;Sell: Close <= KAMA"""
		kama = self.TA.kama(df)
		return np.where(df['Close'] > kama, 1, -1)

	def ma(self, df: pd.DataFrame):
		"""Buy: Close > MA;Sell: Close <= MA"""
		ma = self.TA.ma(df)
		return np.where(df['Close'] > ma, 1, -1)

	def mama(self, df: pd.DataFrame):
		"""Buy: MAMA > FAMA;Sell: MAMA <= FAMA"""
		mama_fast = self.TA.mama_fast(df)
		mama_slow = self.TA.mama_slow(df)
		return np.where(mama_fast > mama_slow, 1, -1)

	def mavp(self, df: pd.DataFrame):
		"""Buy: Close > MAVP;Sell: Close <= MAVP"""
		mavp = self.TA.mavp(df)
		return np.where(df['Close'] > mavp, 1, -1)

	def midpoint(self, df: pd.DataFrame):
		"""Buy: Close > MidPoint;Sell: Close <= MidPoint"""
		midpoint = self.TA.midpoint(df)
		return np.where(df['Close'] > midpoint, 1, -1)

	def midprice(self, df: pd.DataFrame):
		"""Buy: Close > MidPrice;Sell: Close <= MidPrice"""
		midprice = self.TA.midprice(df)
		return np.where(df['Close'] > midprice, 1, -1)

	def psar(self, df: pd.DataFrame):
		"""Buy: Close > PSAR;Sell: Close <= PSAR"""
		psar = self.TA.psar(df)
		return np.where(df['Close'] > psar, 1, -1)

	def sarext(self, df: pd.DataFrame):
		"""Buy: Close > SAR-ext;Sell: Close <= SAR-ext"""
		sarext = self.TA.sarext(df)
		return np.where(df['Close'] > sarext, 1, -1)

	def t3(self, df: pd.DataFrame):
		"""Buy: Close > T3;Sell: Close <= T3"""
		t3 = self.TA.t3(df)
		return np.where(df['Close'] > t3, 1, -1)

	def trima(self, df: pd.DataFrame):
		"""Buy: Close > TRIMA;Sell: Close <= TRIMA"""
		trima = self.TA.trima(df)
		return np.where(df['Close'] > trima, 1, -1)

	def wma(self, df: pd.DataFrame):
		"""Buy: Close > WMA;Sell: Close <= WMA"""
		wma = self.TA.wma(df)
		return np.where(df['Close'] > wma, 1, -1)
