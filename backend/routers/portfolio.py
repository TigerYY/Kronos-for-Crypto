from fastapi import APIRouter
from backend.services import portfolio_svc

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("")
def get_portfolio():
    """Return current portfolio state (balance, positions, last_update)."""
    return portfolio_svc.get_portfolio_state()


@router.get("/trades")
def get_trades(limit: int = 100):
    """Return recent trade log entries."""
    return portfolio_svc.get_trade_log(limit=limit)
