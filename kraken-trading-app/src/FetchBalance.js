import React, { useState } from 'react';
import axios from 'axios';

const FetchBalance = () => {
  const [balance, setBalance] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);

    const url = 'http://localhost:5000/api/kraken';
    const data = {
      urlPath: '/0/private/Balance',
      data: { nonce: Date.now() },
    };

    try {
      const response = await axios.post(url, data);
      setBalance(response.data);
    } catch (error) {
      console.error('Error fetching data:', error.response.data);
    }

    setLoading(false);
  };

  return (
    <div>
      <h2>Fetch Balance</h2>
      <button onClick={fetchData} disabled={loading}>
        {loading ? 'Loading...' : 'Fetch Balance'}
      </button>
      {balance && (
        <div>
          <h3>Balance:</h3>
          <pre>{JSON.stringify(balance, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default FetchBalance;
