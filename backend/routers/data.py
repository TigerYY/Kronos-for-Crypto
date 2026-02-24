from fastapi import APIRouter, Query
from backend.services import data_svc

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/ohlcv")
def get_ohlcv(
    symbol: str = Query(..., description="e.g. BTC/USDT, ES=F"),
    timeframe: str = Query(..., description="e.g. 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(512, ge=1, le=1000),
):
    """Return OHLCV bars for symbol/timeframe (for charts)."""
    return data_svc.fetch_ohlcv(symbol, timeframe, limit=limit)
