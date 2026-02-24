from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services import backtest_svc

router = APIRouter(prefix="/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    start_date: str = "2024-01-01"
    end_date: str = "2024-06-01"
    initial_capital: float = 10000.0
    lookback: int = 400
    pred_len: int = 12
    step_size: int = 6
    threshold: float = 0.005
    device: str = "auto"


@router.post("")
def post_backtest(body: BacktestRequest):
    """
    Run Kronos strategy backtest over historical data.
    May take several minutes (model load + many prediction steps).
    """
    try:
        return backtest_svc.run_backtest(
            symbol=body.symbol,
            timeframe=body.timeframe,
            start_date=body.start_date,
            end_date=body.end_date,
            initial_capital=body.initial_capital,
            lookback=body.lookback,
            pred_len=body.pred_len,
            step_size=body.step_size,
            threshold=body.threshold,
            device=body.device,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
