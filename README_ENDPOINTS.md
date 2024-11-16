# Endpoints
- [Market](#market)
- [Simulation](#simulation)
- [Backtest](#backtest)
- [Update Last Close](#update-last-close)
- [Auto Livetrade](#auto-livetrade)
- [Check Order Book](#check-order-book)
- [Check Stop Loss & Take Profit](#check-stop-loss--take-profit)
- [News](#news)
- [Initialise Demo](#initialise-demo)
- [LiveTrade](#livetrade)
- [Orders](#orders)
- [Trade](#trade)
- [Update Candles](#update-candles)

---

# Market

`/api/market [GET]`

Fetch current market price for tokens from Kraken

Redirects to `/api/simulation` with `get_simulation=GET SIMULATION`

### Query Parameters:
- `convert_from`: `string` (Optional)
	- Specify which token to convert from
	- If not provided, `convert_to` will be used to fetch prices for `ALL TOKEN -> convert_to`
- `convert_to`: `string` (Optional)
	- Specify which token to convert to
	- If not provided, `convert_from` will be used to fetch prices for `convert_from -> ALL TOKEN`
- `exclude`: `string` (Optional)
	- Specify which token to exclude from the response
	- Usually used to exclude `convert_from` or `convert_to` token
- `force_convert`: `"FORCE"` (Optional)
	- If `"FORCE"` is given, all prices will be converted to GBP
	- Can only be used when convert from/to GBP
- `include_inactive`: `"INCLUDE"`
	- If `"INCLUDE"` is given, inactive tokens will also be fetched
- `get_simulation`: `"GET SIMULATION"`
  - IF `"GET SIMULATION"` is given, redirects to `/api/simulation`

### Response:
- `token`: `string`
	- ID of the cryptocurrency / fiat
- `price`: `number`
	- Price of the token in number
- `price_str`: `string`
	- Price of the token in string
- `last_close`: `number`
	- Close price of previous day

### Examples

Example 1: `/api/market?convert_from=eth&convert_to=btc`

#### Response
```bash
[
	{
		"token": "BTC",
		"price": 0.055080, # ETH -> BTC
		"last_close": 0.055080
	}
]
```

Example 2: `/market?convert_from=gbp&force_convert=force&include_inactive=include`

#### Response
```bash
[
	{
		"token": "BTC",
		"price": ..., # GBP -> BTC
		"last_close": ...
	},
	{
		"token": "1INCH",
		"price": ..., # Price converted from USD->1INCH
		"last_close": ...
	}
]
```

---

# Simulation

`/api/simulation [GET]`

Get simulation data or backtest strategies

### Query Parameters:
- `get_strategies`: `"GET STRATEGIES"` (Optional)
	- If `"GET STRATEGIES"` provided, return all backtest strategy combinations
- `convert_from`: `string`
	- Specify which token is used for the simulation, usually fiat
- `convert_to`: `string`
	- Specify which token to simulate the trades, usually cryptocurrency
- `strategy`: `string` (Optional)
	- Strategy that must be in the list fetched using `get_strategies`
	- If both strategy and timeframe are not provided, the simulation will be without backtest decisions
- `timeframe`: `string` (Optional)
	- Timeframe for the backtest, E.g. 1h, 4h, 1d
	- If both strategy and timeframe are not provided, the simulation will be without backtest decision

### Response:
- `simulation_data`: `list[number]`
	- List of simulation data, can be used for graph display
	- 120 simulation data
- `graph_min`: `number`
	- Min of the data, with the starting data as centre
	- Can be used as min of graph for starting data to be at centre
- `graph_max`: `number`
	- Max of the data, with the starting data as centre
	- Can be used as max of graph for starting data to be at centre
- `funds_values`: `list[number]`
	- Funds of each data point
	- 120 data
- `bot_actions`: `list[number]`
	- Buy/Sell actions made by the bot
	- `-1`: Sell: `0`: No action, `1`: Buy
	- 120 decision data
- `stopped_by`: `None | "stop loss limit" | "target limit"`
	- Indicate if the simulation is stopped by stop loss limit or target limit
- `stopped_at`: `number`
	- When was it stopped

### Examples

Example 1: `/api/simulation?convert_from=gbp&convert_to=btc`

#### Response
```bash
{
	"simulation_data": [1, 2, 1, 2, 1, ...],
	"graph_min": -1,
	"graph_max": 2
}
```

Example 2: `/api/simulation?convert_from=gbp&convert_to=btc&strategy=MACD %26 Aroon&timeframe=1d&funds=500&stop_loss=400&take_profit=600`

#### Response
```bash
{
	"simulation_data": [1, 2, 1, 2, 1, ...],
	"graph_min": -1,
	"graph_max": 2,
	"funds_values": [500, 490, 510, ...]
	"bot_actions": [0, 1, -1, 0, ...]
	"stopped_by": 'stop loss limit'
	"stopped_at": 79
}
```

Example 3: `/api/simulation?get_strategies=GET STRATEGIES`

#### Response
```bash
[
	"Strategy 1",
	"Strategy 2",
	...
]
```

---

# Backtest

`/api/backtest [POST]`

Run backtest and save the recommended strategy in firebase

### Authorisation:
- `Bearer {Google_OIDC_Token}`

### Response:
- `STATUS 200`

### Examples

Example 1: `/api/backtest`

#### Data:
```bash
Authorization: Bearer {Google_OIDC_Token}
```

#### Response
```bash
STATUS 200
```

---

# Update Last Close

`/api/update-history-prices [POST]`

Fetch token's OHLC, all token metrics and update user's wallet value in firebase

### Authorisation:
- `Bearer {Google_OIDC_Token}`

### Response:
- `STATUS 200`

### Examples

Example 1: `/api/update-history-prices`

#### Data:
```bash
Authorization: Bearer {Google_OIDC_Token}
```

#### Response
```bash
STATUS 200
```

---

# Auto Livetrade

`/api/auto-livetrade [POST]`

Check and perform livetrade based on backtest result

### Request Data:
- `timeframe`: `"1min" | "5min" | "15min" | "30min" | "1h" | "4h" | "1d"`
	- Specify which timeframe's livetrades to be checked

### Authorisation:
- `Bearer {Google_OIDC_Token}`

### Response:
- `STATUS 200`

### Examples

Example 1: `/api/auto-livetrade`

#### Data:
```bash
Authorization: Bearer {Google_OIDC_Token}
Data: { "timeframe": "1min" }
```

#### Response
```bash
STATUS 200
```

---

# Check Order Book

`/api/check-orders [POST]`

Check and perform orders

### Authorisation:
- `Bearer {Google_OIDC_Token}`

### Response:
- `STATUS 200`

### Examples

Example 1: `/api/check-orders`

#### Data:
```bash
Authorization: Bearer {Google_OIDC_Token}
```

#### Response
```bash
STATUS 200
```

---

# Check Stop Loss & Take Profit

`/api/check-lossprofit [POST]`

Check and perform stop loss and take profit

### Authorisation:
- `Bearer {Google_OIDC_Token}`

### Response:
- `STATUS 200`

### Examples

Example 1: `/api/check-lossprofit`

#### Data:
```bash
Authorization: Bearer {Google_OIDC_Token}
```

#### Response
```bash
STATUS 200
```

---

# News

`/api/news [POST]`

Fetch GNews and save in firebase database

### Authorisation:
- `Bearer {Google_OIDC_Token}`

### Response:
- `STATUS 200`

### Examples

Example 1: `/api/news`

#### Data:
```bash
Authorization: Bearer {Google_OIDC_Token}
```

#### Response
```bash
STATUS 200
```

---

# Initialise Demo

`/api/initialise-demo [POST]`

Initialise account with demo amount

### Authorisation:
- `Bearer {JWT_TOKEN}`
	- User's JWT Token assigned by firebase

### Request Data:
- `uid`: `string`
	- User's ID

### Response:
- `STATUS 200`

### Examples

Example 1: `/api/news`

#### Data:
```bash
Authorization: Bearer {User_JWT_Token}
Data: { "uid": "User ID" }
```

#### Response
```bash
STATUS 200
```

---

# LiveTrade

`/api/livetrade [POST]`

Create, Update and Close Livetrades

### Authorisation:
- `Bearer {JWT_TOKEN}`
	- User's JWT Token assigned by firebase

### Request Data:
- `uid`: `string`
	- User's ID
- `livetrade`: `"RESERVE" | "UPDATE" | "UNRESERVE" | "SELL"`
	- `RESERVE`: Create a bot and place the first order
	- `UPDATE`: Update take profit and/or stop loss of a bot
	- `UNRESERVE`: Close a bot and release the amount hold by the bot
	- `SELL`: Unreserve the bot and sell the token back to fiat
- `livetrade_id`: `string`
	- ID for the bot to act on
	- *Required for `UPDATE`, `UNRESERVE` and `SELL`
- `from_token`: `string`
	- Token ID used for the investment, usually fiat (GBP/USD)
	- *Required for `RESERVE`
- `to_token`: `string`
	- ID for the Token to invest on (E.g. BTC)
	- *Required for `RESERVE`
- `from_amount`: `string | number`
	- Amount to reserve for the trade
	- *Required for `RESERVE`
- `strategy`: `string`
	- Backtest strategy of the livetrade
	- *Required for `RESERVE`
- `timeframe`: `string`
	- Backtest timeframe of the livetrade process
	- *Required for `Reserve`
- `take_profit`: `string | number` (Optional)
	- Take profit limit for the bot to stop
- `stop_loss`: `string | number` (Optional)

### Response:
- `uid`: `string`
	- ID of the user who created the bot
- `livetrade_id`: `string`
	- ID for the bot
- `strategy`: `string`
	- Backtest strategy used by the bot
- `timeframe`: `string`
	- Backtest timeframe used by the bot
- `name`: `string`
	- Name of the bot
- `is_active`: `boolean`
	- Status of the bot
- `start_time`: `DateTime`
	- Time of the bot was created
- `initial_amount`: `number`
	- Initial investment amount in fiat
- `initial_amount_str`: `string`
	- Initial investment amount in string format
- `amount`: `number`
	- Amount of token currently holding
- `amount_str`: `string`
	- Amount of token holding in string format
- `fiat`: `string`
	- Fiat used for this bot investment
- `cur_token`: `string`
	- Current token the bot is holding (Either fiat or token invested)
- `token_id`: `string`
	- Token that will be invested by the bot
- `order_id`: `string`
	- The ID of the latest order placed by the bot (May be completed)
- `status`: `string`
	- `READY_TO_TRADE`: The bot is active and waiting for backtest signal to trade
	- `ORDER_PLACED`: The bot has placed an order and waiting for the order to complete
	- `COMPLETED`: The bot is closed
	- `STOP_LOSS`: The bot has hit the stop loss limit and stopped (Order may not be completed yet)
	- `TAKING_PROFIT`: The bot has hit the profit limit and stopped (Order may not be completed yet)
- `stop_loss`: `number`
	- Stop loss limit assigned to the bot
- `take_profit`: `number`
	- Take profit limit assigned to the bot

### Examples

Example 1: `/api/livetrade`

- Create bot

#### Data:
```bash
Authorization: Bearer {User_JWT_Token}
Data:
{
	"uid": "User ID",
	"livetrade": "RESERVE",
	"from_token": "GBP",
	"to_token": "ETH",
	"from_amount": 500,
	"strategy": "RSI70_30 & DX",
	"timeframe": "1d",
	"take_profit": 600,
	"stop_loss": 400
}
```

#### Response
```bash
{
	"uid": "cppe1M0W2ReOb5LdTuxTSRa2mw23",
	"livetrade_id": "09CqLdnNEUkZAYBts3Im",
	"strategy": "CCI & WilliamsR (General trend and momentum analysis, 1H)",
	"timeframe": "1h",
	"name": "MachD-133",
	"is_active": true,
	"start_time": October 19, 2024 at 9:07:15 AM UTC+1,
	"initial_amount": 500,
	"initial_amount_str": "500",
	"amount": 500,
	"amount_str": "500",
	"fiat": "GBP",
	"cur_token": "GBP",
	"token_id": "ETH",
	"order_id": "10Hg4CkxlzuZHlIkTJj9",
	"status": "ORDER_PLACED",
	"take_profit": 600,
	"stop_loss": 400,
	"order": { ... }
}
```

Example 2: `/api/livetrade`

- Update bot's Take Profit and/or Stop Loss

#### Data:
```bash
Authorization: Bearer {User_JWT_Token}
Data:
{
	"uid": "User ID",
	"livetrade": "UDPATE",
	"livetrade_id": "09CqLdnNEUkZAYBts3Im",
	"take_profit": 700,
	"stop_loss": 300
}
```

#### Response
```bash
{
	"uid": "cppe1M0W2ReOb5LdTuxTSRa2mw23",
	"livetrade_id": "09CqLdnNEUkZAYBts3Im",
	"strategy": "CCI & WilliamsR (General trend and momentum analysis, 1H)",
	"timeframe": "1h",
	"name": "MachD-133",
	"is_active": true,
	"start_time": October 19, 2024 at 9:07:15 AM UTC+1,
	"initial_amount": 500,
	"initial_amount_str": "500",
	"amount": 500,
	"amount_str": "500",
	"fiat": "GBP",
	"cur_token": "GBP",
	"token_id": "ETH",
	"order_id": "10Hg4CkxlzuZHlIkTJj9",
	"status": "ORDER_PLACED",
	"take_profit": 700,
	"stop_loss": 300
}
```

Example 3: `/api/livetrade`

- Sell Bot

#### Data:
```bash
Authorization: Bearer {User_JWT_Token}
Data:
{
	"uid": "User ID",
	"livetrade": "SELL",
	"livetrade_id": "09CqLdnNEUkZAYBts3Im"
}
```

#### Response
```bash
{
	"uid": "cppe1M0W2ReOb5LdTuxTSRa2mw23",
	"livetrade_id": "09CqLdnNEUkZAYBts3Im",
	"strategy": "CCI & WilliamsR (General trend and momentum analysis, 1H)",
	"timeframe": "1h",
	"name": "MachD-133",
	"is_active": false,
	"start_time": October 19, 2024 at 9:07:15 AM UTC+1,
	"closed_time": October 19, 2024 at 9:15:15 AM UTC+1,
	"initial_amount": 500,
	"initial_amount_str": "500",
	"amount": 500,
	"amount_str": "500",
	"fiat": "GBP",
	"cur_token": "GBP",
	"token_id": "ETH",
	"order_id": "10Hg4CkxlzuZHlIkTJj9",
	"status": "COMPLETED",
	"take_profit": 700,
	"stop_loss": 300,
	"order": { ... }
}
```

---

# Orders

`/api/order [POST]`

Create or cancel order

### Authorisation:
- `Bearer {JWT_TOKEN}`
	- User's JWT Token assigned by firebase

### Request Data:
- `uid`: `string`
	- User's ID
- `from_token`: `string`
	- Token used for the trade
- `to_token`: `string`
	- Token to trade for
- `from_amount`: `string`
	- Amount to trade
- `order`: `"ORDER" | "CANCEL"`
	- `ORDER`: Place order
	- `CANCEL`: Cancel order
- `order_price`: `string`
	- Price to bid for this order
- `order_id`: `string`
	- Used when cancelling order

### Response:
- `order_id`: `string`
  - ID of this order
- `uid`: `string`
  - ID of the user created this order (even if it is created by bot)
- `from_token`: `string`
  - Token to trade from
- `to_token`: `string`
  - Token to trade to
- `price`: `number`
  - Bid price of this order
- `price_str`: `string`
  - Bid price in string format
- `volume`: `string`
  - Amount of token used for this trade
- `created_time`: `DateTime`
  - Creation time of this order
- `closed_time`: `DateTime`
  - Closed time of this order
- `status`: `"OPEN" | "COMPLETED" | "CANCELLED"`
  - `OPEN` indicates that the order is opened, waiting to be completed
  - `COMPLETED` indicates that the order is fulfilled
  - `CANCELLED` indicates that the order is cancelled
- `created_by`: `string`
  - `USER` indicates that the order is created by user, manually
  - If this order is created by a bot, the bot name will be used
- `bot_id`: `string`
  - The ID of the bot who created this order
  - None if it is created by user

### Examples

Example 1: `/api/order`

- Create order

#### Data:
```bash
Authorization: Bearer {User_JWT_Token}
Data:
{
	"uid": "User ID",
	"from_token": "BTC",
	"to_token": "GBP",
	"from_amount": 0.05,
	"order": "ORDER",
	"order_price": 52350
}
```

#### Response
```bash
{
  order_id: "0cF3WoZDCaLEKUzbCNU3"
  uid: "cppe1M0W2ReOb5LdTuxTSRa2mw23"
  from_token: "GBP"
  to_token: "ETH"
  price: 52350
  price_str: "52350"
  volume: "0.05"
  created_time: October 28, 2024 at 4:00:06 AM UTC
  closed_time: null
  status: "OPEN"
  created_by; "USER"
	bot_id: null
}
```

Example 2: `/api/order`

- Cancel an order

#### Data:
```bash
Authorization: Bearer {User_JWT_Token}
Data:
{
	"uid": "User ID",
	"order": "CANCEL",
	"order_id": "0cF3WoZDCaLEKUzbCNU3"
}
```

#### Response
```bash
{
  order_id: "0cF3WoZDCaLEKUzbCNU3"
  uid: "cppe1M0W2ReOb5LdTuxTSRa2mw23"
  from_token: "GBP"
  to_token: "ETH"
  price: 52350
  price_str: "52350"
  volume: "0.05"
  created_time: October 28, 2024 at 4:00:06 AM UTC
  closed_time: October 28, 2024 at 5:00:06 AM UTC
  status: "CANCELLED"
  created_by; "USER"
	bot_id: null
}
```

---

# Trade

`/api/trade [POST]`

Redirect Trades to
- Initialise demo account
- Create/Cancel Orders
- Create/Update/Close bots

### Authorisation:
- Same as `/api/livetrade`, `/api/order` and `/api/demo`

### Request Data:
- Either set from `/api/livetrade`, `/api/order` or `/api/demo`

### Response:
- Result from `/api/livetrade`, `/api/order` or `/api/demo`

### Examples

Example 1: `/api/trade`

- Create order

#### Data:
```bash
Authorization: Bearer {User_JWT_Token}
Data:
{
	"uid": "User ID",
	"from_token": "BTC",
	"to_token": "GBP",
	"from_amount": 0.05,
	"order": "ORDER",
	"order_price": 52350
}
```

#### Response
```bash
{
  order_id: "0cF3WoZDCaLEKUzbCNU3"
  uid: "cppe1M0W2ReOb5LdTuxTSRa2mw23"
  from_token: "GBP"
  to_token: "ETH"
  price: 52350
  price_str: "52350"
  volume: "0.05"
  created_time: October 28, 2024 at 4:00:06 AM UTC
  closed_time: null
  status: "OPEN"
  created_by; "USER"
	bot_id: null
}
```

---

# Update Candles

`/api/update-candles [POST]`

Fetch candles and save in firebase

### Authorisation:
- `Bearer {Google_OIDC_Token}`

### Response:
- `STATUS 200`

### Examples

Example 1: `/api/update-candles`

#### Data:
```bash
Authorization: Bearer {Google_OIDC_Token}
```

#### Response
```bash
STATUS 200
```

---

### Recalibrate Bot

`/api/recalibrate-bot [POST]`

Recalibrate Bot Amount from Livetrades, only work on development server

### Response:
- `STATUS 200`

### Examples

Example 1: `/api/recalibrate-bot`

#### Response
```bash
STATUS 200
```
