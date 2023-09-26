import tkinter as tk
import requests
import urllib.parse
import hashlib
import hmac
import base64
import time
import threading
import numpy as np


class KrakenApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kraken API Application")
        self.dark_mode_enabled = False
        self.api_url = "https://api.kraken.com"
        self.load_api_keys()
        self.create_widgets()
        self.apply_dark_mode()
        self.trading_thread = None  # Initialize the trading thread


    def load_api_keys(self):
        # Read API keys from a file (tempkeys)
        with open("Krakenbot/tempkeys", "r") as f:
            lines = f.read().splitlines()
            self.api_key = lines[0]
            self.api_sec = lines[1]

    def create_widgets(self):
        # Create frames for different sections
        self.create_buttons_frame()
        self.create_strategy_frame()
        self.create_output_frame()
        self.create_input_fields_frame()

    def create_buttons_frame(self):
        buttons_frame = tk.Frame(self)
        buttons_frame.pack(side=tk.LEFT)

        self.fetch_button = self.create_button(buttons_frame, "Fetch Balance", self.fetch_balance)
        self.specific_balance_button = self.create_button(buttons_frame, "Specific Balance (GBP)", lambda: self.fetch_specific_balance("GBP"))
        self.open_orders_button = self.create_button(buttons_frame, "Open Orders", self.fetch_open_orders)
        self.closed_orders_button = self.create_button(buttons_frame, "Closed Orders", self.fetch_closed_orders)
        self.trades_history_button = self.create_button(buttons_frame, "Trades History", self.fetch_trades_history)
        self.dark_mode_button = self.create_button(buttons_frame, "Toggle Dark Mode", self.toggle_dark_mode)

    def create_strategy_frame(self):
        strategy_frame = tk.Frame(self)
        strategy_frame.pack(side=tk.LEFT)

        buy_limit = 21574
        sell_limit = 21600
        buy_amount = 0.0001
        sell_amount = 0.0001

        self.buy_limit_label = self.create_label(strategy_frame, "Buy Limit:")
        self.buy_limit_entry = self.create_entry(strategy_frame)
        self.sell_limit_label = self.create_label(strategy_frame, "Sell Limit:")
        self.sell_limit_entry = self.create_entry(strategy_frame)
        self.buy_amount_label = self.create_label(strategy_frame, "Buy Amount:")
        self.buy_amount_entry = self.create_entry(strategy_frame)
        self.sell_amount_label = self.create_label(strategy_frame, "Sell Amount:")
        self.sell_amount_entry = self.create_entry(strategy_frame)

        self.start_trading_button = self.create_button(strategy_frame, "Start Trading", self.start_trading)

    def create_label(self, frame, text):
        label = tk.Label(frame, text=text)
        label.pack()
        return label

    def create_entry(self, frame):
        entry = tk.Entry(frame)
        entry.pack()
        return entry

    def start_trading(self):
        # Start the trading thread
        if self.trading_thread is None or not self.trading_thread.is_alive():
            self.trading_thread = threading.Thread(target=self.trading_logic)
            self.trading_thread.daemon = True  # Set the thread as a daemon so it exits when the main application exits
            self.trading_thread.start()

    def create_button(self, frame, text, command):
        button = tk.Button(frame, text=text, command=command)
        button.pack(side=tk.TOP, padx=5)
        return button
    
    def create_output_frame(self):
        output_frame = tk.Frame(self)
        output_frame.pack(side=tk.LEFT)

        # Create a vertical scrollbar for the text boxes
        text_scrollbar = tk.Scrollbar(output_frame)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create the text widgets with the yscrollcommand option set to the scrollbar's set method
        self.text_widget = tk.Text(output_frame, height=10, width=50, yscrollcommand=text_scrollbar.set)
        self.text_widget.pack(side=tk.LEFT)

        self.trading_output_text = tk.Text(output_frame, height=10, width=50, yscrollcommand=text_scrollbar.set)
        self.trading_output_text.pack(side=tk.LEFT)

        # Configure the scrollbar to work with the text widgets
        text_scrollbar.config(command=lambda *args: self.scroll_text_widgets(*args))

    # Add a method to scroll the text widgets
    def scroll_text_widgets(self, *args):
        self.text_widget.yview(*args)
        self.trading_output_text.yview(*args)

    def create_input_fields_frame(self):
        input_fields_frame = tk.Frame(self)
        input_fields_frame.pack(side=tk.LEFT)

        self.create_input_field(input_fields_frame, "Ordertype:")
        self.create_input_field(input_fields_frame, "Type:")
        self.create_input_field(input_fields_frame, "Volume:")
        self.create_input_field(input_fields_frame, "Pair:")
        self.create_input_field(input_fields_frame, "Price:")

        self.custom_order_button = self.create_button(input_fields_frame, "Custom AddOrder", self.make_custom_order)

    def create_input_field(self, frame, label_text):
        label = tk.Label(frame, text=label_text)
        label.pack()
        entry = tk.Entry(frame)
        entry.pack()

    def create_trading_output_widget(self):
        self.trading_output_text = tk.Text(self, height=10, width=50)
        self.trading_output_text.pack()

    def apply_dark_mode(self):
        # Define light and dark mode colors
        light_bg = "#FFFFFF"
        light_fg = "#000000"
        dark_bg = "#121212"
        dark_fg = "#FFFFFF"

        # Choose colors based on dark mode status
        bg_color = dark_bg if self.dark_mode_enabled else light_bg
        fg_color = dark_fg if self.dark_mode_enabled else light_fg

        # Apply dark mode to the main window
        self.configure(bg=bg_color)

        # Apply dark mode to labels, entries, and buttons
        label_bg = dark_bg if self.dark_mode_enabled else light_bg
        label_fg = dark_fg if self.dark_mode_enabled else light_fg
        entry_bg = "#333333" if self.dark_mode_enabled else light_bg
        entry_fg = dark_fg if self.dark_mode_enabled else light_fg
        button_bg = "#333333" if self.dark_mode_enabled else light_bg
        button_fg = dark_fg if self.dark_mode_enabled else light_fg

        for widget in self.winfo_children():
            if isinstance(widget, (tk.Label, tk.Entry)):
                widget.configure(bg=label_bg, fg=label_fg)
            elif isinstance(widget, tk.Button):
                widget.configure(bg=button_bg, fg=button_fg)
            elif isinstance(widget, tk.Text):
                widget.configure(bg=bg_color, fg=fg_color)

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

    def fetch_balance(self):
        data = {"nonce": str(int(1000 * time.time()))}
        response = self.kraken_request("/0/private/Balance", data)
        self.text_widget.delete("1.0", tk.END)
        for asset, amount in response['result'].items():
            self.text_widget.insert(tk.END, f"{asset}: {amount}\n")

    def fetch_specific_balance(self, asset):
        data = {"nonce": str(int(1000 * time.time())), "asset": asset}
        response = self.kraken_request("/0/private/TradeBalance", data)
        self.display_response(response)

    def fetch_open_orders(self):
        data = {"nonce": str(int(1000 * time.time())), "trades": True}
        response = self.kraken_request("/0/private/OpenOrders", data)
        self.display_response(response)

    def fetch_closed_orders(self):
        data = {"nonce": str(int(1000 * time.time())), "trades": True}
        response = self.kraken_request("/0/private/ClosedOrders", data)
        self.display_response(response)

    def fetch_trades_history(self):
        data = {"nonce": str(int(1000 * time.time())), "trades": True}
        response = self.kraken_request("/0/private/TradesHistory", data)
        self.display_response(response)

    def display_response(self, response):
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, str(response))

        
    def make_custom_order(self):
        user_entered_ordertype = self.ordertype_entry.get()
        user_entered_type = self.type_entry.get()
        user_entered_volume = self.volume_entry.get()
        user_entered_pair = self.pair_entry.get()
        user_entered_price = self.price_entry.get()

        data = {
            "nonce": str(int(1000 * time.time())),
            "ordertype": user_entered_ordertype,
            "type": user_entered_type,
            "volume": user_entered_volume,
            "pair": user_entered_pair,
            "price": user_entered_price
        }

        response = self.kraken_request("/0/private/AddOrder", data)
        self.display_response(response)

    def display_trading_output(self, text):
        self.trading_output_text.insert(tk.END, text + '\n')

    def toggle_dark_mode(self):
        self.dark_mode_enabled = not self.dark_mode_enabled
        self.apply_dark_mode()

    def fetch_historical_data(self, pair, interval, since):
        """
        Fetch historical price data from Kraken.

        :param pair: Trading pair (e.g., "XBTGBP").
        :param interval: Time interval for data (e.g., "1h" for 1-hour candles).
        :param since: Unix timestamp for the start of the data range.
        :return: List of historical price data.
        """
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}&since={since}"

        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                print(data)
                if 'result' in data and pair in data['result']:
                    return data['result'][pair]
                else:
                    print(f"Error: No data found for trading pair '{pair}' in the response.")
            else:
                print(f"Error: Failed to fetch historical data (HTTP {response.status_code}).")
        except Exception as e:
            print(f"Error fetching historical data: {e}")
        
        time.sleep(2)

        return []




    def fetch_current_price(self, pair):
        """
        Fetch the current price for a trading pair.

        :param pair: Trading pair symbol (e.g., 'XBTGBP' for Bitcoin to GBP).
        :return: Current price as a float or None if the request fails.
        """
        try:
            response = requests.get(f"https://api.kraken.com/0/public/Ticker?pair={pair}")
            response_data = response.json()
            
            # Check if the response contains data for the specified pair
            if 'result' in response_data and pair in response_data['result']:
                current_price = float(response_data['result'][pair]['c'][0])
                return current_price
            else:
                print(f"Error: Trading pair '{pair}' not found in API response.")
                return None
        except Exception as e:
            print(f"Error fetching current price: {e}")
            return None


    def calculate_macd(self, data, short_window, long_window, signal_window):
        """
        Calculate MACD indicator.

        :param data: List of historical price data.
        :param short_window: Short-term moving average window.
        :param long_window: Long-term moving average window.
        :param signal_window: Signal line moving average window.
        :return: List of MACD values.
        """
        if len(data) < long_window:
            return []

        # Extract closing prices from the data
        close_prices = np.array([float(item[4]) for item in data])

        # Calculate short-term EMA
        short_ema = self.calculate_ema(close_prices, short_window)

        # Calculate long-term EMA
        long_ema = self.calculate_ema(close_prices, long_window)

        # Calculate MACD line
        macd_line = short_ema - long_ema

        # Calculate signal line
        signal_line = self.calculate_ema(macd_line, signal_window)

        return macd_line, signal_line

    def calculate_ema(self, data, window):
        """
        Calculate Exponential Moving Average (EMA).

        :param data: Input data (e.g., price or MACD values).
        :param window: EMA window.
        :return: EMA values.
        """
        ema = []
        alpha = 2 / (window + 1)
        ema_prev = data[0]

        for value in data:
            ema_prev = (1 - alpha) * ema_prev + alpha * value
            ema.append(ema_prev)

        return np.array(ema)
    
    def place_market_order(self, type, pair, volume, ordertype):
        """
        Place a market order.

        :param ordertype: Order type ('market').
        :param type: Order type ('buy' or 'sell').
        :param volume: Amount to buy/sell.
        :param pair: Trading pair symbol (e.g., 'XBTGBP' for Bitcoin to GBP).
        :return: Response from Kraken API or None if the request fails.
        """
        try:
            data = {
                "nonce": str(int(1000 * time.time())),
                "ordertype": ordertype,
                "type": type,
                "volume": volume,
                "pair": pair,
            }
            response = self.kraken_request("/0/private/AddOrder", data)
            return response
        except Exception as e:
            print(f"Error placing market order: {e}")
            return None

    
    # Function to run trading logic in a separate thread
    def trading_logic(self):
    # Define MACD parameters
        short_ema_period = 1
        long_ema_period = 26
        signal_ema_period = 9

        while True:
            # Fetch historical price data
            historical_data = self.fetch_historical_data("XXBTZGBP",short_ema_period, long_ema_period)
            
            if historical_data:
                # Calculate MACD
                macd_line, signal_line = self.calculate_macd(
                    historical_data, short_ema_period, long_ema_period, signal_ema_period
                )

                current_price = float(self.fetch_current_price("XXBTZGBP"))

                trading_output = f"Current Price: {current_price}\n"
                
                # Check for MACD buy signal
                if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
                    trading_output += f"Buy signal detected! Buying BTC at {current_price}!\n"
                    resp = self.place_market_order("buy", "XXBTZGBP", 0.0001, 'market')  # Adjust volume as needed

                    if not resp.get('error'):
                        trading_output += "Successfully bought BTC\n"
                    else:
                        trading_output += f"Error: {resp.get('error')}\n"

                # Check for MACD sell signal
                elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
                    trading_output += f"Sell signal detected! Selling BTC at {current_price}!\n"
                    resp = self.place_market_order("sell", "XXBTZGBP", 0.0001, 'market')  # Adjust volume as needed

                    if not resp.get('error'):
                        trading_output += "Successfully sold BTC\n"
                    else:
                        trading_output += f"Error: {resp.get('error')}\n"
                
                else:
                    trading_output += "No trading signal\n"

                self.display_trading_output(trading_output)
            
            time.sleep(3)




if __name__ == "__main__":
    app = KrakenApp()
    app.mainloop()
