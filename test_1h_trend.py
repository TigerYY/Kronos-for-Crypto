import pandas as pd
import numpy as np
from trading.data_fetcher import DataFetcher
import json

fetcher = DataFetcher(exchange_id='binance')
symbol = "BTC/USDT"
tf_dfs = fetcher.fetch_multi_timeframe(symbol, ["15m", "1h"], 400)

for tf, df in tf_dfs.items():
    if df is not None:
        closes = df['close'].values
        start_price = closes[0]
        end_price = closes[-1]
        min_price = np.min(closes)
        max_price = np.max(closes)
        trend = (end_price - start_price) / start_price * 100
        print(f"--- {tf} History (400 bars) ---")
        print(f"Start: {start_price:.2f}, End: {end_price:.2f}, Trend: {trend:+.2f}%")
        print(f"Min: {min_price:.2f}, Max: {max_price:.2f}")
