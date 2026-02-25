from fastapi import APIRouter
from pydantic import BaseModel
from backend.services import config_svc

router = APIRouter(prefix="/config", tags=["config"])


class ConfigUpdate(BaseModel):
    threshold: float | None = None
    strong_threshold: float | None = None
    weights: dict[str, float] | None = None
    buy_pct: float | None = None
    max_exposure: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    min_confidence: float | None = None
    lora_adapter: str | None = None


@router.get("")
def get_config():
    """Return current strategy/risk config."""
    return config_svc.get_config()


@router.put("")
def put_config(body: ConfigUpdate):
    """Update config (partial update)."""
    data = body.model_dump(exclude_none=True)
    return config_svc.put_config(data)
