# Mach D Trading
## Team member
- Aaron Barker
- Gerald Lee
- Jerry Chin

### Libraries Installation
```bash
pip install -r requirements.txt
```

#### To install TA-Lib

Windows x64

1. Download pip wheel (`TA_Lib-0.4.29-cp312-cp312-win_amd64.whl`) on https://github.com/cgohlke/talib-build/releases
2. Run
   ```bash
    pip install TA_Lib-0.4.29-cp312-cp312-win_amd64.whl
   ```

Linux

```bash
export TA_LIBRARY_PATH="/usr/lib"
export TA_INCLUDE_PATH="/usr/include"
sudo apt-get update
sudo apt-get install --y --no-install-recommends build-essential gcc wget
sudo apt clean
sudo wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz
tar -xvzf ta-lib-0.6.4-src.tar.gz
cd ta-lib-0.6.4
./configure --prefix=/usr
make
sudo make install
pip install ta-lib==0.6.3
cd ..
rm -rf ta-lib*
```

<hr />


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
FETCH_NEWS_IN_DAY="13" # When is the earliest news to fetch (E.g. 13 days before)
NEWS_EXPIRED_IN_DAY="14" # When will old news be deleted

DEMO_ACCOUNT_AMOUNT="10000"
MAX_TOKEN_HISTORY_IN_DAYS="7"
TOKEN_HISTORY_INTERVAL_IN_MINUTES="120"
FIAT="GBP"
TIMEFRAME_MAP="short->1h;medium->4h;long->1d"
BACKTEST_TIMEFRAME="60->1h;240->4h;1440->1d" # Do not use 1min for whole year data, server can't handle
BOT_NAME="MachD"
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

## <span style="color: #FF0000">**IMPORTANT FOR DEVELOPERS**</span>
### **Inaccurate Calculations**
- Use `utils.py > acc_calc(num1, op, num2, decimal_point)` for any calculations, especially money/token related
  - `num1` and `num2` can be in any form, including `float`, `int`, `str`, `Decimal`
  - `op` can be `+`, `-`, `*`, `/`, `%`, `//`, `==`, `!=`, `>`, `>=`, `<`, `<=`
  - `decimal_point` defaulted to 18, which is standard decimal points for cryptocurrencies
- <span style="color: #FF0000">**DO NOT**</span> perform your own calculation, as python has serious floating-point issue, especially on cryptocurrencies with many decimal points
  - Unless you perform necessary steps to prevent that


<hr />

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


<hr/>

## Local Scripts
### Convert and Upload Binance OHLC CSV Data to Firebase
1. Go to [Binance Data Website](https://www.binance.com/en-GB/landing/data)
2. Click **Spot** under **K-Line**
3. Select **Pairs**, **Interval** and **Dates**
4. Click **Confirm** and **Download**
5. Move the Files into their own folder
   - (`/Krakenbot/LocalScripts/binance_data/[timeframe]/[token]/*.csv`)
6. In `binance_to_candle.py`, change `combine_only = True`
7. Change `first_timestamp`, and `latest_timestamp` if needed
8. Run the file
9. Rename csv files' USDT to USD, as we save USD in our database, or convert USDT them using the next section instruction instead
10. Double confirm all the files are correct before uploading them to firebase
11. In `upload_csv_candles.py`, change `timeframe_dir` to 1440 and `batch_save=True`, and run the file
12. Re-run the file with different timeframe (60, 240)
13. For timeframe `1`, you will need `batch_save=False` since the data is too large
    - This operation will take some time over long period OHLC data

#### If need to convert currency into GBP
1. Move a combined `BTCUSDT_1.csv` back into `/Krakenbot/LocalScripts/binance_data/`
2. Download an external `BTCGBP_1.csv` (E.g. from [Bitfinex](https://www.cryptodatadownload.com/data/bitfinex/), but Bitfinex have only 1-hour data)
    - Bitfinex data's csv first line is a link, remove that
3. Move `BTCGBP_1.csv` into `/Krakenbot/LocalScripts/binance_data/` besides `BTCUSDT_1.csv`
4. In `binance_to_candle.py`, change `combine_only = False`, and change other variables if needed (Such as filenames, column names...)
5. Run the file again

<hr/>

### Upload Discover's About Content
1. Create a `'.docx'` file in `/Krakenbot/LocalScripts/discover/`
   - Save the file with token_id as name, E.g. `BTC.docx`
2. Run `upload_discover_content.py`
3. Check and enter 'Y' to save

<hr/>

### Upload Analysis Data to Firebase
1. Open up `analysis.csv` in `Krakenbot\LocalScripts\`
2. Add all analysis data under the columns<br/>
   **DO NOT** change/reorder the columns without updating `upload_analysis.py`
   - `tokens`: Token ID ***(E.g. BTC)***
   - `risk`: Risk of that Token + Goal ***(High / Medium / Low)***
   - `goal_length`: Financial goal of that analysis ***(Long / Medium / Short)***
   - `summary`: Short analysis/summary of that token + risk + goal
   - `analysis`: Long/Full version of analysis
   - `technical_analysis`: Technical version of analysis
3. Run `upload_analysis.py`
   - You will need `ENV` file with database credentials ready
    ```bash
    python Krakenbot/LocalScripts/upload_analysis.py
    ```

## Test Cases

Run `python manage.py test` to test the utils functions, trade and market endpoints
