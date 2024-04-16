import pandas as pd
import streamlit as st
import requests
import urllib.parse
import hashlib
import hmac
import base64
import time
import datetime as dt
import streamlit as st
import pandas as pd
import numpy as np
import logging

class KrakenAppStreamlit:
    def __init__(self):
        self.title = "Kraken API Application"
        self.api_url = "https://api.kraken.com"
        self.output_text = None
        self.load_api_keys()

    def load_api_keys(self):
        if not hasattr(self, 'api_key') or not hasattr(self, 'api_sec'):
            # Read API keys from a file (tempkeys)
            with open("tempkeys", "r") as f:
                lines = f.read().splitlines()
                self.api_key = lines[0]
                self.api_sec = lines[1]
        else:
            print("Keys already loaded")

    # Load the backtesting results CSV file
    @st.cache
    def load_data(_self, file_path):
        df = pd.read_csv(file_path, index_col=0)
        return df
        
    def main(self):
        st.set_page_config(page_title=self.title, page_icon="📈", layout="wide", initial_sidebar_state="expanded")
        
        with st.sidebar:
            st.image("https://assets.zyrosite.com/cdn-cgi/image/format=auto,w=294,fit=crop,q=95/YrD15NnZWQuRJoV6/machd_logo-Y4Lpqn8P75i27V6n.png", width=270)
            st.markdown("---")
            self.create_buttons()

        # Display the main trading application section
        self.display_main_trading_section()

    def display_main_trading_section(self):
        col1, col2 = st.columns([1, 3])
        with col1:
            # Display the balance output
            if hasattr(self, 'balance_output'):
                st.subheader("Balances:")
                st.write("")
                for asset, balance in self.balance_output.items():
                    st.write(f"**{asset}**: {balance}")

            elif hasattr(self, 'trades_history_output'):
                st.subheader("Trades History")
                st.write(self.trades_history_output)
                
            elif hasattr(self, 'open_orders_output'):
                st.subheader("Open Orders")
                st.write(self.open_orders_output)
                
            elif hasattr(self, 'closed_orders_output'):
                st.subheader("Closed Orders")
                st.write(self.closed_orders_output)

        with col2:
            st.markdown("<h1 style='text-align: center;'>Mach D Live Trading Application</h1>", unsafe_allow_html=True)
            st.markdown("---")

            with st.expander("MACD Strategy", expanded=False):
                self.create_MACD_strategy()

            with st.expander("RSI Strategy", expanded=False):
                self.create_RSI_strategy()

            with st.expander("Custom AddOrder", expanded=False):
                self.create_input_fields()

    
    def create_buttons(self):
        st.sidebar.header("Get Balances")
        #specific_currency = st.sidebar.text_input("Enter Specific Currency:", key="specific_currency_input")
        #if st.sidebar.button("Specific Balance"):
        #    self.fetch_specific_balance(specific_currency)

        # Fetch Balance Button
        if st.sidebar.button("Fetch Balance", key="fetch_balance_btn"):
            self.fetch_balance()

        st.sidebar.header("Orders")
        if st.sidebar.button("Open Orders"):
            self.fetch_open_orders()
        if st.sidebar.button("Closed Orders"):
            self.fetch_closed_orders()
        if st.sidebar.button("Trades History"):
            self.fetch_trades_history()
    
    def create_MACD_strategy(self):
        trading_pair = st.text_input("Trading Pair (MACD):", key="macd_trading_pair_input")
        buy_amount = st.text_input("Buy Amount (MACD):", key="macd_buy_amount_input")
        sell_amount = st.text_input("Sell Amount (MACD):", key="macd_sell_amount_input")
        if st.button("Start Trading MACD"):
            self.start_trading_MACD(trading_pair, buy_amount, sell_amount)
    
    def create_RSI_strategy(self):
        trading_pair_rsi = st.text_input("Trading Pair RSI:", key="rsi_trading_pair_input")
        timeframe_rsi = st.text_input("Timeframe/RSI Calculation period:", key="rsi_timeframe_input")
        interval_rsi = st.text_input("Interval: DONT USE WIP", key="rsi_interval_input")
        upper_bound_sell = st.text_input("Upper bound sell:", key="rsi_upper_bound_sell_input")
        lower_bound_buy = st.text_input("Lower bound buy:", key="rsi_lower_bound_buy_input")
        buy_amount_rsi = st.text_input("Buy Amount RSI:", key="rsi_buy_amount_input")
        sell_amount_rsi = st.text_input("Sell Amount RSI:", key="rsi_sell_amount_input")
        if st.button("Start Trading RSI"):
            self.start_trading_RSI(trading_pair_rsi, timeframe_rsi, interval_rsi, upper_bound_sell, lower_bound_buy, buy_amount_rsi, sell_amount_rsi)
    
    def create_input_fields(self):
        ordertype = st.text_input("Ordertype:", key="custom_ordertype_input")
        type = st.text_input("Type:", key="custom_type_input")
        volume = st.text_input("Volume:", key="custom_volume_input")
        pair = st.text_input("Pair:", key="custom_pair_input")
        price = st.text_input("Price:", key="custom_price_input")
        if st.button("Custom AddOrder"):
            self.make_custom_order(ordertype, type, volume, pair, price)
    
    def fetch_balance(self):
        data = {"nonce": str(int(1000 * time.time()))}
        response = self.kraken_request("/0/private/Balance", data)
        self.balance_output = self.display_output(response)
    
    def fetch_open_orders(self):
        data = {"nonce": str(int(1000 * time.time())), "trades": True}
        response = self.kraken_request("/0/private/OpenOrders", data)
        self.open_orders_output = self.display_output_orders(response)
    
    def fetch_closed_orders(self):
        data = {"nonce": str(int(1000 * time.time())), "trades": True}
        response = self.kraken_request("/0/private/ClosedOrders", data)
        self.closed_orders_output = self.display_output_orders(response)
    
    def fetch_trades_history(self):
        data = {"nonce": str(int(1000 * time.time())), "trades": True}
        response = self.kraken_request("/0/private/TradesHistory", data)
        self.trades_history_output = self.display_output_history(response)
    
    def make_custom_order(self, ordertype, type, volume, pair, price):
        data = {
            "nonce": str(int(1000 * time.time())),
            "ordertype": ordertype,
            "type": type,
            "volume": volume,
            "pair": pair,
            "price": price
        }
        response = self.kraken_request("/0/private/AddOrder", data)
        self.display_output(response)
    
    def start_trading_MACD(self, trading_pair, buy_amount, sell_amount):
        # Implement your MACD trading logic here
        pass
    
    def start_trading_RSI(self, trading_pair, timeframe, interval, upper_bound_sell, lower_bound_buy, buy_amount, sell_amount):
        # Implement your RSI trading logic here
        pass
    
    def display_output(self, response):
        if isinstance(response, dict):
            output = {}
            for asset, balance in response['result'].items():
                if float(balance) != 0:
                    output[asset] = balance
            return output
    
    def display_output_orders(self, response):
        if isinstance(response, dict):
            output = {}
            orders = response.get('result', {}).get('open', {})
            for order_id, order_info in orders.items():
                desc = order_info.get('descr', {})
                pair = desc.get('pair', '')
                ordertype = desc.get('type', '')
                price = desc.get('price', '')
                volume = desc.get('vol', '')
                status = order_info.get('status', '')
                output[f"Order {order_id} - {pair} ({ordertype})"] = f"Price: {price}, Volume: {volume}, Status: {status}"
            return output
    
    def display_output_history(self, response):
        if isinstance(response, dict):
            output = {}
            trades = response.get('result', {}).get('trades', [])
            for trade_id, trade_info in trades.items():
                pair = trade_info.get('pair', '')
                price = trade_info.get('price', '')
                volume = trade_info.get('vol', '')
                time = trade_info.get('time', '')
                output[f"Trade {trade_id} - {pair}"] = f"Price: {price}, Volume: {volume}, Time: {time}"
            return output

    
    def kraken_request(self, url_path, data):
        headers = {"API-Key": self.api_key, "API-Sign": self.get_kraken_signature(url_path, data, self.api_sec)}
        resp = requests.post(self.api_url + url_path, headers=headers, data=data)
        return resp.json()
    
    def get_kraken_signature(self, url_path, data, secret):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = url_path.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

KrakenAppStreamlit().main()
