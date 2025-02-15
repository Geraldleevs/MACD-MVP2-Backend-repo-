import aiohttp
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime
import time
import os
from typing import List, Dict
import talib

def dev_print(message, no_print):
    if no_print is False:
        print(message)

async def fetch_ohlc_data(session, pair, interval, since=None):
    url = 'https://api.kraken.com/0/public/OHLC'
    params = {'pair': pair, 'interval': interval}
    
    if since:
        params['since'] = since

    async with session.get(url, params=params) as response:
        if response.status == 200:
            data = await response.json()
            if data['error']:
                return None, None
            else:
                result = data['result']
                last_timestamp = int(result['last'])
                ohlc_data = []
                for key in result:
                    if key != 'last':
                        for entry in result[key]:
                            timestamp = int(entry[0])
                            timestamp_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                            ohlc_data.append({
                                'Unix_Timestamp': timestamp,
                                'Timestamp': timestamp_str,
                                'Open': float(entry[1]),
                                'High': float(entry[2]),
                                'Low': float(entry[3]),
                                'Close': float(entry[4]),
                                'Volume': float(entry[5]),
                                'Count': float(entry[6])  
                            })
                return ohlc_data, last_timestamp
        else:
            return None, None

def apply_ta_indicators(df, no_print = True):
    start_time = time.time()
    new_columns = {}

    # MACD
    macd, macd_signal, macd_hist = talib.MACD(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    new_columns['MACD'] = macd
    new_columns['MACD_Signal'] = macd_signal
    new_columns['MACD_Hist'] = macd_hist
    new_columns['indicator_macd'] = np.where(macd > macd_signal, 1, -1)

    # SMA
    sma = talib.SMA(df['Close'], timeperiod=30)
    new_columns['SMA'] = sma
    new_columns['indicator_sma'] = np.where(df['Close'] > sma, 1, -1)

    # EMA
    ema = talib.EMA(df['Close'], timeperiod=30)
    new_columns['EMA'] = ema
    new_columns['indicator_ema'] = np.where(df['Close'] > ema, 1, -1)

    # ADX
    adx = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=14)
    new_columns['ADX'] = adx
    new_columns['indicator_adx'] = np.where(adx > 25, 1, -1)

    # Aroon
    aroon_up, aroon_down = talib.AROON(df['High'], df['Low'], timeperiod=14)
    new_columns['Aroon_Up'] = aroon_up
    new_columns['Aroon_Down'] = aroon_down
    new_columns['indicator_aroon'] = np.where(aroon_up > aroon_down, 1, -1)

    # RSI variations
    for overbought, oversold in zip(range(70, 76), range(30, 36)):
        rsi = talib.RSI(df['Close'], timeperiod=14)
        col_name = f'RSI{overbought}_{oversold}'
        new_columns[col_name] = rsi
        new_columns[f'indicator_{col_name.lower()}'] = np.where(rsi > overbought, -1, np.where(rsi < oversold, 1, 0))

    # Stochastic variations
    stochastic_params = [
        (14, 3, 80, 20),
        (14, 3, 85, 15),
        (10, 3, 80, 20),
        (10, 3, 85, 15),
        (21, 5, 80, 20),
        (21, 5, 85, 15)
    ]
    for k_period, d_period, overbought, oversold in stochastic_params:
        slowk, _ = talib.STOCH(df['High'], df['Low'], df['Close'], fastk_period=k_period, slowk_period=3, slowd_period=d_period)
        col_name = f'Stochastic_{k_period}_{d_period}_{overbought}_{oversold}'
        new_columns[col_name] = slowk
        new_columns[f'indicator_{col_name.lower()}'] = np.where(slowk > overbought, -1, np.where(slowk < oversold, 1, 0))

    # Add the remaining indicators similarly
    # CCI
    cci = talib.CCI(df['High'], df['Low'], df['Close'], timeperiod=14)
    new_columns['CCI'] = cci
    new_columns['indicator_cci'] = np.where(cci > 100, -1, np.where(cci < -100, 1, 0))

    # Williams %R
    willr = talib.WILLR(df['High'], df['Low'], df['Close'], timeperiod=14)
    new_columns['WilliamsR'] = willr
    new_columns['indicator_williamsr'] = np.where(willr < -80, 1, np.where(willr > -20, -1, 0))

    # Momentum
    mom = talib.MOM(df['Close'], timeperiod=10)
    new_columns['Momentum'] = mom
    new_columns['indicator_momentum'] = np.where(mom > 0, 1, -1)

    # Bollinger Bands
    upperband, middleband, lowerband = talib.BBANDS(df['Close'], timeperiod=20)
    new_columns['UpperBand'] = upperband
    new_columns['MiddleBand'] = middleband
    new_columns['LowerBand'] = lowerband
    new_columns['indicator_bbands'] = np.where(df['Close'] > upperband, -1, np.where(df['Close'] < lowerband, 1, 0))

    # ATR
    atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
    new_columns['ATR'] = atr
    new_columns['indicator_atr'] = np.where(atr > atr.shift(1), 1, -1)

    # OBV
    if 'Volume' in df.columns:
        obv = talib.OBV(df['Close'], df['Volume'])
        new_columns['OBV'] = obv
        new_columns['indicator_obv'] = np.where(obv > obv.shift(1), 1, -1)
    else:
        new_columns['OBV'] = np.zeros(len(df))
        new_columns['indicator_obv'] = np.zeros(len(df))

    # MFI
    if 'Volume' in df.columns:
        mfi = talib.MFI(df['High'], df['Low'], df['Close'], df['Volume'], timeperiod=14)
        new_columns['MFI'] = mfi
        new_columns['indicator_mfi'] = np.where(mfi > 80, -1, np.where(mfi < 20, 1, 0))
    else:
        new_columns['MFI'] = np.zeros(len(df))
        new_columns['indicator_mfi'] = np.zeros(len(df))

    # AD
    if 'Volume' in df.columns:
        ad = talib.AD(df['High'], df['Low'], df['Close'], df['Volume'])
        new_columns['AD'] = ad
        new_columns['indicator_ad'] = np.where(ad > ad.shift(1), 1, -1)
    else:
        new_columns['AD'] = np.zeros(len(df))
        new_columns['indicator_ad'] = np.zeros(len(df))

    # Ichimoku
    tenkan_sen = (df['High'].rolling(window=9).max() + df['Low'].rolling(window=9).min()) / 2
    kijun_sen = (df['High'].rolling(window=26).max() + df['Low'].rolling(window=26).min()) / 2
    new_columns['Tenkan_Sen'] = tenkan_sen
    new_columns['Kijun_Sen'] = kijun_sen
    new_columns['indicator_ichimoku'] = np.where(tenkan_sen > kijun_sen, 1, -1)

    # Aroon Oscillator
    aroonosc = talib.AROONOSC(df['High'], df['Low'], timeperiod=14)
    new_columns['AroonOsc'] = aroonosc
    new_columns['indicator_aroonosc'] = np.where(aroonosc > 0, 1, -1)

    # DEMA
    dema = talib.DEMA(df['Close'], timeperiod=30)
    new_columns['DEMA'] = dema
    new_columns['indicator_dema'] = np.where(df['Close'] > dema, 1, -1)

    # TEMA
    tema = talib.TEMA(df['Close'], timeperiod=30)
    new_columns['TEMA'] = tema
    new_columns['indicator_tema'] = np.where(df['Close'] > tema, 1, -1)

    # ADXR
    adxr = talib.ADXR(df['High'], df['Low'], df['Close'], timeperiod=14)
    new_columns['ADXR'] = adxr
    new_columns['indicator_adxr'] = np.where(adxr > 25, 1, -1)

    # APO
    apo = talib.APO(df['Close'], fastperiod=12, slowperiod=26)
    new_columns['APO'] = apo
    new_columns['indicator_apo'] = np.where(apo > 0, 1, -1)

    # BOP
    bop = talib.BOP(df['Open'], df['High'], df['Low'], df['Close'])
    new_columns['BOP'] = bop
    new_columns['indicator_bop'] = np.where(bop > 0, 1, -1)

    # CMO
    cmo = talib.CMO(df['Close'], timeperiod=14)
    new_columns['CMO'] = cmo
    new_columns['indicator_cmo'] = np.where(cmo > 0, 1, -1)

    # DX
    dx = talib.DX(df['High'], df['Low'], df['Close'], timeperiod=14)
    new_columns['DX'] = dx
    new_columns['indicator_dx'] = np.where(dx > 25, 1, -1)

    # MACDEXT
    macdext, macdext_signal, _ = talib.MACDEXT(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    new_columns['MACDEXT'] = macdext
    new_columns['MACDEXT_Signal'] = macdext_signal
    new_columns['indicator_macdext'] = np.where(macdext > macdext_signal, 1, -1)

    # MACDFIX
    macdfix, macdfix_signal, _ = talib.MACDFIX(df['Close'], signalperiod=9)
    new_columns['MACDFIX'] = macdfix
    new_columns['MACDFIX_Signal'] = macdfix_signal
    new_columns['indicator_macdfix'] = np.where(macdfix > macdfix_signal, 1, -1)

    # MINUS_DI
    minus_di = talib.MINUS_DI(df['High'], df['Low'], df['Close'], timeperiod=14)
    new_columns['MINUS_DI'] = minus_di
    new_columns['indicator_minus_di'] = np.where(minus_di > 25, 1, -1)

    # MINUS_DM
    minus_dm = talib.MINUS_DM(df['High'], df['Low'], timeperiod=14)
    new_columns['MINUS_DM'] = minus_dm
    new_columns['indicator_minus_dm'] = np.where(minus_dm > 0, 1, -1)

    # PLUS_DI
    plus_di = talib.PLUS_DI(df['High'], df['Low'], df['Close'], timeperiod=14)
    new_columns['PLUS_DI'] = plus_di
    new_columns['indicator_plus_di'] = np.where(plus_di > 25, 1, -1)

    # PLUS_DM
    plus_dm = talib.PLUS_DM(df['High'], df['Low'], timeperiod=14)
    new_columns['PLUS_DM'] = plus_dm
    new_columns['indicator_plus_dm'] = np.where(plus_dm > 0, 1, -1)

    # PPO
    ppo = talib.PPO(df['Close'], fastperiod=12, slowperiod=26)
    new_columns['PPO'] = ppo
    new_columns['indicator_ppo'] = np.where(ppo > 0, 1, -1)

    # ROC
    roc = talib.ROC(df['Close'], timeperiod=10)
    new_columns['ROC'] = roc
    new_columns['indicator_roc'] = np.where(roc > 0, 1, -1)

    # ROCP
    rocp = talib.ROCP(df['Close'], timeperiod=10)
    new_columns['ROCP'] = rocp
    new_columns['indicator_rocp'] = np.where(rocp > 0, 1, -1)

    # ROCR
    rocr = talib.ROCR(df['Close'], timeperiod=10)
    new_columns['ROCR'] = rocr
    new_columns['indicator_rocr'] = np.where(rocr > 0, 1, -1)

    # ROCR100
    rocr100 = talib.ROCR100(df['Close'], timeperiod=10)
    new_columns['ROCR100'] = rocr100
    new_columns['indicator_rocr100'] = np.where(rocr100 > 100, 1, -1)

    # STOCHF
    fastk, fastd = talib.STOCHF(df['High'], df['Low'], df['Close'], fastk_period=14, fastd_period=3)
    new_columns['STOCHF_K'] = fastk
    new_columns['STOCHF_D'] = fastd
    new_columns['indicator_stochf'] = np.where(fastk > fastd, 1, -1)

    # STOCHRSI
    fastk, fastd = talib.STOCHRSI(df['Close'], timeperiod=14, fastk_period=14, fastd_period=3)
    new_columns['STOCHRSI_K'] = fastk
    new_columns['STOCHRSI_D'] = fastd
    new_columns['indicator_stochrsi'] = np.where(fastk > fastd, 1, -1)

    # TRIX
    trix = talib.TRIX(df['Close'], timeperiod=30)
    new_columns['TRIX'] = trix
    new_columns['indicator_trix'] = np.where(trix > 0, 1, -1)

    # ULTOSC
    ultosc = talib.ULTOSC(df['High'], df['Low'], df['Close'], timeperiod1=7, timeperiod2=14, timeperiod3=28)
    new_columns['ULTOSC'] = ultosc
    new_columns['indicator_ultosc'] = np.where(ultosc > 50, 1, -1)

    # HT_TRENDLINE
    ht_trendline = talib.HT_TRENDLINE(df['Close'])
    new_columns['HT_TRENDLINE'] = ht_trendline
    new_columns['indicator_ht_trendline'] = np.where(df['Close'] > ht_trendline, 1, -1)

    # KAMA
    kama = talib.KAMA(df['Close'], timeperiod=30)
    new_columns['KAMA'] = kama
    new_columns['indicator_kama'] = np.where(df['Close'] > kama, 1, -1)

    # MA
    ma = talib.MA(df['Close'], timeperiod=30)
    new_columns['MA'] = ma
    new_columns['indicator_ma'] = np.where(df['Close'] > ma, 1, -1)

    # MAMA
    mama, fama = talib.MAMA(df['Close'])
    new_columns['MAMA'] = mama
    new_columns['FAMA'] = fama
    new_columns['indicator_mama'] = np.where(mama > fama, 1, -1)

    # MAVP
    mavp = talib.MAVP(df['Close'], df['High'], minperiod=2, maxperiod=30)
    new_columns['MAVP'] = mavp
    new_columns['indicator_mavp'] = np.where(df['Close'] > mavp, 1, -1)

    # MIDPOINT
    midpoint = talib.MIDPOINT(df['Close'], timeperiod=14)
    new_columns['MIDPOINT'] = midpoint
    new_columns['indicator_midpoint'] = np.where(df['Close'] > midpoint, 1, -1)

    # MIDPRICE
    midprice = talib.MIDPRICE(df['High'], df['Low'], timeperiod=14)
    new_columns['MIDPRICE'] = midprice
    new_columns['indicator_midprice'] = np.where(df['Close'] > midprice, 1, -1)

    # SAR
    sar = talib.SAR(df['High'], df['Low'], acceleration=0.02, maximum=0.2)
    new_columns['SAR'] = sar
    new_columns['indicator_sar'] = np.where(df['Close'] > sar, 1, -1)

    # SAREXT
    sarext = talib.SAREXT(df['High'], df['Low'])
    new_columns['SAREXT'] = sarext
    new_columns['indicator_sarext'] = np.where(df['Close'] > sarext, 1, -1)

    # T3
    t3 = talib.T3(df['Close'], timeperiod=30)
    new_columns['T3'] = t3
    new_columns['indicator_t3'] = np.where(df['Close'] > t3, 1, -1)

    # TRIMA
    trima = talib.TRIMA(df['Close'], timeperiod=30)
    new_columns['TRIMA'] = trima
    new_columns['indicator_trima'] = np.where(df['Close'] > trima, 1, -1)

    # WMA
    wma = talib.WMA(df['Close'], timeperiod=30)
    new_columns['WMA'] = wma
    new_columns['indicator_wma'] = np.where(df['Close'] > wma, 1, -1)

    # Add all the new columns to the DataFrame at once
    df = pd.concat([df, pd.DataFrame(new_columns)], axis=1)

    end_time = time.time()
    dev_print(f"TA indicators applied in {end_time - start_time:.2f} seconds", no_print)
    return df

async def process_interval(session, pair, interval, since=None, no_print=True):
    ohlc_data, last_timestamp = await fetch_ohlc_data(session, pair, interval, since)

    if ohlc_data:
        df = pd.DataFrame(ohlc_data)
        df = apply_ta_indicators(df, no_print)
        return df
    return None

async def apply_backtest(pairs: List[str], intervals: List[int], since: datetime = None, no_print=True) -> Dict[str, Dict[str, pd.DataFrame]]:
    since_timestamp = since.timestamp() if since else None
    results = {}

    async with aiohttp.ClientSession() as session:
        tasks = [process_interval(session, pair, interval, since_timestamp, no_print) for pair in pairs for interval in intervals]
        raw_data = await asyncio.gather(*tasks)

        for i, pair in enumerate(pairs):
            pair_data = {}
            for j, interval in enumerate(intervals):
                df = raw_data[i * len(intervals) + j]
                if df is not None:
                    pair_data[str(interval)] = df
            results[pair] = pair_data

    return results

async def generate_event_csv(pairs, intervals, start_date, end_date, output_name):
    start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
    end_timestamp = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

    results = await apply_backtest(pairs, intervals, since=datetime.utcfromtimestamp(start_timestamp), no_print=False)

    output_dir = 'MachD/backtest_results'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for pair in results:
        for interval in results[pair]:
            df = results[pair][interval]
            df = df[(df['Unix_Timestamp'] >= start_timestamp) & (df['Unix_Timestamp'] <= end_timestamp)]
            if not df.empty:
                df.to_csv(f'{output_dir}/{output_name}_{pair}_{interval}.csv', index=False)

if __name__ == '__main__':
    pairs = ['XBTGBP', 'ETHGBP', 'DOGEUSDT']
    intervals = [1, 60, 240, 1440]

    # Generate full OHLC data
    results = asyncio.run(apply_backtest(pairs, intervals, no_print=False))
    
    output_dir = 'MachD/backtest_results'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for pair in results:
        for interval in results[pair]:
            df = results[pair][interval]
            df.to_csv(f'{output_dir}/{pair}_{interval}.csv', index=False)

    # Generate event-specific datasets
    event_datasets = [
        ("2024-04-01", "2024-05-01", "halving_event1440"),
        ("2023-12-15", "2024-01-15", "christmas_rush2023-24_1440"),
        ("2024-12-15", "2025-01-15", "christmas_rush2024-25_1440"),
    ]
    
    for start_date, end_date, output_name in event_datasets:
        asyncio.run(generate_event_csv(pairs, [1440], start_date, end_date, output_name))
