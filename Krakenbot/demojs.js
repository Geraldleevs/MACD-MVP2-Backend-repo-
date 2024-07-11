/**
 * @typedef {Object} DataFrame
 * @property {string} Timestamp - The date and time when the OHLC (Open, High, Low, Close) data was recorded. Typically in Unix time format or a readable datetime string.
 * @property {number} Open - The price of the asset at the start of the trading interval.
 * @property {number} High - The highest price of the asset during the trading interval.
 * @property {number} Low - The lowest price of the asset during the trading interval.
 * @property {number} Close - The price of the asset at the end of the trading interval.
 * @property {number} Volume - The total volume of the asset traded during the trading interval.
 * @property {number} Count - The number of trades that occurred during the trading interval.
 * 
 * @property {number} macd - The Moving Average Convergence Divergence (MACD) value for the current interval. It is calculated as the difference between a short-term and a long-term exponential moving average (EMA).
 * @property {number} signal - The MACD Signal Line, which is an EMA of the MACD line.
 * @property {number} histogram - The difference between the MACD line and the Signal line. It indicates the strength and direction of the trend.
 * @property {number} prev_histogram - The histogram value of the previous trading interval. Used to detect changes in trend direction.
 * 
 * @property {number} indicator_macd - The buy/sell signals specifically derived from the MACD indicator.
 * 
 * @property {number} sma_50 - The 50-period Simple Moving Average (SMA) of the closing prices.
 * @property {number} sma_200 - The 200-period Simple Moving Average (SMA) of the closing prices.
 * @property {number} sma_diff - The difference between the 50-period SMA and the 200-period SMA.
 * @property {number} prev_sma_diff - The sma_diff value of the previous trading interval. Used to detect changes in trend direction.
 * @property {number} indicator_sma - The buy/sell signals specifically derived from the SMA indicator.
 * 
 * @property {number} rsi - The Relative Strength Index (RSI) value, indicating overbought or oversold conditions. Typically ranges between 0 and 100.
 * @property {number} prev_rsi - The RSI value of the previous trading interval. Used to detect changes in trend direction.
 * @property {number} indicator_rsi70_30 - The buy/sell signals specifically derived from the RSI indicator with overbought and oversold thresholds set at 70 and 30, respectively.
 * 
 * @property {number} conversion_line - Part of the Ichimoku Cloud indicator, also known as Tenkan-sen, representing the midpoint of the 9-period high and low.
 * @property {number} base_line - Part of the Ichimoku Cloud indicator, also known as Kijun-sen, representing the midpoint of the 26-period high and low.
 * @property {number} leading_span_a - Part of the Ichimoku Cloud indicator, calculated as the midpoint between the conversion line and the base line, projected 26 periods into the future.
 * @property {number} leading_span_b - Part of the Ichimoku Cloud indicator, calculated as the midpoint of the 52-period high and low, projected 26 periods into the future.
 * @property {number} lagging_span - Part of the Ichimoku Cloud indicator, also known as Chikou Span, representing the closing price shifted 26 periods into the past.
 * @property {number} conversion_base_diff - The difference between the conversion line and the base line.
 * @property {number} prev_diff - The conversion_base_diff value of the previous trading interval. Used to detect changes in trend direction.
 * @property {number} indicator_ichimoku - The buy/sell signals specifically derived from the Ichimoku Cloud indicator.
 * 
 * @property {number} upper - The upper band of the Donchian Channel, representing the highest high over a specific period.
 * @property {number} lower - The lower band of the Donchian Channel, representing the lowest low over a specific period.
 * @property {number} mid - The midpoint between the upper and lower bands of the Donchian Channel.
 * @property {number} indicator_donchian_channel - The buy/sell signals specifically derived from the Donchian Channel indicator.
 * 
 * @property {number} %K - The %K line of the Stochastic Oscillator, representing the current closing price relative to the range of prices over a certain period.
 * @property {number} %D - The %D line of the Stochastic Oscillator, which is a moving average of the %K line.
 * @property {number} prev_%K - The %K value of the previous trading interval. Used to detect changes in trend direction.
 * @property {number} indicator_stochastic_14_3_80_20 - The buy/sell signals specifically derived from the Stochastic Oscillator indicator with a 14-period %K, 3-period %D, and overbought/oversold thresholds at 80/20.
 * 
 * @property {number} indicator_rsi_macd - Combined buy/sell signals derived from both the RSI and MACD indicators.
 * @property {number} indicator_sma_ichimoku - Combined buy/sell signals derived from both the SMA and Ichimoku Cloud indicators.
 * @property {number} indicator_donchian_stochastic - Combined buy/sell signals derived from both the Donchian Channel and Stochastic Oscillator indicators.
 */
