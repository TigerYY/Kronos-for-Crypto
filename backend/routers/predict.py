from fastapi import APIRouter
from pydantic import BaseModel
from backend.services import predict_svc

router = APIRouter(prefix="/predict", tags=["predict"])


class PredictRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframes: list[str] | None = None


@router.post("")
def post_predict(body: PredictRequest):
    """
    Run multi-timeframe Kronos prediction and fused signal.
    Lazy-loads model on first call.
    """
    result = predict_svc.run_predict(body.symbol, body.timeframes)
    if "error" in result:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=result)
    return result
