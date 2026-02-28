import sys
import os
import time

# Ensure we can import from trading.data_fetcher
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from trading.data_fetcher import DataFetcher

def fetch_1h_data():
    fetcher = DataFetcher(exchange_id='binance')
    symbol = "BTC/USDT"
    timeframe = "1h"
    # Fetch 3 years of 1H data (2021-01-01 to roughly present)
    start_date = "2021-01-01"
    end_date = "2026-02-28"  # Use latest known good date
    
    print(f"--- Fetching Dedicated Domain Expert Data: {symbol} @ {timeframe} ---")
    try:
        # data_fetcher.py handles caching to CSV if 'save=True' (default)
        df = fetcher.fetch_historical(symbol, timeframe, start_date, end_date)
        print(f"[{symbol} {timeframe}] Fetched {len(df)} rows.")
        
        # Save explicitly to a dedicated file for LoRA training
        os.makedirs("../data", exist_ok=True)
        out_path = "../data/BTC_1h.csv"
        df.to_csv(out_path, index=False)
        print(f"✅ Successfully saved dataset to {out_path}")
        
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")

if __name__ == "__main__":
    fetch_1h_data()
