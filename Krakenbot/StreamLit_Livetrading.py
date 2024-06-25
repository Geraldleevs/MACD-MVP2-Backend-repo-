import time
import streamlit as st
import pandas as pd
import requests
import urllib.parse
import hashlib
import hmac
import base64
import datetime as dt

class KrakenAppStreamlit:
    st.set_page_config(page_title="Kraken API Application", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

    def __init__(self):
        self.api_url = "https://api.kraken.com"
        self.output_text = None
        self.load_api_keys()

    def load_api_keys(self):
        if not hasattr(self, 'api_key') or not hasattr(self, 'api_sec'):
            # Read API keys from a file (tempkeys)
            with open("Krakenbot/tempkeys.txt", "r") as f:
                lines = f.read().splitlines()
                self.api_key = lines[0]
                self.api_sec = lines[1]
        else:
            print("Keys already loaded")

    def main(self):
        page_names_to_funcs = {
            "Home": self.intro,
            "Account Information": self.Account_information,
            "Backtesting": self.Backtesting_tool,
            "Mean reversion": self.mean_reversion_tool,
            "Live Trading": self.Live_trading_tool
        }

        st.sidebar.image("https://assets.zyrosite.com/cdn-cgi/image/format=auto,w=294,fit=crop,q=95/YrD15NnZWQuRJoV6/machd_logo-Y4Lpqn8P75i27V6n.png", width=270)
        st.sidebar.markdown("---")
        tool_name = st.sidebar.selectbox("Choose a tool", page_names_to_funcs.keys())
        page_names_to_funcs[tool_name]()

    def intro(self):
        st.write("# Welcome to Mach D Trading! 👋")
        st.sidebar.success("Select a tool to use.")
        st.markdown(
            """
            Mach D is a tool for planning and trading.

            **👈 Select a tool from the dropdown on the left** to see some examples
            of what Mach D can do!

            ### Want to learn more?

            - Check out [machdtrading.com](https://machdtrading.com)
            - About [About Mach D](https://www.machdtrading.com/about)
            - News [News @ Mach D](https://www.machdtrading.com/news)
            - Privacy policy [Privacy Policy](https://www.machdtrading.com/privacy-policy)
        """
        )

    def Account_information(self):
        st.header("Account Information")

        fetch_balance_btn = st.sidebar.button("Fetch Balance")
        open_orders_btn = st.sidebar.button("Open Orders")
        closed_orders_btn = st.sidebar.button("Closed Orders")
        trades_history_btn = st.sidebar.button("Trades History")

        if fetch_balance_btn:
            self.fetch_balance()

            if hasattr(self, 'balance_output'):
                st.subheader("Balances:")
                st.write("")
                for asset, balance in self.balance_output.items():
                    st.write(f"**{asset}**: {balance}")

        if open_orders_btn:
            self.fetch_open_orders()

            if hasattr(self, 'open_orders_output'):
                st.subheader("Open Orders")
                for order, info in self.open_orders_output.items():
                    st.write(f"**{order}** - {info}")

        if closed_orders_btn:
            self.fetch_closed_orders()

            if hasattr(self, 'closed_orders_output'):
                st.subheader("Closed Orders")
                for order, info in self.closed_orders_output.items():
                    st.write(f"**{order}** - {info}")
                    st.write("")

        if trades_history_btn:
            self.fetch_trades_history()

            if hasattr(self, 'trades_history_output'):
                st.subheader("Trades History")
                for trade, info in self.trades_history_output.items():
                    st.write(f"**{trade}** \n {info}")

    def Backtesting_tool(self):
        st.header("Backtesting Tool")

    def mean_reversion_tool(self):
        st.header("Mean Reversion Tool")

    def Live_trading_tool(self):
        st.header("Live Trading Tool")

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

                formatted_time = dt.datetime.fromtimestamp(float(time)).strftime('%Y-%m-%d %H:%M:%S')
                output[f"Trade {trade_id} - {pair}"] = f"\nPrice: {price}\n Volume: {volume}\n Time: {formatted_time}"
                
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
