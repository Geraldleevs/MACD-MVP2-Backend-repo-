import tkinter as tk
import requests
import urllib.parse
import hashlib
import hmac
import base64
import time

# Function to make a Kraken API request
def kraken_request(url_path, data):
    headers = {"API-Key": api_key, "API-Sign": get_kraken_signature(url_path, data, api_sec)}
    resp = requests.post(api_url + url_path, headers=headers, data=data)
    return resp.json()

# Function to get Kraken signature
def get_kraken_signature(url_path, data, secret):
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = url_path.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()

# Function to fetch Kraken balance and update the text widget
def fetch_balance():
    data = {"nonce": str(int(1000 * time.time()))}
    response = kraken_request("/0/private/Balance", data)
    
    # Clear the text widget
    text_widget.delete("1.0", tk.END)
    
    # Display the balance in the text widget
    for asset, amount in response['result'].items():
        text_widget.insert(tk.END, f"{asset}: {amount}\n")

# Function to fetch specific balance on an asset
def fetch_specific_balance(asset):
    data = {"nonce": str(int(1000 * time.time())), "asset": asset}
    response = kraken_request("/0/private/TradeBalance", data)
    display_response(response)

# Function to fetch open orders
def fetch_open_orders():
    data = {"nonce": str(int(1000 * time.time())), "trades": True}
    response = kraken_request("/0/private/OpenOrders", data)
    display_response(response)

# Function to fetch closed orders
def fetch_closed_orders():
    data = {"nonce": str(int(1000 * time.time())), "trades": True}
    response = kraken_request("/0/private/ClosedOrders", data)
    display_response(response)

# Function to fetch trades history
def fetch_trades_history():
    data = {"nonce": str(int(1000 * time.time())), "trades": True}
    response = kraken_request("/0/private/TradesHistory", data)
    display_response(response)

# Function to display the API response in the text widget
def display_response(response):
    text_widget.delete("1.0", tk.END)
    text_widget.insert(tk.END, str(response))


# Read API keys from a file (tempkeys)
with open("Krakenbot/tempkeys", "r") as f:
    lines = f.read().splitlines()
    api_key = lines[0]
    api_sec = lines[1]

api_url = "https://api.kraken.com"

# Create the main application window
app = tk.Tk()
app.title("Kraken API Application")

# Create a button to fetch balance
fetch_button = tk.Button(app, text="Fetch Balance", command=fetch_balance)
# Create buttons for each functionality
specific_balance_button = tk.Button(app, text="Specific Balance (GBP)", command=lambda: fetch_specific_balance("GBP"))
open_orders_button = tk.Button(app, text="Open Orders", command=fetch_open_orders)
closed_orders_button = tk.Button(app, text="Closed Orders", command=fetch_closed_orders)
trades_history_button = tk.Button(app, text="Trades History", command=fetch_trades_history)
# Create a text widget to display the balance
text_widget = tk.Text(app, height=5, width=30)
# Pack the buttons
fetch_button.pack()
specific_balance_button.pack()
open_orders_button.pack()
closed_orders_button.pack()
trades_history_button.pack()
text_widget.pack()
# Create input fields for all parameters
ordertype_label = tk.Label(app, text="Ordertype:")
ordertype_label.pack()
ordertype_entry = tk.Entry(app)
ordertype_entry.pack()

type_label = tk.Label(app, text="Type:")
type_label.pack()
type_entry = tk.Entry(app)
type_entry.pack()

volume_label = tk.Label(app, text="Volume:")
volume_label.pack()
volume_entry = tk.Entry(app)
volume_entry.pack()

pair_label = tk.Label(app, text="Pair:")
pair_label.pack()
pair_entry = tk.Entry(app)
pair_entry.pack()

price_label = tk.Label(app, text="Price:")
price_label.pack()
price_entry = tk.Entry(app)
price_entry.pack()

# Function to make a custom AddOrder request
def make_custom_order():
    # Get user-entered values for all parameters
    user_entered_ordertype = ordertype_entry.get()
    user_entered_type = type_entry.get()
    user_entered_volume = volume_entry.get()
    user_entered_pair = pair_entry.get()
    user_entered_price = price_entry.get()
    
    # Construct the request data using user-entered values
    data = {
        "nonce": str(int(1000 * time.time())),
        "ordertype": user_entered_ordertype,
        "type": user_entered_type,
        "volume": user_entered_volume,
        "pair": user_entered_pair,
        "price": user_entered_price
    }
    
    response = kraken_request("/0/private/AddOrder", data)
    display_response(response)

# Create a button for the custom AddOrder request
custom_order_button = tk.Button(app, text="Custom AddOrder", command=make_custom_order)
custom_order_button.pack()

# Start the Tkinter main loop
app.mainloop()
