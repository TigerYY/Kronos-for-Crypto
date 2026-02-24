"""
OHLCV data service. Uses DataFetcher from trading (no model load).
"""
import os
import sys

# Ensure project root on path when backend is run as module
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from trading.data_fetcher import DataFetcher

_fetcher: DataFetcher | None = None


def get_fetcher() -> DataFetcher:
    global _fetcher
    if _fetcher is None:
        _fetcher = DataFetcher(exchange_id="binance")
    return _fetcher


def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 512) -> list[dict]:
    """Fetch OHLCV and return list of dicts (JSON-serializable)."""
    df = get_fetcher().fetch_ohlcv(symbol, timeframe, limit=limit)
    if df is None or df.empty:
        return []
    df = df.copy()
    df["timestamps"] = df["timestamps"].astype(str)
    return df.to_dict(orient="records")
