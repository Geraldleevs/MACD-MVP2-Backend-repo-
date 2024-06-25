# Mach D Trading
## Team member
- Aaron Barker
- Gerald Lee
- Jerry Chin

### Libraries Installation
```bash
pip install -r requirements.txt

# OR

pip install numpy
pip install pandas
pip install streamlit
pip install Django
pip install djangorestframework
pip install plotly
pip install requests
pip install firebase
```

### running on streamlit
`python -m streamlit run Krakenbot\StreamLit_Livetrading.py`

### CSV for downloaded binance header
`open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore` - Binance default
`open_time,Open,High,Low,Close,Volume,Close_time,Quote_volume,Count,Taker_buy_volume,Taker_buy_quote_volume,Ignore` - Mach D usable

## ENV Variables
```bash
DJANGO_SECRET_KEY="ANY_SECRET_STRING"
API_URL="https://mach-d-trading-xr6ou3pjdq-nw.a.run.app" # The api url, for Google scheduler authentication
GCLOUD_EMAIL="firebase-adminsdk...@...gserviceaccount.com" # Your Google scheduler's service account email
PYTHON_ENV="development" # development | production
ADDRESS="127.0.0.1" # Use 0.0.0.0 in docker / cloud
PORT="8080"

# These are from firebase credentials.json, download it from the firebase project and copy down
FIREBASE_PROJECT_ID="project_id"
FIREBASE_PRIVATE_KEY_ID="private_key_id"
FIREBASE_PRIVATE_KEY="private_key"
FIREBASE_CLIENT_EMAIL="client_email"
FIREBASE_CLIENT_ID="client_id"
FIREBASE_CLIENT_X509_CERT_URL="client_x509_cert_url"
```

## Django-REST Server
### Setup Server
`python manage.py migrate`

### Starting Server
`python manage.py runserver` or use vscode's `run and debug` `Django Server` script

## Starting with Docker
```bash
docker compose up # CTRL + C to stop
docker compose start # If already built
docker compose logs -f # Show logs, CTRL + C to stop
docker compose stop
docker compose down --rmi local # Remove container to rebuild with changes

# or

docker build -t KrakenBot . # Note the trailing "."
docker run -p 8000:8000 --name KrakenBot KrakenBot # Change port number [8000:8000] if needed
docker stop KrakenBot
docker rm KrakenBot # Remove container
docker rmi KrakenBot # Remove image
```

## REST API Endpoints

### Market

Fetch market prices: `http://127.0.0.1:8000/api/market [GET]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/market
Query: convert_from, convert_to
Response:
[
  {
    "token": string,
    "price": number
  },
  ...
]
```

#### Example
```
Request: http://127.0.0.1:8000/api/market?convert_from=eth&convert_to=btc
Response:
[
  {
    "token": "BTC",
    "price": "0.055080"
  }
]
```
</details>

<hr/>

### Backtest

Trigger backtest and save in firebase database: `http://127.0.0.1:8000/api/backtest [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/backtest
Authorization: Bearer {Google_OIDC_Token}
Response:
None (Status: 200)
```

#### Example
```
Request: http://127.0.0.1:8000/api/backtest
Authorization: Bearer ANY_VALID_TOKEN
Response:
None (Status: 200)
```
</details>

<hr/>

### Buy/Sell

Buy/Sell tokens: `http://127.0.0.1:8000/api/trade [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/trade
Authorization: Bearer {JWT_Token}
Body:
{
  uid: string,
  token_id: string,
  amount: number,
  value: number,
  trade_type: string
}
Response:
{
  id: string,
  token_id: string,
  amount: number
}
```

#### Example (Buy)
```
Request: http://127.0.0.1:8000/api/trade
Authorization: Bearer ANY_VALID_TOKEN
Body:
{
  uid: "Gmcjdq33QxPSggpJx7CsTK42cQR2",
  token_id: "BTC",
  amount: 10,
  value: 54432.12,
  trade_type: "buy"
}
Response:
{
  id: "BTC",
  token_id: "BTC",
  amount: 10
}
```

#### Example (Sell)
```
Request: http://127.0.0.1:8000/api/trade
Authorization: Bearer ANY_VALID_TOKEN
Body:
{
  uid: "Gmcjdq33QxPSggpJx7CsTK42cQR2",
  token_id: "BTC",
  amount: 10,
  value: 54432.12,
  trade_type: "sell"
}
Response:
{
  id: "BTC",
  token_id: "BTC",
  amount: 10
}
```
</details>

<hr/>

## Google Cloud Deployment
### Environment Variables
```bash
# ...everything from the ENV variable above
ADDRESS="0.0.0.0" # Must be set
# PORT is set somewhere else on Google Cloud, not in environment variable
```
