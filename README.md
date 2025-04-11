## How to Setup

### Environment

- `Python 3.13`
- `Ubuntu 24.04.1 LTS`

### 1. Install TA Lib 0.6.4

```bash
export TA_LIBRARY_PATH="/usr/lib"
export TA_INCLUDE_PATH="/usr/include"
cd /tmp
sudo apt-get update
sudo apt-get install --y --no-install-recommends build-essential gcc wget
sudo apt clean
sudo wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz
tar -xvzf ta-lib-0.6.4-src.tar.gz
cd ta-lib-0.6.4
./configure --prefix=/usr
make
sudo make install
cd ..
rm -rf ta-lib*
```

### 2. Install Python 3.13 and Virtual Env

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.13 python3.13-dev
sudo apt install pipx
pipx ensurepath
pipx install virtualenv
```

### 3. Clone this repository

```bash
git clone ...
cd MachD
```

### 4. Create Virtual Env and Install pip packages

```bash
virtualenv -p /usr/bin/python3.13 .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Create `.env` file

```bash
cp .env-template .env
# Changes are not needed for local development
```

### 6. Run migrations

```bash
python manage.py migrate
```

### 7. Download and Import Binance data

```bash
python manage.py download_binance_data
python manage.py import_binance_data
```

### 8. Start development server

```bash
python manage.py runserver
```

## How to Deploy

### 1. Install Docker

```bash
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
	"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
	$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
	sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 2. Install GCloud CLI

```bash
sudo apt-get update
sudo apt-get install apt-transport-https ca-certificates gnupg curl
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install google-cloud-cli
gcloud init
# Follow the instructions to login, and Select the project code
```

### 3. Authorise Docker

```bash
gcloud auth configure-docker
```

### 4. Build Docker Container

```bash
docker compose down --rmi local  # Remove all existing container and images to avoid reusign cached images
docker rmi gcr.io/mach-d-rlqsy3/machd:v0
docker compose build
```

### 5. Push to Google Cloud

```bash
gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin gcr.io
docker tag machd-machd gcr.io/mach-d-rlqsy3/machd:v0
docker push gcr.io/mach-d-rlqsy3/machd:v0
```

### 6. Deploy on Google Cloud Run

1. Navigate to [Google Cloud Run](https://console.cloud.google.com/run) and click into the `mach-d-rlqsy3`
2. Click `Edit & deploy new revision`
3. Under `Container(s) > Edit Container > Container image URL`, click `SELECT`
4. Select the latest image (the one with `v0` tag) under `Artifact Registry > gcr.io/mach-d-rlqsy3/machd`
5. If there is any new environment variable, add/edit under `Edit Container > Variables & Secrets`
6. Click `Deploy` at the bottom
