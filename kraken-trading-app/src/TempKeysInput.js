import React, { useState } from 'react';

const TempKeysInput = ({ onSubmit }) => {
  const [apiKey, setApiKey] = useState('');
  const [apiSec, setApiSec] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(apiKey, apiSec);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Enter API Key"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
      />
      <input
        type="text"
        placeholder="Enter API Secret"
        value={apiSec}
        onChange={(e) => setApiSec(e.target.value)}
      />
      <button type="submit">Submit</button>
    </form>
  );
};

export default TempKeysInput;
