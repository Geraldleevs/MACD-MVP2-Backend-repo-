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
```

### running on streamlit
`python -m streamlit run Krakenbot\StreamLit_Livetrading.py`

### CSV for downloaded binance header
`open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore` - Binance default
`open_time,Open,High,Low,Close,Volume,Close_time,Quote_volume,Count,Taker_buy_volume,Taker_buy_quote_volume,Ignore` - Mach D usable

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

You **may** create a `.env` file to set the following env variables
```bash
DJANGO_SECRET_KEY="RandomSecretKeyForDjango"
PYTHON_ENV="development|production" # development for debug mode
PORT="8000"
```

## REST API Endpoints
### Recommendations

Fetch recommendations: `http://127.0.0.1:8000/api/recommendation [GET]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/recommendation
Query: token_id, timeframe
Response:
[
  {
    "token_id": string,
    "timeframe": string,
    "strategy": string,
    "profit": number,
    "profit_percent": number,
    "summary": string,
    "strategy_description": string,
    "updated_on": Date
  },
  ...
]
```

#### Example
```
Request: http://127.0.0.1:8000/api/recommendation?token_id=btc&timeframe=4h
Response:
[
  {
    "token_id": "BTC",
    "timeframe": "4h",
    "strategy": "MACD & Donchian (Breakout and momentum confirmation, 1H)",
    "profit": 22713.315808518673,
    "profit_percent": 127.13315808518672,
    "summary": "Summary",
    "strategy_description": "Strategy Description"
    "updated_on": "2024-06-17T14:22:20.913234Z"
  }
]
```
</details>

<hr/>

### Market

Fetch market prices: `http://127.0.0.1:8000/api/market [GET]`

<details>
<summary>
Endpoint details
</summary>

```
URL: http://127.0.0.1:8000/api/market
Query: token_id
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
Request: http://127.0.0.1:8000/api/market?token_id=eth
Response:
[
  {
    "token": "ETH",
    "price": 2725.45
  }
]
```
</details>

<hr/>

### Backtest

Trigger backtest and save in database: `http://127.0.0.1:8000/api/backtest [POST]`

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

## Google Cloud Deployment
### Environment Variables
```bash
DJANGO_SECRET_KEY="SomeSecretKey"
GCLOUD_EMAIL="....@...iam.gserviceaccount.com" # For scheduler API call for backtest
API_URL="THIS CLOUD API URL" # For backtest API
PYTHON_ENV="deployment"
ADDRESS="0.0.0.0" # Must be set
# PORT is set somewhere else on Google Cloud, not in environment variable
```
