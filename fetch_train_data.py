from trading.data_fetcher import DataFetcher
import time

def fetch_data():
    fetcher = DataFetcher()
    symbols = ["ETH/USDT", "ES=F"]
    start_date = "2024-01-01"
    end_date = "2026-02-25"
    
    print("Fetching training data...")
    for symbol in symbols:
        try:
            cur_start = "2024-06-01" if symbol == "ES=F" else start_date
            df = fetcher.fetch_historical(symbol, "1h", cur_start, end_date)
            print(f"[{symbol}] Fetched {len(df)} rows.")
            time.sleep(2)  # Avoid rate limits
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

if __name__ == "__main__":
    fetch_data()
