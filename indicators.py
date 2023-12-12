import numpy as np
import pandas as pd
import ta

def get_sma(close, period):
    ma = close.rolling(period).mean()
    return pd.Series(ma)

def get_ema(close, period):
    """ This function takes closing price and period and returns exponential moving average"""
    close = close.squeeze()
    #calculate Multiplier (smoothing factor)
    multiplier = 2 / (period + 1)
    #calculate Simple Moving Average
    ma = get_sma(close, period)
    #initialize the Exponential Moving Average list
    ema = [np.NaN] * len(close)

    #iterate over the closing prices
    for index in range(len(close)):
        #check index equals the period calculate EMA
        if index == period:
            ema[index] = close.iloc[index] * multiplier + ma[index - 1] * (1 - multiplier)
        #check index is greater than the period calculate follwing EMA
        if index > period:
            ema[index] = close.iloc[index] * multiplier + ema[index - 1] * (1 - multiplier)

    return pd.Series(ema)

def get_macd(close, fast_period = 12, slow_period = 26, smoothing = 9):
    """ This function takes in closing price, a period of 12 and 26 and a smoothing value and returns"""

    #calculate MACD using the difference of EMA periods 12 and 26
    macd = get_ema(close, 12) - get_ema(close, 26)
    #create series for signal calculation
    empty_values = pd.Series([np.NaN]*slow_period)

    #calculate signal line using smoothing value
    signal_calc_values = macd.iloc[slow_period::].reset_index()
    signal_calc_values.drop(['index'], axis = 1, inplace = True)
    signal = pd.concat([empty_values, get_ema(signal_calc_values[0], smoothing)])
    signal = pd.Series(signal.reset_index().drop(['index'], axis = 1)[0])

    #calculate histogram
    histogram = macd - signal

    return macd, signal, histogram

def get_ichimoku_cloud(high, low, close, conversion_period = 9, base_period = 26, leading_period = 52):
    """ This function takes in price data for high, low, close and also conversion, base and leading periods 
    returning conversion and base line also leading and lagging spans"""
    #calculate conversion line using high and low prices of last 9 periods
    conversion_line = (high.rolling(conversion_period).max() + low.rolling(conversion_period).min()) / 2
    #calculate base line using high and low prices of last 26 periods
    base_line = (high.rolling(base_period).max() + low.rolling(base_period).min()) / 2

    #calculate leading span using high and low prices using period of 52
    leading_span_a = ((conversion_line + base_line) / 2).shift(base_period)
    leading_span_b = (high.rolling(leading_period).max() + low.rolling(leading_period).min()) / 2
    leading_span_b = leading_span_b.shift(base_period)

    #calculate lagging span by shifting using base period
    lagging_span = close.shift(-base_period)
    
    return conversion_line, base_line, leading_span_a, leading_span_b, lagging_span

def get_atr(data, period = 14):
    """calculate ATR using high, low, close data and period"""
    
    #separate price data
    high = data['High']
    low = data['Low']
    close = data['Close']

    #create empty series
    atr = pd.Series(0.0, index=data.index)
    #set ATR to closing value
    atr[0] = close[0]

    #for each remaining close data calculate ATR
    for i in range(1, len(close)):
        
        range1 = high[i] - low[i]
        range2 = abs(high[i] - close[i-1])
        range3 = abs(low[i] - close[i-1])
        #using the difference of prices true range takes max value of ranges
        true_range = max(range1, range2, range3)
        atr[i] = ((period - 1) * atr[i-1] + true_range) / period

    return atr

def get_donchian_channels(data, window_size = 20):
    """calculate donchain using closing data and n value of 20 parameters
    returns upper and lower channels and midline"""

    #separate price data
    close = data['Close']

    #calculate upperchannel using max value in window
    upper_channel = close.rolling(window=window_size).max()
    #calculate lowerchannel using min value in window
    lower_channel = close.rolling(window=window_size).min()
    #calculate midline using upper and lower channel /2
    mid_line = (upper_channel + lower_channel) / 2
    
    return upper_channel, lower_channel, mid_line

def get_bollinger_bands(close, window_size=20):
    """calculate bollinger bands using closing price parameters closing price, window size
    returns upper, lower and rolling mean for bollinger bands"""
    #calculate rolling mean of closing price
    rolling_mean = close.rolling(window_size).mean()
    #calculate standard deviation of closing price
    rolling_std = close.rolling(window_size).std()

    #calculate upper band using rolling mean and rolling standard deviation
    upper_band = rolling_mean + (rolling_std * 2)
    #calculate lower band using rolling mean and rolling standard deviation
    lower_band = rolling_mean - (rolling_std * 2)

    return upper_band, rolling_mean, lower_band

def get_rsi(close, period = 14):
    """
    Calculate the Relative Strength Index (RSI) for a given set of price data.
    """
    diff = close.diff(1)
    up_direction = diff.where(diff > 0, 0.0)
    down_direction = -diff.where(diff < 0, 0.0)
    emaup = up_direction.ewm(
        alpha=1 / period, min_periods=period, adjust=False
    ).mean()
    emadn = down_direction.ewm(
        alpha=1 / period, min_periods=period, adjust=False
    ).mean()
    relative_strength = emaup / emadn
    rsi = pd.Series(
        np.where(emadn == 0, 100, 100 - (100 / (1 + relative_strength))),
        index=close.index,
    )
    return rsi

def get_parabolic_sar(data, acceleration=0.02, maximum=0.2):
    length = len(data)
    trend = 0
    sar = data['Close'][0]
    ep = data['Close'][0]
    af = acceleration

    sar_values = [0] * length

    for i in range(1, length):
        if trend == 0:
            sar = sar + af * (ep - sar)
            if data['Close'][i] > sar:
                trend = 1
                ep = data['High'][i]
                sar = min(data['Low'][:i])
            elif data['Close'][i] < sar:
                trend = -1
                ep = data['Low'][i]
                sar = max(data['High'][:i])
        elif trend > 0:
            sar = min(sar + af * (ep - sar), min(data['Low'][i - 1], data['Low'][i]))
            if data['High'][i] > ep:
                ep = data['High'][i]
                af = min(af + acceleration, maximum)
            if data['Close'][i] < sar:
                trend = -1
                sar = ep
                ep = data['Low'][i]
                af = acceleration
        else:
            sar = max(sar + af * (ep - sar), max(data['High'][i - 1], data['High'][i]))
            if data['Low'][i] < ep:
                ep = data['Low'][i]
                af = min(af + acceleration, maximum)
            if data['Close'][i] > sar:
                trend = 1
                sar = ep
                ep = data['High'][i]
                af = acceleration

        sar_values[i] = sar

    return sar_values

def get_williams_r(data, period=14):
    williams_r_values = []

    for i in range(period, len(data)):
        high = max(data['High'][i-period:i])
        low = min(data['Low'][i-period:i])
        current_close = data['Close'][i]
        wr = -100 * ((high - current_close) / (high - low))
        williams_r_values.append(wr)

    return williams_r_values

def get_cci(data, period=20):
    cci_values = []

    for i in range(period, len(data)):
        tp = (data['High'][i] + data['Low'][i] + data['Close'][i]) / 3
        tp_avg = sum(data['High'][i-period:i] + data['Low'][i-period:i] + data['Close'][i-period:i]) / (3 * period)
        md = sum([abs(tp - (data['High'][j] + data['Low'][j] + data['Close'][j]) / 3) for j in range(i-period, i)]) / period
        cci = (tp - tp_avg) / (0.015 * md)
        cci_values.append(cci)

    return cci_values

def get_on_balance_volume(data):
    obv = [0]
    for i in range(1, len(data)):
        if data['Close'][i] > data['Close'][i-1]:
            obv.append(obv[-1] + data['Volume'][i])
        elif data['Close'][i] < data['Close'][i-1]:
            obv.append(obv[-1] - data['Volume'][i])
        else:
            obv.append(obv[-1])
    return obv

def get_accumulation_distribution_line(data):
    adl = [0]
    for i in range(1, len(data)):
        clv = ((data['Close'][i] - data['Low'][i]) - (data['High'][i] - data['Close'][i])) / (data['High'][i] - data['Low'][i]) if data['High'][i] != data['Low'][i] else 0
        adl.append(adl[-1] + (clv * data['Volume'][i]))
   
def get_money_flow_index(data, period=14):
    typical_price = (data['High'] + data['Low'] + data['Close']) / 3
    raw_money_flow = typical_price * data['Volume']
    positive_flow = []
    negative_flow = []

    for i in range(1, len(typical_price)):
        if typical_price[i] > typical_price[i-1]:
            positive_flow.append(raw_money_flow[i])
            negative_flow.append(0)
        elif typical_price[i] < typical_price[i-1]:
            negative_flow.append(raw_money_flow[i])
            positive_flow.append(0)
        else:
            positive_flow.append(0)
            negative_flow.append(0)

    positive_mf = [sum(positive_flow[i-period+1:i+1]) for i in range(period-1, len(positive_flow))]
    negative_mf = [sum(negative_flow[i-period+1:i+1]) for i in range(period-1, len(negative_flow))]
    mfi = [100 - (100 / (1 + (pmf/nmf))) if nmf != 0 else 100 for pmf, nmf in zip(positive_mf, negative_mf)]

    return mfi

def get_chaikin_money_flow(data, period=20):
    money_flow_multiplier = ((data['Close'] - data['Low']) - (data['High'] - data['Close'])) / (data['High'] - data['Low'])
    money_flow_volume = money_flow_multiplier * data['Volume']
    cmf = [money_flow_volume[i-period+1:i+1].sum() / data['Volume'][i-period+1:i+1].sum() for i in range(period-1, len(data))]
    
    return cmf

def get_average_directional_index(data, period=14):
    plus_dm = data['High'].diff()
    minus_dm = data['Low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0

    tr1 = pd.Series(data['High'] - data['Low'])
    tr2 = pd.Series(abs(data['High'] - data['Close'].shift(1)))
    tr3 = pd.Series(abs(data['Low'] - data['Close'].shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = abs(100 * (minus_dm.rolling(window=period).mean() / atr))
    dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
    adx = dx.rolling(window=period).mean()

    return adx

def get_pivot_points(data):
    pivot_point = (data['High'].shift(1) + data['Low'].shift(1) + data['Close'].shift(1)) / 3
    support1 = (pivot_point * 2) - data['High'].shift(1)
    resistance1 = (pivot_point * 2) - data['Low'].shift(1)
    support2 = pivot_point - (data['High'].shift(1) - data['Low'].shift(1))
    resistance2 = pivot_point + (data['High'].shift(1) - data['Low'].shift(1))
    
    return pivot_point, support1, resistance1, support2, resistance2

def get_dmi(data, period=14):
    # Calculate the differences between consecutive highs and lows
    delta_high = data['High'].diff()
    delta_low = data['Low'].diff()

    # Initialize the components of the DMI
    dm_plus = pd.Series([0] * len(data))
    dm_minus = pd.Series([0] * len(data))
    tr = pd.Series([0] * len(data))

    for i in range(1, len(data)):
        # Determine if the movements are positive, negative, or neutral
        if delta_high[i] > delta_low[i] and delta_high[i] > 0:
            dm_plus[i] = delta_high[i]
        if delta_low[i] > delta_high[i] and delta_low[i] > 0:
            dm_minus[i] = delta_low[i]

        # Calculate the True Range
        tr[i] = max(data['High'][i] - data['Low'][i], 
                    abs(data['High'][i] - data['Close'][i-1]), 
                    abs(data['Low'][i] - data['Close'][i-1]))

    # Smooth the True Range and Directional Movements
    atr = tr.rolling(window=period).mean()
    smooth_dm_plus = dm_plus.rolling(window=period).mean()
    smooth_dm_minus = dm_minus.rolling(window=period).mean()

    # Calculate the Directional Indicators
    di_plus = 100 * (smooth_dm_plus / atr)
    di_minus = 100 * (smooth_dm_minus / atr)

    # Calculate the ADX
    dx = (abs(di_plus - di_minus) / abs(di_plus + di_minus)) * 100
    adx = dx.rolling(window=period).mean()

    return di_plus, di_minus, adx

# Sample usage:
# data should be a DataFrame with 'High', 'Low', and 'Close' columns
# For example:
# data = pd.DataFrame({'High': [...], 'Low': [...], 'Close': [...]})
di_plus, di_minus, adx = calculate_dmi(data)
