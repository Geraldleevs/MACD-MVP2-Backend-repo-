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
`docker compose up`

`Ctrl + C to stop`

You **may** create a `.env` file to set the following env variables
```bash
DJANGO_SECRET_KEY="RandomSecretKeyForDjango"
PYTHON_ENV="development|production" # development for debug mode
PORT="8000"
```

## REST API Endpoints
### Recommendations
```
URL: http://127.0.0.1:8000/api/recommendations
Query: token_id, timeframe
Response:
[
  {
    "token": string,
    "strategy": string,
    "profit": number,
    "profit_percent": number,
    "summary": string,
    "strategy_description": string
  },
	...
]
```

#### Example
```
Request: http://127.0.0.1:8000/api/recommendations?token_id=btc&timeframe=4h
Response:
[
  {
    "token": "BTC",
    "strategy": "MACD & Donchian (Breakout and momentum confirmation, 1H)",
    "profit": 22713.315808518673,
    "profit_percent": 127.13315808518672,
    "summary": "Summary",
    "strategy_description": "Strategy Description"
  }
]
```

<hr/>

### Market
```
URL: http://127.0.0.1:8000/api/market
Query: token_id, timeframe
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

## Google Cloud Deployment
### Environment Variables
```bash
DJANGO_SECRET_KEY="SomeSecretKey"
PYTHON_ENV="deployment"
ADDRESS="0.0.0.0" # Must be set
# PORT is set somewhere else on Google Cloud, not in environment variable
```
