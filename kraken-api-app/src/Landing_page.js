import React, { useState } from "react"
import "./styles.css"

export default function App() {
  const [indicator1, setIndicator1] = useState("")
  const [indicator2, setIndicator2] = useState("")
  const [fiatValue, setFiatValue] = useState("")
  const [token, setToken] = useState("")

  const indicatorFunctions = [
    "EMA",
    "MACD",
    "Ichimoku Cloud",
    "ATR",
    "Donchian Channels",
    "RSI",
    "Bollinger Bands",
  ]

  const tokenList = ["BTC", "ETH", "APE", "CHZ", "DOG", "LIN", "MAN", "UNI"]

  const handleBacktest = () => {
    // Here you would call the backtest function or API endpoint with the selected values
    console.log(
      `Backtesting with Indicator 1: ${indicator1}, Indicator 2: ${indicator2}, Fiat Value: ${fiatValue}, Token: ${token}`
    )
  }

  return (
    <div className="App">
      <h1>Mach D Trading Bot Demo</h1>

      <div>
        <label>Select Indicator 1:</label>
        <select
          value={indicator1}
          onChange={e => setIndicator1(e.target.value)}
        >
          <option value="">--Select--</option>
          {indicatorFunctions.map(indicator => (
            <option key={indicator} value={indicator}>
              {indicator}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label>Select Indicator 2:</label>
        <select
          value={indicator2}
          onChange={e => setIndicator2(e.target.value)}
        >
          <option value="">--Select--</option>
          {indicatorFunctions.map(indicator => (
            <option key={indicator} value={indicator}>
              {indicator}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label>Enter Fiat Value:</label>
        <input
          type="number"
          value={fiatValue}
          onChange={e => setFiatValue(e.target.value)}
        />
      </div>

      <div>
        <label>Select Token:</label>
        <select value={token} onChange={e => setToken(e.target.value)}>
          <option value="">--Select--</option>
          {tokenList.map(t => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      <button onClick={handleBacktest}>Backtest</button>
    </div>
  )
}
