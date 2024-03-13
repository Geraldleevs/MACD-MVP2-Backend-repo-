import React, { useState } from 'react';
import axios from 'axios';
import TempKeysInput from './TempKeysInput';
import TradingLogic from './TradingLogic';

const App = () => {
  const [apiKey, setApiKey] = useState('');
  const [apiSec, setApiSec] = useState('');

  const handleTempKeysSubmit = (apiKey, apiSec) => {
    setApiKey(apiKey);
    setApiSec(apiSec);
  };

  return (
    <div>
      <h1>Kraken API Trading</h1>
      {apiKey && apiSec ? (
        <TradingLogic apiKey={apiKey} apiSec={apiSec} />
      ) : (
        <TempKeysInput onSubmit={handleTempKeysSubmit} />
      )}
    </div>
  );
};

export default App;
