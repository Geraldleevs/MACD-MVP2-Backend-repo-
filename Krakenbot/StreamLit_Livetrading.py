import streamlit as st
import requests
import urllib.parse
import hashlib
import hmac
import base64
import time

class KrakenAppStreamlit:
    def __init__(self):
        self.title = "Kraken API Application"
        self.api_url = "https://api.kraken.com"
        self.output_text = None
        self.load_api_keys()
        st.set_page_config(page_title=self.title, page_icon="📈", layout="wide", initial_sidebar_state="expanded")

    
    def load_api_keys(self):
        if not hasattr(self, 'api_key') or not hasattr(self, 'api_sec'):
            # Read API keys from a file (tempkeys)
            with open("tempkeys", "r") as f:
                lines = f.read().splitlines()
                self.api_key = lines[0]
                self.api_sec = lines[1]
        else:
            print("Keys already loaded")
        
    def main(self):
        
        with st.sidebar:
            st.image("https://assets.zyrosite.com/cdn-cgi/image/format=auto,w=294,fit=crop,q=95/YrD15NnZWQuRJoV6/machd_logo-Y4Lpqn8P75i27V6n.png", width=270)
            st.markdown("---")

        # Create a sidebar radio button for app selection
        app_selection = st.sidebar.radio("Select App", ("Backtesting", "Realtime trading"))
        
        # Depending on the selection, call the respective method
        if app_selection == "Backtesting":
            self.MachD_Backtesting()
        elif app_selection == "Realtime trading":
            self.MachD_Realtime_Trading()
    
    def MachD_Backtesting(self):
        st.write("Welcome to Backtesting")
        # Add your content for App 1 here
    
    def MachD_Realtime_Trading(self):
    
            

        with st.container():
            st.markdown("<h1 style='text-align: center; color: #301934;'>Mach D Live Trading Application</h1>", unsafe_allow_html=True)
            st.markdown("---")

            with st.expander("MACD Strategy", expanded=False):
                self.create_MACD_strategy()

            with st.expander("RSI Strategy", expanded=False):
                self.create_RSI_strategy()

            with st.expander("Custom AddOrder", expanded=False):
                self.create_input_fields()

            self.create_buttons()
            self.output_text = st.empty()  # Create an empty container for output
    
    def create_buttons(self):
        st.sidebar.header("Get Balances")
        if st.sidebar.button("Fetch Balance"):
            self.fetch_balance()

        specific_currency = st.sidebar.text_input("Enter Specific Currency:")
        if st.sidebar.button("Specific Balance"):
            self.fetch_specific_balance(specific_currency)

        st.sidebar.header("Orders")
        if st.sidebar.button("Open Orders"):
            self.fetch_open_orders()
        if st.sidebar.button("Closed Orders"):
            self.fetch_closed_orders()
        if st.sidebar.button("Trades History"):
            self.fetch_trades_history()
    
    def create_MACD_strategy(self):
        trading_pair = st.text_input("Trading Pair (MACD):")
        buy_amount = st.text_input("Buy Amount (MACD):")
        sell_amount = st.text_input("Sell Amount (MACD):")
        if st.button("Start Trading MACD"):
            self.start_trading_MACD(trading_pair, buy_amount, sell_amount)
    
    def create_RSI_strategy(self):
        trading_pair_rsi = st.text_input("Trading Pair RSI:")
        timeframe_rsi = st.text_input("Timeframe/RSI Calculation period:")
        interval_rsi = st.text_input("Interval: DONT USE WIP")
        upper_bound_sell = st.text_input("Upper bound sell:")
        lower_bound_buy = st.text_input("Lower bound buy:")
        buy_amount_rsi = st.text_input("Buy Amount RSI:")
        sell_amount_rsi = st.text_input("Sell Amount RSI:")
        if st.button("Start Trading RSI"):
            self.start_trading_RSI(trading_pair_rsi, timeframe_rsi, interval_rsi, upper_bound_sell, lower_bound_buy, buy_amount_rsi, sell_amount_rsi)
    
    def create_input_fields(self):
        ordertype = st.text_input("Ordertype:")
        type = st.text_input("Type:")
        volume = st.text_input("Volume:")
        pair = st.text_input("Pair:")
        price = st.text_input("Price:")
        if st.button("Custom AddOrder"):
            self.make_custom_order(ordertype, type, volume, pair, price)
    
    def fetch_balance(self):
        data = {"nonce": str(int(1000 * time.time()))}
        response = self.kraken_request("/0/private/Balance", data)
        st.header("Balance")
        self.display_output(response)
    
    def fetch_specific_balance(self, asset):
        data = {"nonce": str(int(1000 * time.time())), "asset": asset}
        response = self.kraken_request("/0/private/TradeBalance", data)
        st.header("Balance: ", asset)
        self.display_output(response)
    
    def fetch_open_orders(self):
        data = {"nonce": str(int(1000 * time.time())), "trades": True}
        response = self.kraken_request("/0/private/OpenOrders", data)
        st.header("Open Orders")
        self.display_output(response)
    
    def fetch_closed_orders(self):
        data = {"nonce": str(int(1000 * time.time())), "trades": True}
        response = self.kraken_request("/0/private/ClosedOrders", data)
        st.header("Closed Orders")
        self.display_output(response)
    
    def fetch_trades_history(self):
        data = {"nonce": str(int(1000 * time.time())), "trades": True}
        response = self.kraken_request("/0/private/TradesHistory", data)
        st.header("Trades History")
        self.display_output(response)
    
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
            col1, col2 = st.columns(2)
            for key, value in response.items():
                # col1.write(key)
                col2.write(value)

    
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