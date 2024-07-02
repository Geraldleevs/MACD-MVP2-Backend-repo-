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
pip install django
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

GNEWS_API_KEY="GNEWS_API_KEY"
GNEWS_MAX_FETCH="10" # Free account only get max 10
GNEWS_FETCH_KEYWORD="bitcoin:BTC,ethereum:ETH,dogecoin:DOGE,cordano:ADA,solana:SOL,ripple coin:XRP"
# Specify keyword in the form 'search_text:tag'
# Each call fetch only one keyword separated by ',' fetch in sequence

NEWS_EXPIRED_IN_DAY="0" # When will old news be deleted
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
Query: convert_from, convert_to, exclude
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

### Update Last Close

Fetch yesterday close price and update in firebase: `http://127.0.0.1:8000/api/update-last-close [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/update-last-close
Authorization: Bearer {Google_OIDC_Token}
Response:
None (Status: 200)
```

#### Example
```
Request: http://127.0.0.1:8000/api/update-last-close
Authorization: Bearer ANY_VALID_TOKEN
Response:
None (Status: 200)
```
</details>

<hr/>

### Daily Update

Call backtest and update last close at once (For GCloud Scheduler): `http://127.0.0.1:8000/api/daily-update [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/daily-update
Authorization: Bearer {Google_OIDC_Token}
Response:
None (Status: 200)
```

#### Example
```
Request: http://127.0.0.1:8000/api/daily-update
Authorization: Bearer ANY_VALID_TOKEN
Response:
None (Status: 200)
```
</details>

<hr/>

### News

Fetch GNews and save in firebase database: `http://127.0.0.1:8000/api/news [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/news
Authorization: Bearer {Google_OIDC_Token}
Response:
None (Status: 200)
```

#### Example
```
Request: http://127.0.0.1:8000/api/news
Authorization: Bearer ANY_VALID_TOKEN
Response:
None (Status: 200)
```
</details>

<hr/>

### Trade

Trade tokens / Live Trade: `http://127.0.0.1:8000/api/trade [POST]`

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
  from_token: string,
  from_amount: number,
  to_token: number,
  demo_init: 'demo_init', # Only for initialise demo account capital
  livetrade: 'livetrade', # Only for starting livetrade
  strategy: 'livetrade strategy',
  timeframe: 'livetrade timeframe'
}
Response:
{
  "from_token": string,
  "to_token": string,
  "from_amount": number,
  "to_amount": number,
  "time": datetime,
  "id": string
}
```

#### Example
```
Request: http://127.0.0.1:8000/api/trade
Authorization: Bearer ANY_VALID_TOKEN
Body:
{
  uid: "Gmcjdq33QxPSggpJx7CsTK42cQR2",
  from_token: "GBP",
  from_amount: 10,
  to_token: "ADA"
}
Response:
{
  "from_token": "GBP",
  "to_token": "ADA",
  "from_amount": 10,
  "to_amount": 32.234148857299424,
  "time": "2024-06-25T21:32:10.348844Z",
  "id": "4SbS6hjUdkWfh0jhvpR0"
}
```

#### Example Live Trade
```
Request: http://127.0.0.1:8000/api/trade
Authorization: Bearer ANY_VALID_TOKEN
Body:
{
  uid: "Gmcjdq33QxPSggpJx7CsTK42cQR2",
  from_token: 'GBP',
  from_amount: 10,
  to_token: "ADA",
  livetrade: 'livetrade',
  strategy: 'RSI74',
  timeframe: '1d'
}
Response:
{
  'id': 'SdDKsxUBEcrl6x73ptqz',
  'strategy': 'RSI74',
  'timeframe': '2024-06-25T21:32:10.348844Z',
  'token_id': 'BTC',
  'amount': 10000,
}
```

#### Example Initialise Account
```
Request: http://127.0.0.1:8000/api/trade
Authorization: Bearer ANY_VALID_TOKEN
Body:
{
  uid: "Gmcjdq33QxPSggpJx7CsTK42cQR2",
  from_token: "GBP",
  from_amount: 10000,
  demo_init: 'demo_init'
}
Response:
None
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
