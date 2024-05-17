import numpy as np
import pandas as pd
import tkinter as tk
from itertools import combinations
import logging

# Data placeholder DF
#read BTCUSDT data file
df = pd.read_csv('data/BTCUSDT_data.csv')
#drop unamed and index columns
df.drop(["Unnamed: 0", "index"], axis = 1, inplace = True)

# Function Definitions
# --------------------

def sma(close, period):
    """Calculate Simple Moving Average."""
    ma = close.rolling(period).mean()
    return pd.Series(ma)

def ema(close, period):
    """ This function takes closing price and period and returns exponential moving average"""

    #calculate Multiplier (smoothing factor)
    multiplier = 2 / (period + 1)
    #calculate Simple Moving Average
    ma = sma(close, period)
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

def macd(close, fast_period = 12, slow_period = 26, smoothing = 9):
    """ This function takes in closing price, a period of 12 and 26 and a smoothing value and returns"""

    #calculate MACD using the difference of EMA periods 12 and 26
    macd = ema(close, 12) - ema(close, 26)
    #create series for signal calculation
    empty_values = pd.Series([np.NaN]*slow_period)

    #calculate signal line using smoothing value
    signal_calc_values = macd.iloc[slow_period::].reset_index()
    signal_calc_values.drop(['index'], axis = 1, inplace = True)
    signal = pd.concat([empty_values, ema(signal_calc_values[0], smoothing)])
    signal = pd.Series(signal.reset_index().drop(['index'], axis = 1)[0])

    #calculate histogram
    histogram = macd - signal

    return macd, signal, histogram

def ichimoku_cloud(high, low, close, conversion_period = 9, base_period = 26, leading_period = 52):
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

def calculate_atr(data, period = 14):
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
def atr(high, low, close, period=14):
    """Calculate the Average True Range (ATR) for a given period."""
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

def use_atr(df, period=14):
    """Generate buy/sell signals based on ATR."""
    df['ATR'] = atr(df['High'], df['Low'], df['Close'], period)
    
    # Define buy/sell conditions based on ATR (modify as needed)
    # For this example, we'll use a simple breakout strategy
    buy_condition = df['Close'] > df['Close'].shift() + df['ATR'].shift()
    sell_condition = df['Close'] < df['Close'].shift() - df['ATR'].shift()
    
    df['buy_sell'] = 0
    df.loc[buy_condition, 'buy_sell'] = 1
    df.loc[sell_condition, 'buy_sell'] = -1
    
    return df

def calculate_donchian_channels(data, window_size = 20):
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

def rsi(close, number_of_periods=14):
    """ calculate RSI using closing price and number of periods
    returns RSI"""

    #initialise deltas, seed, up, down
    deltas = np.diff(close)
    seed = deltas[:number_of_periods+1]
    up = seed[seed >= 0].sum()/number_of_periods
    down = -seed[seed < 0].sum()/number_of_periods

    #calculate first RSI value
    rs = up/down
    rsi = np.zeros_like(close)
    rsi[:number_of_periods] = 100. - 100./(1.+rs)

    #calculate RSI for remaining number of periods
    for i in range(number_of_periods, len(close)):
        delta = deltas[i-1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
            
        #calculate average for up and down moves
        up = (up*(number_of_periods-1) + upval)/number_of_periods
        down = (down*(number_of_periods-1) + downval)/number_of_periods
        #calculate RSI for current period
        rs = up/down
        rsi[i] = 100. - 100./(1.+rs)

    return rsi

def bollinger_bands(close, window_size=20):
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

def fibonacci_retracement(close, open):
    """calculate fibonacci retracement using close and open price
    returns fibonacci retracement in separate dataframe"""
    #fibonacci levels
    fib_levels = [0, 0.236, 0.382, 0.5, 0.618, 0.764, 1.0]

    diff = close - open
    #list comprehension
    levels = np.array([close - level * diff for level in fib_levels])
    df = pd.DataFrame(levels.T, columns=[f"Fibonacci {int(level*100)}%" for level in fib_levels])
    return df

def stochastic_oscillator(high, low, close, k_period=14, d_period=3):
    """Calculate the Stochastic Oscillator."""
    low_min = low.rolling(window=k_period).min()
    high_max = high.rolling(window=k_period).max()
    
    K = ((close - low_min) / (high_max - low_min)) * 100
    D = K.rolling(window=d_period).mean()
    
    return K, D

# Utility Functions for Trading Strategies
# ----------------------------------------
def buy(trading_data, buy_type, fiat_amount):  
    trading_data = trading_data[(trading_data['buy_sell'] == 1) | (trading_data['buy_sell'] == -1)]
    if buy_type == 'all':
        position = False
        coin = 0
        for idx, row in trading_data.iterrows():
            if (row['buy_sell'] == 1) & (position == False):
                position = True
                coin = fiat_amount / row['Close']
                print("Bought {} with {}".format(coin, fiat_amount))
                fiat_amount = 0
                
            elif (row['buy_sell'] == -1) & (position == True):
                fiat_amount = coin * row['Close']
                print("Sold {} for {}".format(coin, fiat_amount))
                coin = 0
                position = False
        fiat_amount += coin * trading_data.iloc[-1, 5]
        coin = 0
    
    if buy_type == 'consec':
        position = False
        fiat_buy = fiat_amount / 4
        coin = 0
        for idx, row in trading_data.iterrows():
            if (row['buy_sell'] == 1) & (fiat_amount > fiat_buy):
                position = True
                coin += fiat_buy / row['Close']
                print("Bought {} with {}".format(coin, fiat_amount))
                fiat_amount -= fiat_buy
            elif (row['buy_sell'] == 1) & (fiat_amount < fiat_buy) & (fiat_amount > 0):
                position = True
                coin += fiat_amount / row['Close']
                print("Bought {} with {}".format(coin, fiat_amount))
                fiat_amount = 0 
            elif (row['buy_sell'] == -1) & (position == True):
                fiat_amount += coin * row['Close']
                print("Sold {} for {}".format(coin, fiat_amount))
                coin = 0
                fiat_buy = fiat_amount / 4
                position = False
        fiat_amount += coin * trading_data.iloc[-1, 5]
        coin = 0
    return fiat_amount


# ... [Other utility functions like use_sma, use_ichimoku, etc.]
def use_atr(df, period=14):
    """Generate buy/sell signals based on ATR."""
    df['ATR'] = atr(df['High'], df['Low'], df['Close'], period)
    
    # Define buy/sell conditions based on ATR (modify as needed)
    # For this example, we'll use a simple breakout strategy
    buy_condition = df['Close'] > df['Close'].shift() + df['ATR'].shift()
    sell_condition = df['Close'] < df['Close'].shift() - df['ATR'].shift()
    
    df['buy_sell'] = 0
    df.loc[buy_condition, 'buy_sell'] = 1
    df.loc[sell_condition, 'buy_sell'] = -1
    
    return df

def use_macd(df):
    df['macd'], df['signal'], df['histogram'] = macd(df.Close)
    df['prev_histogram'] = df['histogram'].shift(1)
    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition_1 = (trading_df['prev_histogram'] < 0) & (trading_df['histogram'] > 0) 
    buy_condition_2 = (trading_df['macd'] < 0) & (trading_df['signal'] < 0)
    
    trading_df.loc[buy_condition_1 & buy_condition_2, 'buy_sell'] = 1

    sell_signal_1 = (trading_df['prev_histogram'] > 0) & (trading_df['histogram'] < 0) 
    sell_signal_2 = (trading_df['macd'] > 0) & (trading_df['signal'] > 0)

    trading_df.loc[sell_signal_1 & sell_signal_2, 'buy_sell'] = -1

    #Clean up df
    df.drop(['macd', 'signal', 'histogram', 'prev_histogram'], axis = 1, inplace = True)

    return trading_df

def use_sma(df):
    df['sma_50'] = sma(df.Close, 50)
    df['sma_200'] = sma(df.Close, 200)
    df['sma_diff'] = df['sma_50'] - df['sma_200']
    df['prev_sma_diff'] = df['sma_diff'].shift(1)
    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['sma_diff'] > 0) & (trading_df['prev_sma_diff'] < 0)
    sell_condition = (trading_df['sma_diff'] < 0) & (trading_df['prev_sma_diff'] > 0)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1

    # Clean up df
    df.drop(['sma_50', 'sma_200', 'sma_diff', 'prev_sma_diff'], axis = 1, inplace = True)

    return trading_df

def use_rsi70_30(df, overbought_thresh = 70, oversold_thresh = 30):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis = 1, inplace = True)
    return trading_df
#ALTERNATIVE RSI FUNCTIONS
def use_rsi65_25(df, overbought_thresh=65, oversold_thresh=25):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis = 1, inplace = True)
    return trading_df
def use_rsi66_26(df, overbought_thresh=66, oversold_thresh=26):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis = 1, inplace = True)
    return trading_df
def use_rsi67_27(df, overbought_thresh=67, oversold_thresh=27):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis = 1, inplace = True)
    return trading_df
def use_rsi68_28(df, overbought_thresh=68, oversold_thresh=28):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis = 1, inplace = True)
    return trading_df
def use_rsi69_29(df, overbought_thresh=69, oversold_thresh=29):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis = 1, inplace = True)
    return trading_df
def use_rsi70_30(df, overbought_thresh=70, oversold_thresh=30):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis = 1, inplace = True)
    return trading_df
def use_rsi71_31(df, overbought_thresh=71, oversold_thresh=31):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis = 1, inplace = True)
    return trading_df
def use_rsi72_32(df, overbought_thresh=72, oversold_thresh=32):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis = 1, inplace = True)
    return trading_df
def use_rsi73_33(df, overbought_thresh=73, oversold_thresh=33):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis = 1, inplace = True)
    return trading_df
def use_rsi74_34(df, overbought_thresh=74, oversold_thresh=34):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis = 1, inplace = True)
    return trading_df
def use_rsi75_35(df, overbought_thresh=75, oversold_thresh=35):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)

    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    # Clean up df
    df.drop(['rsi', 'prev_rsi'], axis=1, inplace=True)
    return trading_df


def use_ichimoku(df):
    df['conversion_line'], df['base_line'], df['leading_span_a'], df['leading_span_b'], df['lagging_span'] = ichimoku_cloud(df.High, df.Low, df.Close)
    df['conversion_base_diff'] = df['conversion_line'] - df['base_line']
    df['prev_diff'] = df['conversion_base_diff'].shift(1)
    
    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition_1 = trading_df.Close >= np.maximum(trading_df['leading_span_a'], trading_df['leading_span_b'])
    buy_condition_2 = (trading_df['conversion_base_diff'] > 0) & (trading_df['prev_diff'] < 0)
    trading_df.loc[buy_condition_1 & buy_condition_2, 'buy_sell'] = 1

    sell_condition_1 = trading_df.Close < np.minimum(trading_df['leading_span_a'], trading_df['leading_span_b'])
    sell_condition_2 = (trading_df['conversion_base_diff'] < 0) & (trading_df['prev_diff'] > 0)
    trading_df.loc[sell_condition_1 & sell_condition_2, 'buy_sell'] = -1

    # Clean up df
    df.drop(['conversion_line', 'base_line', 'leading_span_a', 'leading_span_b', 'lagging_span', 'conversion_base_diff', 'prev_diff'], axis = 1, inplace = True)
    return trading_df

def use_donchian_channel(df):
    df['upper'], df['lower'], df['mid'] = calculate_donchian_channels(df)
    trading_df = df[(df.Time >= '2022-12-01 00:00:00') & (df.Time <= '2023-02-01 23:59:00')]
    trading_df = trading_df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = trading_df.Close >= trading_df.upper
    trading_df.loc[buy_condition, 'buy_sell'] = 1

    sell_condition = trading_df.Close <= trading_df.lower
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    
    df.drop(['upper', 'lower', 'mid'], axis = 1, inplace = True)
    return trading_df

def use_stochastic(df, k_period=14, d_period=3):
    """Generate buy/sell signals based on the Stochastic Oscillator."""
    df['%K'], df['%D'] = stochastic_oscillator(df['High'], df['Low'], df['Close'], k_period, d_period)
    
    # Define buy/sell conditions based on Stochastic Oscillator
    buy_condition = (df['%K'].shift() < 20) & (df['%K'] > df['%D']) & (df['%K'] > 20)
    sell_condition = (df['%K'].shift() > 80) & (df['%K'] < df['%D']) & (df['%K'] < 80)
    
    df['buy_sell'] = 0
    df.loc[buy_condition, 'buy_sell'] = 1
    df.loc[sell_condition, 'buy_sell'] = -1
    
    return df
#Test functions
atr_test = use_atr(df)
atr_test[(atr_test['buy_sell'] == 1) | (atr_test['buy_sell'] == -1)]

macd_test = use_macd(df)
macd_test[(macd_test['buy_sell'] == 1) | (macd_test['buy_sell'] == -1)]

sma_test = use_sma(df)
sma_test[(sma_test['buy_sell'] == 1) | (sma_test['buy_sell'] == -1)]

rsi_test = use_rsi70_30(df)
rsi_test[(rsi_test['buy_sell'] == 1) | (rsi_test['buy_sell'] == -1)]

ichimoku_test = use_ichimoku(df)
ichimoku_test[(ichimoku_test['buy_sell'] == 1) | (ichimoku_test['buy_sell'] == -1)]

donchian_test = use_donchian_channel(df)
donchian_test[(donchian_test['buy_sell'] == 1) | (donchian_test['buy_sell'] == -1)]

SO_test = use_stochastic(df)
SO_test[(SO_test['buy_sell'] == 1) | (SO_test['buy_sell'] == -1)]

# Set up logging
logging.basicConfig(filename='trade_logs.log', level=logging.INFO, format='%(asctime)s - %(message)s')
coin_profit_df = pd.DataFrame()

# Create an empty DataFrame to store the trades log
trades_log = pd.DataFrame(columns=['Coin', 'Strategy', 'Buy/Sell', 'Price'])

# Assuming filesyear and indicators are defined elsewhere or in previous cells
#indicators = [use_macd, use_rsi, use_sma]
#to use non custom parameter rsi use 'use_rsi'
indicators = [
    use_macd,
    use_sma,
    use_ichimoku,
    use_donchian_channel,
    use_atr,
    use_rsi65_25,
    use_rsi66_26,
    use_rsi67_27,
    use_rsi68_28,
    use_rsi69_29,
    use_rsi70_30,
    use_rsi71_31,
    use_rsi72_32,
    use_rsi73_33,
    use_rsi74_34,
    use_rsi75_35
]

filesfull = ['BTCUSDT_full.csv', 'ETHUSDT_full.csv', 'DOGEUSDT_full.csv', 'LINKUSDT_full.csv']
filesyrbtc = ['BTCUSDT_data.csv']
filesyear = ['BTCUSDT_data.csv', 'ETHUSDT_data.csv','DOGEUSDT_data.csv', 'LINKUSDT_data.csv']

# Initialization
coin_profit_df = pd.DataFrame()


# Generate column names based on indicator combinations
strategy_columns = ['{} & {}'.format(indicators[i].__name__, indicators[j].__name__) 
                    for i in range(len(indicators)) 
                    for j in range(i + 1, len(indicators))]

# Initialize the DataFrame with the strategy columns
coin_profit_df = pd.DataFrame(columns=strategy_columns)

for file in filesyear:
    df = pd.read_csv("./data/{}".format(file))
    coin_name = file[0:3]
    
    # Log the coin being processed
    logging.info(f"Processing Coin: {coin_name}")
    
    # Create a dictionary to store the profits for the current coin
    coin_profits = {}
    
    for i in range(len(indicators)):
        
        for j in range(i + 1, len(indicators)):
            trading_frame_1 = indicators[i](df)
            trading_frame_2 = indicators[j](df)
            trading_data = df.copy()
            trading_data['buy_sell_1'] = trading_frame_1.iloc[:, -1]
            trading_data['buy_sell_2'] = trading_frame_2.iloc[:, -1]

            position = False
            coin = 0
            fiat_amount = 10000
            for idx, row in trading_data.iterrows():
                if (row['buy_sell_1'] == 1) and (row['buy_sell_2'] == 1) and (position == False):
                    position = True
                    coin = fiat_amount / row['Close']
                    fiat_amount = 0

                    # Log the trade
                    trade_message = f"  BUY: Strategy={indicators[i].__name__} & {indicators[j].__name__}, Price={row['Close']}"
                    logging.info(trade_message)

                elif ((row['buy_sell_1'] == -1) and (row['buy_sell_2'] == -1)) and (position == True):
                    fiat_amount = coin * row['Close']
                    coin = 0
                    position = False

                    # Log the trade
                    trade_message = f"  SELL: Strategy={indicators[i].__name__} & {indicators[j].__name__}, Price={row['Close']}"
                    logging.info(trade_message)

            fiat_amount += coin * trading_data.iloc[-1, 5]
            coin = 0

            # Store the profit for the current coin and strategy
            coin_profits['{} & {}'.format(indicators[i].__name__, indicators[j].__name__)] = fiat_amount

            # Log the completion of the strategy execution with a new line for clarity
            logging.info(f"Completed Strategy: {indicators[i].__name__} & {indicators[j].__name__}, Coin: {coin_name}, Profit: {fiat_amount}\n")


    # Assign the coin_profits dictionary directly to a row in coin_profit_df
    coin_profit_df.loc[coin_name] = coin_profits
    print(coin_profit_df.loc[coin_name], "\n")

# Determine the best strategy for each coin
coin_profit_df['Recommended Strategy'] = coin_profit_df.idxmax(axis=1)

# Cell 3: Save the trades log to a CSV file
coin_profit_df.to_csv('coin_profit.csv')


