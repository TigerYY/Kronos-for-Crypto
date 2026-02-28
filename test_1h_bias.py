import pandas as pd
from trading.data_fetcher import DataFetcher
from crypto_simulator import CryptoSimulator

sim = CryptoSimulator()
fetcher = sim.data_fetcher
symbol = "BTC/USDT"

print(f"Fetching data for {symbol}...")
tf_dfs = fetcher.fetch_multi_timeframe(symbol, ["15m", "1h"], 400)

for tf, df in tf_dfs.items():
    print(f"\n--- {tf} ---")
    if df is not None:
        print(f"Latest Close: {df['close'].iloc[-1]}, Start Time: {df['timestamps'].iloc[0]}, End Time: {df['timestamps'].iloc[-1]}")
        try:
            pred_df = sim.predict(df)
            start_pred = df['close'].iloc[-1]
            end_pred = pred_df['close'].iloc[-1]
            change = (end_pred - start_pred) / start_pred * 100
            print(f"Predicted Final Close: {end_pred:.2f} ({change:+.2f}%)")
            
            # Print the actual predicted values
            print(f"Predicted Series: {[round(x, 2) for x in pred_df['close'].tolist()]}")
            
        except Exception as e:
            print(f"Prediction failed: {e}")
