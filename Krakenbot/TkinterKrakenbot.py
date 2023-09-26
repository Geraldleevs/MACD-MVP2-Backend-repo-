import tkinter as tk
import requests
import urllib.parse
import hashlib
import hmac
import base64
import time
import threading

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

        # buy_limit = 21574
        # sell_limit = 21600
        # buy_amount = 0.0001
        # sell_amount = 0.0001

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

        self.text_widget = tk.Text(output_frame, height=10, width=100)
        self.text_widget.pack()

        self.trading_output_text = tk.Text(output_frame, height=10, width=100)
        self.trading_output_text.pack()

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

    
    # Function to run trading logic in a separate thread
    def trading_logic(self):
        user_entered_buy_limit = float(self.buy_limit_entry.get())
        user_entered_sell_limit = float(self.sell_limit_entry.get())
        user_entered_buy_amount = float(self.buy_amount_entry.get())
        user_entered_sell_amount = float(self.sell_amount_entry.get())

        while True:
            response = requests.get("https://api.kraken.com/0/public/Ticker?pair=BTCGBP").json()
            current_price = float(response['result']['XXBTZGBP']['c'][0])

            trading_output = f"Current Price: {current_price}\n"
            
            if current_price < user_entered_buy_limit:
                trading_output += f"Buying  {user_entered_buy_amount} of BTC at {current_price}!\n"
                resp = self.kraken_request("/0/private/AddOrder", {
                    "nonce": str(int(1000 * time.time())),
                    "ordertype": "market",
                    "type": "buy",
                    "volume": user_entered_buy_amount,
                    "pair": "XBTGBP",
                })
                
                if not resp.get('error'):
                    trading_output += "Successfully bought BTC\n"
                else:
                    trading_output += f"Error: {resp.get('error')}\n"
            elif current_price > user_entered_sell_limit:
                trading_output += f"Selling  {user_entered_sell_amount} of BTC at {current_price}!\n"
                resp = self.kraken_request("/0/private/AddOrder", {
                    "nonce": str(int(1000 * time.time())),
                    "ordertype": "market",
                    "type": "sell",
                    "volume": user_entered_sell_amount,
                    "pair": "XBTGBP",
                })
                
                if not resp.get('error'):
                    trading_output += "Successfully sold BTC\n"
                else:
                    trading_output += f"Error: {resp.get('error')}\n"
            else:
                trading_output += f"Current Price: {current_price}, not buying or selling\n"
            
            self.display_trading_output(trading_output)
            time.sleep(3)

if __name__ == "__main__":
    app = KrakenApp()
    app.mainloop()
