const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(bodyParser.json());

const getKrakenSignature = (urlPath, data, apiSec) => {
  const postData = new URLSearchParams(data).toString();
  const nonce = new Date().getTime() * 1000;
  const message = urlPath + postData + nonce;
  const secret = Buffer.from(apiSec, 'base64');
  const hash = crypto.createHash('sha256').update(message).digest();
  const hmac = crypto.createHmac('sha512', secret);
  const signature = hmac.update(urlPath + hash).digest('base64');
  return {
    'API-Key': data.api_key,
    'API-Sign': signature,
    'API-Nonce': nonce,
    'Content-Type': 'application/x-www-form-urlencoded',
  };
};

app.post('/api/kraken', async (req, res) => {
  try {
    const { urlPath, data, apiKey, apiSec } = req.body;
    const headers = getKrakenSignature(urlPath, data, apiSec);
    const response = await axios.post(`https://api.kraken.com${urlPath}`, data, { headers });
    res.json(response.data);
  } catch (error) {
    console.error('Error making Kraken request:', error.response.data);
    res.status(error.response.status || 500).json({ error: error.response.data });
  }
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

const cors = require('cors');
app.use(cors({
  origin: 'https://your-frontend-domain.com', // Replace with your frontend URL
  optionsSuccessStatus: 200,
}));