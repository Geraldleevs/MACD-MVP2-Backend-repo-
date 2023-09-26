import time
import requests
import urllib.parse
import hashlib
import hmac
import base64

with open ("Krakenbot/tempkeys", "r") as f:
    lines = f.read().splitlines()
    api_key = lines[0]
    api_sec = lines[1]

api_url = "https://api.kraken.com"

def get_kraken_signature(url_path, data, secret):
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = url_path.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(secret),message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())

    return sigdigest.decode()

def kraken_request(url_path, data, api_key, api_sec):
    headers = {"API-Key": api_key, "API-Sign": get_kraken_signature(url_path, data, api_sec)}
    resp = requests.post((api_url + url_path), headers=headers, data=data )

    return resp 

#Total balance
# resp = kraken_request("/0/private/Balance", {
#     "nonce": str(int(1000 * time.time()))
# }, api_key, api_sec)

#Specific balance on asset
# resp = kraken_request("/0/private/TradeBalance", {
#     "nonce": str(int(1000 * time.time())),
#     "asset": "GBP"
# }, api_key, api_sec)

#Open orders query
# resp = kraken_request("/0/private/OpenOrders", {
#     "nonce": str(int(1000 * time.time())),
#     "trades": True
# }, api_key, api_sec)

#Closed orders query
# resp = kraken_request("/0/private/ClosedOrders", {
#     "nonce": str(int(1000 * time.time())),
#     "trades": True
# }, api_key, api_sec)

#Trades History query
# resp = kraken_request("/0/private/TradesHistory", {
#      "nonce": str(int(1000 * time.time())),
#      "trades": True
#  }, api_key, api_sec)

#Create sell order
# resp = kraken_request("/0/private/AddOrder", {
#      "nonce": str(int(1000 * time.time())),
#      "ordertype": "limit",
#      "type": "sell",
#      "volume": 1.00,
#      "pair": "XBTUSD",
#      "price": 27000
#  }, api_key, api_sec)

buy_limit = 21574
sell_limit = 21600
buy_amount = 0.0001
sell_amount = 0.0001

while True:
    current_price = requests.get("https://api.kraken.com/0/public/Ticker?pair=BTCGBP").json()['result']['XXBTZGBP']['c'][0]
    print(current_price)
    if float(current_price) < buy_limit:
        print(f"Buying  {buy_amount} of BTC at {current_price}!")
    
        resp = kraken_request("/0/private/AddOrder", {
        "nonce": str(int(1000 * time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": buy_amount,
        "pair": "XBTGBP",
        }, api_key, api_sec)

        if not resp.json()['error']:
            print("successfully bought BTC")
        else:
            print(f"Error: {resp.json()['error']}")
    elif float(current_price) > sell_limit:
        print(f"Selling  {sell_amount} of BTC at {current_price}!")
    
        resp = kraken_request("/0/private/AddOrder", {
        "nonce": str(int(1000 * time.time())),
        "ordertype": "market",
        "type": "sell",
        "volume": sell_amount,
        "pair": "XBTGBP",
        }, api_key, api_sec)

        if not resp.json()['error']:
            print("successfully sold BTC")
        else:
            print(f"Error: {resp.json()['error']}")
    else:
        print(f"Current Price: {current_price}, not buying or selling")
    time.sleep(3)