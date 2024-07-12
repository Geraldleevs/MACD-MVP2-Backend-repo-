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
pip install aiohttp
pip install aiohttp asyncio

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
CORS="https://mach-d-rlqsy3.flutterflow.app/" # Split by ';'

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
FETCH_NEWS_IN_DAY="13" # When is the earliest news to fetch (E.g. 13 days before)
NEWS_EXPIRED_IN_DAY="14" # When will old news be deleted

DEMO_ACCOUNT_AMOUNT="10000"
MAX_TOKEN_HISTORY_IN_DAYS="7"
TOKEN_HISTORY_INTERVAL_IN_MINUTES="120"
FIAT="GBP"
TIMEFRAME_MAP="short->1h;medium->4h;long->1d"
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

Fetch history close price and update in firebase: `http://127.0.0.1:8000/api/update-history-prices [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/update-history-prices
Authorization: Bearer {Google_OIDC_Token}
Response:
None (Status: 200)
```

#### Example
```
Request: http://127.0.0.1:8000/api/update-history-prices
Authorization: Bearer ANY_VALID_TOKEN
Response:
None (Status: 200)
```
</details>

<hr/>

### Auto Livetrade

Check and perform livetrade based on backtest result: `http://127.0.0.1:8000/api/auto-livetrade [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/auto-livetrade
Authorization: Bearer {Google_OIDC_Token}
Body:
{
  "timeframe": '1min' | '5min' | '15min' | '30min' | '1h' | '4h' | '1d'
}
Response:
None (Status: 200)
```

#### Example
```
Request: http://127.0.0.1:8000/api/auto-livetrade
Authorization: Bearer ANY_VALID_TOKEN
Body:
{
  "timeframe": "1h"
}
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

Trade tokens: `http://127.0.0.1:8000/api/trade [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/trade
Authorization: Bearer {JWT_Token}
Body:
{
  "uid": string,
  "from_token": string,
  "from_amount": number,
  "to_token": number
}
Response:
{
  "from_token": string,
  "to_token": string,
  "from_amount": number,
  "to_amount": number,
  "time": datetime,
  "id": string,
  "operated_by": "User"
}
```

#### Example
```
Request: http://127.0.0.1:8000/api/trade
Authorization: Bearer ANY_VALID_TOKEN
Body:
{
  "uid": "Gmcjdq33QxPSggpJx7CsTK42cQR2",
  "from_token": "GBP",
  "from_amount": 10,
  "to_token": "ADA"
}
Response:
{
  "from_token": "GBP",
  "to_token": "ADA",
  "from_amount": 10,
  "to_amount": 32.234148857299424,
  "time": "2024-06-25T21:32:10.348844Z",
  "id": "4SbS6hjUdkWfh0jhvpR0",
  "operated_by": "User"
}
```
</details>

<hr/>

### Initialise Demo Account

Initialise Demo Account: `http://127.0.0.1:8000/api/trade [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/trade
Authorization: Bearer {JWT_Token}
Body:
{
  "uid": string,
  "demo_init": "demo_init"
}
Response:
None
```
</details>

<hr/>

### Start Live Trade

Start Live Trade: `http://127.0.0.1:8000/api/trade [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/trade
Authorization: Bearer {JWT_Token}
Body:
{
  "uid": string,
  "from_token": string,
  "from_amount": number,
  "to_token": number,
  "livetrade": "RESERVE",
  "strategy": string,
  "timeframe": string
}
Response:
{
  "id": string,
  "strategy": string,
  "timeframe": string,
  "token_id": string,
  "amount": number
}
```

#### Example
```
Request: http://127.0.0.1:8000/api/trade
Authorization: Bearer ANY_VALID_TOKEN
Body:
{
  "uid": "Gmcjdq33QxPSggpJx7CsTK42cQR2",
  "from_token": "GBP",
  "from_amount": 1000,
  "to_token": "DOGE",
  "livetrade": "reserve",
  "strategy": "RSI74",
  "timeframe": "1d"
}
Response:
{
  "id": "nlP3vMpnjDJLZHjO7U3t",
  "strategy": "RSI74",
  "timeframe": "1d",
  "token_id": "DOGE",
  "amount": 1000
}
```
</details>

<hr/>

### End Live Trade (Without Selling the tokens)

End Live Trade: `http://127.0.0.1:8000/api/trade [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/trade
Authorization: Bearer {JWT_Token}
Body:
{
  "uid": string,
  "livetrade": "UNRESERVE",
  "livetrade_id": string
}
Response:
None
```

#### Example
```
Request: http://127.0.0.1:8000/api/trade
Authorization: Bearer ANY_VALID_TOKEN
Body:
{
  "uid": "Gmcjdq33QxPSggpJx7CsTK42cQR2",
  "livetrade": "unreserve",
  "livetrade_id": "4uX4DPceT7opa9W0ky2l"
}
Response:
None
```
</details>

<hr/>

### End Live Trade (With selling the tokens)

Sell Live Trade: `http://127.0.0.1:8000/api/trade [POST]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/trade
Authorization: Bearer {JWT_Token}
Body:
{
  "uid": string,
  "to_token": string,
  "livetrade": "SELL",
  "livetrade_id": string
}
Response:
{
  "id": string,
  "time": datetime,
  "from_token": string,
  "from_amount": number,
  "to_token": string,
  "to_amount": number,
  "operated_by": "User"
}
```

#### Example
```
Request: http://127.0.0.1:8000/api/trade
Authorization: Bearer ANY_VALID_TOKEN
Body:
{
  "uid": "Gmcjdq33QxPSggpJx7CsTK42cQR2",
  "to_token": "GBP",
  "livetrade": "sell",
  "livetrade_id": "4uX4DPceT7opa9W0ky2l"
}
Response:
{
  "id": "NRmOjVjuJXs5KRWaxbDV",
  "time": "2024-07-03T00:01:44.277624Z",
  "from_token": "DOGE",
  "from_amount": 1000
  "to_token": "GBP",
  "to_amount": 100.99,
  "operated_by": "User"
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

### How to Deploy

1. Install [Docker](https://www.docker.com/products/docker-desktop/) and [GCloud CLI](https://cloud.google.com/sdk/docs/install)
2. Start Docker
3. Initialise GCloud CLI and Login
    ```bash
    gcloud init
    ```
4. Authorise Docker for GCloud
   ```bash
   gcloud auth configure-docker
   ```
5. (Optional) If you've already built the docker before, you need to dispose the old docker image first
   ```bash
   docker compose down --rmi local
   docker rmi gcr.io/[PROJECT_NAME]/machd-krakenbot:v0
   ```
6. Build Docker Image
   ```bash
   docker compose up
   # Ctrl + C after it is done building
   # Last Line should be 'Watching for file changes with StatReloader'
   ```
7. Push docker image to Google Cloud
   ```bash
   docker tag machd-krakenbot gcr.io/[PROJECT_NAME]/machd-krakenbot:v0
   docker push gcr.io/[PROJECT_NAME]/machd-krakenbot:v0
   ```
8. Navigate to [Google Cloud Run](https://console.cloud.google.com/run) and click into the `[PROJECT_NAME]`
9.  Click `Edit & deploy new revision`
10. Under `Container(s) > Edit Container > Container image URL`, click `SELECT`
11. Select the latest image (Should be the first one) under `Artifact Registry > gcr.io/[project-name] > machd-krakenbot`
12. If there is any new environment variable, add/edit under `Edit Container > Variables & Secrets`
13. Click `Deploy` at the bottom
