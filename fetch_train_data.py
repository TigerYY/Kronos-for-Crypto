from trading.data_fetcher import DataFetcher
import time

def fetch_data():
    fetcher = DataFetcher()
    symbols = ["ETH/USDT", "ES=F", "XAU/USDT"]
    start_date = "2024-01-01"
    end_date = "2026-02-25"
    
    # 各 symbol 数据可用起始日期映射
    symbol_start = {
        "ETH/USDT":  start_date,
        "ES=F":      "2024-06-01",  # yfinance 分钟级数据限制
        "XAU/USDT": "2023-01-01",  # Binance 永续合约，无时间限制，拉取更长历史
    }

    print("Fetching training data...")
    for symbol in symbols:
        try:
            cur_start = symbol_start.get(symbol, start_date)
            df = fetcher.fetch_historical(symbol, "1h", cur_start, end_date)
            print(f"[{symbol}] Fetched {len(df)} rows.")
            time.sleep(2)  # Avoid rate limits
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

if __name__ == "__main__":
    fetch_data()
