import pandas as pd
from trading.data_fetcher import DataFetcher
from crypto_simulator import CryptoSimulator
import datetime

sim = CryptoSimulator()
fetcher = sim.data_fetcher
symbol = "BTC/USDT"

print("Fetching historical data for backtesting...)")
# Fetch enough data to simulate a few steps
total_lookback = 400 + 12 * 5  # 5 prediction windows
df = fetcher.fetch_multi_timeframe(symbol, ["1h"], total_lookback)["1h"]

if df is not None:
    print(f"Total Rows: {len(df)}")
    
    # We will simulate making a prediction at various points and comparing to actual
    correct_dir = 0
    total = 0
    
    for i in range(400, len(df), 12):
        window_df = df.iloc[i-400:i].copy()
        
        if len(window_df) == 400:
            actual_start_close = window_df['close'].iloc[-1]
            try:
                pred_df = sim.predict(window_df)
                pred_end_close = pred_df['close'].iloc[-1]
                pred_dir = 1 if pred_end_close > actual_start_close else -1
                
                # Look ahead 12 bars in the original df
                if i + 12 <= len(df):
                    actual_end_close = df['close'].iloc[i + 12 - 1]
                    actual_dir = 1 if actual_end_close > actual_start_close else -1
                    
                    correct = pred_dir == actual_dir
                    if correct: correct_dir += 1
                    total += 1
                    
                    print(f"Step {total} | Start: {actual_start_close:.2f} | Pred: {pred_end_close:.2f} ({'UP' if pred_dir>0 else 'DN'}) | Actual: {actual_end_close:.2f} ({'UP' if actual_dir>0 else 'DN'}) | Correct: {correct}")
            except Exception as e:
                print(f"Error at step {i}: {e}")
                
    if total > 0:
        print(f"\n1H Directional Accuracy: {correct_dir/total*100:.2f}% ({correct_dir}/{total})")
