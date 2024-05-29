# ... [Other utility functions like use_sma, use_ichimoku, etc.]
from TA_calculations import *



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
    
    trading_df = df.copy()
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
    trading_df = df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = (trading_df['sma_diff'] > 0) & (trading_df['prev_sma_diff'] < 0)
    sell_condition = (trading_df['sma_diff'] < 0) & (trading_df['prev_sma_diff'] > 0)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1

    # Clean up df
    df.drop(['sma_50', 'sma_200', 'sma_diff', 'prev_sma_diff'], axis = 1, inplace = True)

    return trading_df

#RSI FUNCTIONS
def use_rsi(df, overbought_thresh, oversold_thresh):
    df['rsi'] = rsi(df.Close)
    df['prev_rsi'] = df['rsi'].shift(1)
    trading_df = df.copy()
    trading_df['buy_sell'] = 0

    buy_condition = (trading_df['rsi'] < oversold_thresh) & (trading_df['prev_rsi'] >= oversold_thresh)
    sell_condition = (trading_df['rsi'] > overbought_thresh) & (trading_df['prev_rsi'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    df.drop(['rsi', 'prev_rsi'], axis=1, inplace=True)
    return trading_df

def use_rsi65_25(df): 
    return use_rsi(df, overbought_thresh=65, oversold_thresh=25)

def use_rsi66_26(df): 
    return use_rsi(df, overbought_thresh=66, oversold_thresh=26)

def use_rsi67_27(df): 
    return use_rsi(df, overbought_thresh=67, oversold_thresh=27)

def use_rsi68_28(df): 
    return use_rsi(df, overbought_thresh=68, oversold_thresh=28)

def use_rsi69_29(df): 
    return use_rsi(df, overbought_thresh=69, oversold_thresh=29)

def use_rsi70_30(df): 
    return use_rsi(df, overbought_thresh=70, oversold_thresh=30)

def use_rsi71_31(df): 
    return use_rsi(df, overbought_thresh=71, oversold_thresh=31)

def use_rsi72_32(df): 
    return use_rsi(df, overbought_thresh=72, oversold_thresh=32)

def use_rsi73_33(df): 
    return use_rsi(df, overbought_thresh=73, oversold_thresh=33)

def use_rsi74_34(df): 
    return use_rsi(df, overbought_thresh=74, oversold_thresh=34)

def use_rsi75_35(df): 
    return use_rsi(df, overbought_thresh=75, oversold_thresh=35)

def use_ichimoku(df):
    df['conversion_line'], df['base_line'], df['leading_span_a'], df['leading_span_b'], df['lagging_span'] = ichimoku_cloud(df.High, df.Low, df.Close)
    df['conversion_base_diff'] = df['conversion_line'] - df['base_line']
    df['prev_diff'] = df['conversion_base_diff'].shift(1)
    
    trading_df = df.copy()
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
    trading_df = df.copy()
    trading_df.loc['buy_sell'] = 0

    buy_condition = trading_df.Close >= trading_df.upper
    trading_df.loc[buy_condition, 'buy_sell'] = 1

    sell_condition = trading_df.Close <= trading_df.lower
    trading_df.loc[sell_condition, 'buy_sell'] = -1
    
    df.drop(['upper', 'lower', 'mid'], axis = 1, inplace = True)
    return trading_df

def use_stochastic_oscillator(df, k_period=14, d_period=3, overbought_thresh=80, oversold_thresh=20):
    df['%K'], df['%D'] = stochastic_oscillator(df['High'], df['Low'], df['Close'], k_period, d_period)
    df['prev_%K'] = df['%K'].shift(1)
    trading_df = df.copy()
    trading_df['buy_sell'] = 0

    buy_condition = (trading_df['%K'] < oversold_thresh) & (trading_df['prev_%K'] >= oversold_thresh)
    sell_condition = (trading_df['%K'] > overbought_thresh) & (trading_df['prev_%K'] <= overbought_thresh)

    trading_df.loc[buy_condition, 'buy_sell'] = 1
    trading_df.loc[sell_condition, 'buy_sell'] = -1

    df.drop(['%K', '%D', 'prev_%K'], axis=1, inplace=True)
    return trading_df

#ALTERNATE Stochastic oscilator functions
def use_stochastic_14_3_80_20(df):
    return use_stochastic_oscillator(df, k_period=14, d_period=3, overbought_thresh=80, oversold_thresh=20)

def use_stochastic_14_3_85_15(df):
    return use_stochastic_oscillator(df, k_period=14, d_period=3, overbought_thresh=85, oversold_thresh=15)

def use_stochastic_10_3_80_20(df):
    return use_stochastic_oscillator(df, k_period=10, d_period=3, overbought_thresh=80, oversold_thresh=20)

def use_stochastic_10_3_85_15(df):
    return use_stochastic_oscillator(df, k_period=10, d_period=3, overbought_thresh=85, oversold_thresh=15)

def use_stochastic_21_5_80_20(df):
    return use_stochastic_oscillator(df, k_period=21, d_period=5, overbought_thresh=80, oversold_thresh=20)

def use_stochastic_21_5_85_15(df):
    return use_stochastic_oscillator(df, k_period=21, d_period=5, overbought_thresh=85, oversold_thresh=15)
