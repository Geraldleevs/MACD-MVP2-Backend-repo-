import numpy as np
import pandas as pd
import logging
from itertools import combinations
import talib
import time

def dev_print(message, no_print):
    if no_print is False:
        print(message)

# Function to set up logging for performance metrics
def setup_performance_logging():
    logger = logging.getLogger('performance_metrics')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('performance_metrics_logs.csv')
    formatter = logging.Formatter('%(message)s')  # Only log the message
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

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
    slowk, _ = talib.STOCH(df['High'], df['Low'], df['Close'], fastk_period=k_period, slowk_period=3, slowd_period=d_period)
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

# Map indicator functions to their names
indicator_names = {
    use_macd: 'MACD',
    use_sma: 'SMA',
    use_ema: 'EMA',
    use_adx: 'ADX',
    use_aroon: 'Aroon',
    lambda df: use_rsi(df, 70, 30): 'RSI70_30',
    lambda df: use_rsi(df, 71, 31): 'RSI71_31',
    lambda df: use_rsi(df, 72, 32): 'RSI72_32',
    lambda df: use_rsi(df, 73, 33): 'RSI73_33',
    lambda df: use_rsi(df, 74, 34): 'RSI74_34',
    lambda df: use_rsi(df, 75, 35): 'RSI75_35',
    lambda df: use_stochastic(df, 14, 3, 80, 20): 'Stochastic14_3_80_20',
    lambda df: use_stochastic(df, 14, 3, 85, 15): 'Stochastic14_3_85_15',
    lambda df: use_stochastic(df, 10, 3, 80, 20): 'Stochastic10_3_80_20',
    lambda df: use_stochastic(df, 10, 3, 85, 15): 'Stochastic10_3_85_15',
    lambda df: use_stochastic(df, 21, 5, 80, 20): 'Stochastic21_5_80_20',
    lambda df: use_stochastic(df, 21, 5, 85, 15): 'Stochastic21_5_85_15',
    use_cci: 'CCI',
    use_williams_r: 'WilliamsR',
    use_momentum: 'Momentum',
    use_bbands: 'BBands',
    use_atr: 'ATR',
    use_donchian_channel: 'Donchian',
    use_obv: 'OBV',
    use_mfi: 'MFI',
    use_ad: 'AD',
    use_ichimoku: 'Ichimoku',
    use_aroonosc: 'AroonOsc',
    use_dema: 'DEMA',
    use_tema: 'TEMA',
    use_cdl2crows: 'CDL2CROWS',
    use_cdl3blackcrows: 'CDL3BLACKCROWS',
    use_cdl3inside: 'CDL3INSIDE',
    use_adxr: 'ADXR',
    use_apo: 'APO',
    use_bop: 'BOP',
    use_cmo: 'CMO',
    use_dx: 'DX',
    use_macdext: 'MACDEXT',
    use_macdfix: 'MACDFIX',
    use_minus_di: 'MINUS_DI',
    use_minus_dm: 'MINUS_DM',
    use_plus_di: 'PLUS_DI',
    use_plus_dm: 'PLUS_DM',
    use_ppo: 'PPO',
    use_roc: 'ROC',
    use_rocp: 'ROCP',
    use_rocr: 'ROCR',
    use_rocr100: 'ROCR100',
    use_stochf: 'STOCHF',
    use_stochrsi: 'STOCHRSI',
    use_trix: 'TRIX',
    use_ultosc: 'ULTOSC',
    use_ht_trendline: 'HT_TRENDLINE',
    use_kama: 'KAMA',
    use_ma: 'MA',
    use_mama: 'MAMA',
    use_mavp: 'MAVP',
    use_midpoint: 'MIDPOINT',
    use_midprice: 'MIDPRICE',
    use_sar: 'SAR',
    use_sarext: 'SAREXT',
    use_t3: 'T3',
    use_trima: 'TRIMA',
    use_wma: 'WMA'
}

# Performance Metrics Calculation Functions
def calculate_mean_return(returns):
    return np.mean(returns)

def calculate_std_return(returns):
    return np.std(returns)

def calculate_sharpe_ratio(returns, risk_free_rate=0.0):
    mean_return = calculate_mean_return(returns)
    std_return = calculate_std_return(returns)
    return (mean_return - risk_free_rate) / std_return if std_return != 0 else np.nan

def calculate_max_drawdown(returns):
    cumulative_returns = np.cumprod(1 + returns) - 1
    peak = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns - peak) / peak
    return np.min(drawdown)

# Evaluate Strategy Function
def evaluate_strategy(strategy_returns, strategy_name):
    mean_return = calculate_mean_return(strategy_returns)
    std_return = calculate_std_return(strategy_returns)
    sharpe_ratio = calculate_sharpe_ratio(strategy_returns)
    max_drawdown = calculate_max_drawdown(strategy_returns)

    return {
        'Strategy': strategy_name,
        'Mean Return': mean_return,
        'Standard Deviation of Return': std_return,
        'Sharpe Ratio': sharpe_ratio,
        'Maximum Drawdown': max_drawdown
    }

# Define use cases and recommended timeframes with additional combinations
use_cases = {
    ('RSI', 'MACD'): ('Identifying divergences and confirming trend reversals', '1H'),
    ('SMA', 'RSI'): ('Assessing trend direction and pinpointing entry/exit signals', '1D'),
    ('Ichimoku', 'MACD'): ('Holistic trend analysis with momentum confirmation', '4H'),
    ('Donchian', 'ATR'): ('Validating breakouts with volatility measurement', '1D'),
    ('RSI', 'Donchian'): ('Spotting overbought/oversold conditions with breakout verification', '1H'),
    ('SMA', 'ATR'): ('Confirming trend direction and gauging market volatility', '1D'),
    ('Ichimoku', 'RSI'): ('Analyzing trend direction with momentum confirmation', '4H'),
    ('MACD', 'ATR'): ('Confirming momentum with volatility analysis', '1H'),
    ('SMA', 'MACD'): ('Combining trend direction with momentum analysis', '1D'),
    ('Donchian', 'MACD'): ('Confirming breakouts with momentum analysis', '1H'),
    ('Ichimoku', 'ATR'): ('Comprehensive trend analysis with volatility assessment', '4H'),
    ('Stochastic', 'MACD'): ('Momentum confirmation within trending markets', '1H'),
    ('RSI', 'Momentum'): ('Identifying overbought/oversold conditions with momentum shifts', '1H'),
    ('ADX', 'Momentum'): ('Assessing trend strength with momentum confirmation', '1H'),
    ('ADX', 'RSI'): ('Combining trend strength analysis with overbought/oversold conditions', '1H'),
    ('CCI', 'MACD'): ('Validating trend strength with momentum analysis', '1H'),
    ('CCI', 'RSI'): ('Spotting overbought/oversold conditions with trend strength validation', '1H'),
    ('CCI', 'Stochastic'): ('Combining overbought/oversold conditions with momentum analysis', '1H'),
    ('CCI', 'ATR'): ('Trend confirmation with volatility assessment', '1D'),
    ('CCI', 'Donchian'): ('Breakout validation with trend strength analysis', '1H'),
    ('CCI', 'Momentum'): ('Trend strength analysis with momentum confirmation', '1H'),
    ('Donchian', 'Stochastic'): ('Breakout validation within momentum conditions', '1H'),
    ('Donchian', 'Momentum'): ('Combining breakout analysis with momentum confirmation', '1H'),
    ('WilliamsR', 'MACD'): ('Overbought/oversold conditions with momentum validation', '1H'),
    ('WilliamsR', 'RSI'): ('Overbought/oversold conditions with trend strength validation', '1H'),
    ('WilliamsR', 'Stochastic'): ('Combining overbought/oversold conditions with momentum analysis', '1H'),
    ('WilliamsR', 'ATR'): ('Volatility assessment with overbought/oversold conditions', '1D'),
    ('WilliamsR', 'Donchian'): ('Breakout validation with overbought/oversold conditions', '1H'),
    ('WilliamsR', 'Momentum'): ('Overbought/oversold conditions with momentum confirmation', '1H'),
    ('MACD', 'MFI'): ('Momentum validation with money flow analysis', '1H'),
    ('RSI', 'MFI'): ('Overbought/oversold conditions with money flow validation', '1H'),
    ('Stochastic', 'MFI'): ('Combining momentum analysis with money flow validation', '1H'),
    ('ATR', 'MFI'): ('Volatility assessment with money flow analysis', '1D'),
    ('Donchian', 'MFI'): ('Breakout validation with money flow analysis', '1H'),
    ('Momentum', 'MFI'): ('Momentum confirmation with money flow analysis', '1H'),
    ('MACD', 'OBV'): ('Momentum validation with volume confirmation', '1H'),
    ('RSI', 'OBV'): ('Overbought/oversold conditions with volume validation', '1H'),
    ('Stochastic', 'OBV'): ('Combining momentum analysis with volume confirmation', '1H'),
    ('ATR', 'OBV'): ('Volatility assessment with volume analysis', '1D'),
    ('Donchian', 'OBV'): ('Breakout validation with volume confirmation', '1H'),
    ('Momentum', 'OBV'): ('Momentum confirmation with volume analysis', '1H'),
    ('Ichimoku', 'OBV'): ('Holistic trend analysis with volume confirmation', '4H'),
    ('Ichimoku', 'MFI'): ('Holistic trend analysis with money flow validation', '4H'),
    ('Ichimoku', 'WilliamsR'): ('Holistic trend analysis with overbought/oversold conditions', '4H'),
    ('Ichimoku', 'CCI'): ('Holistic trend analysis with trend strength validation', '4H'),
    ('ADX', 'OBV'): ('Trend strength with volume confirmation', '1H'),
    ('ADX', 'MFI'): ('Trend strength with money flow validation', '1H'),
    ('ADX', 'Stochastic'): ('Trend strength with momentum analysis', '1H'),
    ('MACD', 'WilliamsR'): ('Momentum validation with overbought/oversold conditions', '1H'),
    ('SMA', 'Momentum'): ('Trend direction with momentum confirmation', '1H'),
    ('EMA', 'Momentum'): ('Trend direction with exponential smoothing', '1H'),
    ('DEMA', 'TEMA'): ('Comparison of double and triple exponential moving averages', '1H'),
    ('DEMA', 'Momentum'): ('Double exponential smoothing with momentum confirmation', '1H'),
    ('TEMA', 'Momentum'): ('Triple exponential smoothing with momentum confirmation', '1H'),
    ('CDL2CROWS', 'MACD'): ('Bearish reversal pattern with momentum confirmation', '1H'),
    ('CDL3BLACKCROWS', 'RSI'): ('Bearish reversal pattern with overbought/oversold conditions', '1H'),
    ('CDL3INSIDE', 'Stochastic'): ('Reversal pattern with momentum analysis', '1H'),
    ('ADXR', 'APO'): ('Trend strength analysis with absolute price oscillator', '1H'),
    ('BOP', 'CMO'): ('Combining balance of power with momentum oscillator', '1H'),
    ('DX', 'MACDEXT'): ('Directional movement index with extended MACD analysis', '1H'),
    ('MACDFIX', 'MINUS_DI'): ('MACD fix with minus directional indicator', '1H'),
    ('MINUS_DM', 'PLUS_DI'): ('Minus directional movement with plus directional indicator', '1H'),
    ('PLUS_DM', 'PPO'): ('Plus directional movement with percentage price oscillator', '1H'),
    ('ROC', 'ROCP'): ('Rate of change with rate of change percentage', '1H'),
    ('ROCR', 'ROCR100'): ('Rate of change ratio with 100 scale', '1H'),
    ('STOCHF', 'STOCHRSI'): ('Stochastic fast with stochastic RSI', '1H'),
    ('TRIX', 'ULTOSC'): ('Triple exponential average with ultimate oscillator', '1H'),
    ('HT_TRENDLINE', 'KAMA'): ('Hilbert Transform trendline with Kaufman adaptive moving average', '1H'),
    ('MA', 'MAMA'): ('Simple moving average with MESA adaptive moving average', '1H'),
    ('MAVP', 'MIDPOINT'): ('Variable period moving average with midpoint over period', '1H'),
    ('MIDPRICE', 'SAR'): ('Midpoint price over period with parabolic SAR', '1H'),
    ('SAREXT', 'T3'): ('Extended parabolic SAR with triple exponential moving average', '1H'),
    ('TRIMA', 'WMA'): ('Triangular moving average with weighted moving average', '1H'),
    ('BBands', 'ATR'): ('Combining Bollinger Bands and Average True Range for volatility assessment and confirmation of price movements', '1D'),
}

# Define a default use case and timeframe for undefined combinations
default_use_case = ('General trend and momentum analysis', '1H')

# Function to determine the use case and timeframe
def determine_use_case(indicator1, indicator2):
    use_case = use_cases.get((indicator1, indicator2))
    if use_case is None:
        use_case = use_cases.get((indicator2, indicator1))
    if use_case is None:
        use_case = default_use_case
    return use_case

# Example list of files to process
ALL_FILES = [
    # very short term (Added temporarily for quicker live trade, uses 1h files)
    ('Concatenated-BTCUSDT-1h-2023-concatenated.csv', 'BTC', '1min'),
    ('Concatenated-ETHUSDT-1h-2023-concatenated.csv', 'ETH', '1min'),
    ('Concatenated-DOGEUSDT-1h-2023-concatenated.csv', 'DOGE', '1min'),
    # short term - trades are based on hourly closing data
    ('Concatenated-BTCUSDT-1h-2023-concatenated.csv', 'BTC', '1h'),
    ('Concatenated-ETHUSDT-1h-2023-concatenated.csv', 'ETH', '1h'),
    ('Concatenated-DOGEUSDT-1h-2023-concatenated.csv', 'DOGE', '1h'),
    # medium term - trades are based on 4h closing data
    ('Concatenated-BTCUSDT-4h-2023-4-concatenated.csv', 'BTC', '4h'),
    ('Concatenated-ETHUSDT-4h-2023-4-concatenated.csv', 'ETH', '4h'),
    ('Concatenated-DOGEUSDT-4h-2023-4-concatenated.csv', 'DOGE', '4h'),
    # long term - trades are based on daily closing data
    ('Concatenated-BTCUSDT-1d-2023-4-concatenated.csv', 'BTC', '1d'),
    ('Concatenated-ETHUSDT-1d-2023-4-concatenated.csv', 'ETH', '1d'),
    ('Concatenated-DOGEUSDT-1d-2023-4-concatenated.csv', 'DOGE', '1d'),
    # Add other file names as needed
]

def main(token_id='', timeframe='', no_print=True):
    start_time = time.time()

    # Initialize the list to collect all profit DataFrames
    profit_dfs = []

    files = [file for file in ALL_FILES if token_id in file[1] and timeframe in file[2]]

    if len(files) < 1:
        return pd.DataFrame([])

    dev_print(f"Files to process: {len(files)}", no_print)

    # Set up logging for performance metrics
    performance_logger = setup_performance_logging()

    # Read and process all files at once
    dfs = {}
    for (file, coin_id, file_timeframe) in files:
        df = pd.read_csv(f"./data/{file}", usecols=['Open', 'High', 'Low', 'Close', 'Close_time'])
        df['close_time'] = pd.to_datetime(df['Close_time'], unit='ms')
        dfs[(coin_id, file_timeframe)] = df

    dev_print(f"Time to read files: {time.time() - start_time} seconds", no_print)

    # Process each file
    for (file, coin_id, file_timeframe) in files:
        df = dfs[(coin_id, file_timeframe)]
        coin_name = file.split('.')[0]  # Use the file name without extension as the coin name

        # Create a dictionary to store the profits for the current coin
        coin_profits = {}

        # Calculate trading signals for all indicators once
        trading_signals = {name: func(df) for func, name in indicator_names.items()}

        dev_print(f"Time to calculate trading signals for {coin_name}: {time.time() - start_time} seconds", no_print)

        # Generate combinations of indicators, avoiding comparisons of the same type
        indicator_combinations = [
            (name1, name2) for name1, name2 in combinations(indicator_names.values(), 2)
        ]

        for (name1, name2) in indicator_combinations:
            trading_data = df.copy()
            trading_data['buy_sell_1'] = trading_signals[name1]
            trading_data['buy_sell_2'] = trading_signals[name2]

            # Vectorized buy/sell logic
            buy_signals = (trading_data['buy_sell_1'] == 1) & (trading_data['buy_sell_2'] == 1)
            sell_signals = (trading_data['buy_sell_1'] == -1) & (trading_data['buy_sell_2'] == -1)

            positions = np.where(buy_signals, 1, np.where(sell_signals, -1, 0))
            positions = pd.Series(positions).ffill().fillna(0).values

            # Calculate coin holdings and fiat amount
            coin_holdings = 0
            fiat_amount = 10000
            position = False

            for i in range(len(positions)):
                if positions[i] == 1 and not position:
                    coin_holdings = fiat_amount / trading_data['Close'].iloc[i]
                    fiat_amount = 0
                    position = True
                elif positions[i] == -1 and position:
                    fiat_amount = coin_holdings * trading_data['Close'].iloc[i]
                    coin_holdings = 0
                    position = False

            # Final value if still holding coins
            if coin_holdings > 0:
                fiat_amount = coin_holdings * trading_data['Close'].iloc[-1]
                coin_holdings = 0

            strategy_name = f'{name1} & {name2}'
            use_case, timeframe = determine_use_case(name1, name2)

            # Evaluate the strategy performance
            strategy_returns = trading_data['Close'].pct_change().dropna()
            performance_metrics = evaluate_strategy(strategy_returns, strategy_name)

            # Log performance metrics
            for key, value in performance_metrics.items():
                performance_logger.info(f"{coin_name},{strategy_name},{key},{value}")

            coin_profits[f'{strategy_name} ({use_case}, {timeframe})'] = fiat_amount

        coin_profits_df = pd.DataFrame(coin_profits, index=[f'{coin_id} | {file_timeframe}'])
        profit_dfs.append(coin_profits_df)

    # Concatenate all the profit DataFrames into a single DataFrame
    coin_profit_df = pd.concat(profit_dfs)

    dev_print(f"Time to process all files: {time.time() - start_time} seconds", no_print)

    # Determine the best strategy for each coin and other columns in one go
    coin_profit_df = pd.concat([
        coin_profit_df,
        coin_profit_df.idxmax(axis=1).rename('Recommended Strategy'),
        coin_profit_df.max(axis=1).rename('Profit of Recommended Strategy'),
    ], axis=1)

    # Calculate the percentage increase for each coin
    initial_investment = 10000
    coin_profit_df['Percentage Increase'] = ((coin_profit_df['Profit of Recommended Strategy'] - initial_investment) / initial_investment) * 100

    # Keep only the last three columns
    coin_profit_df = coin_profit_df.iloc[:, -3:]

    dev_print(f"Total runtime: {time.time() - start_time} seconds", no_print)

    return coin_profit_df

if __name__ == '__main__':
    result = main(no_print=False)

    # Save the modified DataFrame to a CSV file
    result.to_csv('coin_profit_recommended.csv')

    print(result)
