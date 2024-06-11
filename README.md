# Mach D Trading
## Team member
- Aaron Barker
- Gerald Lee
- Jerry Chin

### Libraries Installation
`pip install -r requirements.txt`
`pip install numpy`
`pip install pandas`
`pip install streamlit`
`pip install django`
`pip install djangorestframework`

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

### REST API Endpoints
#### Recommendations
```
URL: http://127.0.0.1:8000/recommendations
Query: token_id, timeframe
Response:
[
	{
		"token": string,
		"strategy": string,
		"profit": number,
		"profit_percent": number
	},
	...
]
```

##### Example
```
Request: http://127.0.0.1:8000/recommendations?token_id=btc&timeframe=4h
Response:
[
	{
		"token": "Concatenated-BTCUSDT-4h-2023-4-concatenated",
		"strategy": "MACD & Donchian (Breakout and momentum confirmation, 1H)",
		"profit": 22713.315808518673,
		"profit_percent": 127.13315808518672
	}
]
```
