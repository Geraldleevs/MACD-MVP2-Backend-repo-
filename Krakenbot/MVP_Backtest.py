import numpy as np
import pandas as pd
import tkinter as tk
from itertools import combinations
import logging
from TA_calculations import *
import TA_functions 

# Data placeholder DF
#read BTCUSDT data file
df = pd.read_csv('data/BTCUSDT_data.csv')
#drop unamed and index columns
df.drop(["Unnamed: 0", "index"], axis = 1, inplace = True)


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



#Test functions
atr_test = TA_functions.use_atr(df)
atr_test[(atr_test['buy_sell'] == 1) | (atr_test['buy_sell'] == -1)]

macd_test = TA_functions.use_macd(df)
macd_test[(macd_test['buy_sell'] == 1) | (macd_test['buy_sell'] == -1)]

sma_test = TA_functions.use_sma(df)
sma_test[(sma_test['buy_sell'] == 1) | (sma_test['buy_sell'] == -1)]

rsi_test = TA_functions.use_rsi70_30(df)
rsi_test[(rsi_test['buy_sell'] == 1) | (rsi_test['buy_sell'] == -1)]

ichimoku_test = TA_functions.use_ichimoku(df)
ichimoku_test[(ichimoku_test['buy_sell'] == 1) | (ichimoku_test['buy_sell'] == -1)]

donchian_test = TA_functions.use_donchian_channel(df)
donchian_test[(donchian_test['buy_sell'] == 1) | (donchian_test['buy_sell'] == -1)]

SO_test = TA_functions.use_stochastic(df)
SO_test[(SO_test['buy_sell'] == 1) | (SO_test['buy_sell'] == -1)]

# Set up logging
logging.basicConfig(filename='trade_logs.log', level=logging.INFO, format='%(asctime)s - %(message)s')
coin_profit_df = pd.DataFrame()

# Create an empty DataFrame to store the trades log
trades_log = pd.DataFrame(columns=['Coin', 'Strategy', 'Buy/Sell', 'Price'])

# Assuming filesyear and indicators are defined elsewhere or in previous cells
#indicators = [TA_functions.use_macd, TA_functions.use_rsi70_30, TA_functions.use_sma,]
#to use non custom parameter rsi use 'use_rsi'
indicators = [
    TA_functions.use_macd,
    TA_functions.use_sma,
    TA_functions.use_ichimoku,
    TA_functions.use_donchian_channel,
    TA_functions.use_atr,
    TA_functions.use_rsi65_25,
    TA_functions.use_rsi66_26,
    TA_functions.use_rsi67_27,
    TA_functions.use_rsi68_28,
    TA_functions.use_rsi69_29,
    TA_functions.use_rsi70_30,
    TA_functions.use_rsi71_31,
    TA_functions.use_rsi72_32,
    TA_functions.use_rsi73_33,
    TA_functions.use_rsi74_34,
    TA_functions.use_rsi75_35
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


