"""
Portfolio and trade log service.
Reads portfolio_state.json and simulation_log.csv (same format as Streamlit/Simulator).
"""
import os
import json
import pandas as pd
from typing import Any

# Assume backend is run from project root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORTFOLIO_STATE_FILE = os.path.join(ROOT, "portfolio_state.json")
SIMULATION_LOG_FILE = os.path.join(ROOT, "simulation_log.csv")


def get_portfolio_state() -> dict[str, Any]:
    default = {"balance": 10000.0, "positions": {}, "last_update": "—"}
    if not os.path.exists(PORTFOLIO_STATE_FILE):
        return default
    try:
        with open(PORTFOLIO_STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def get_trade_log(limit: int = 100) -> list[dict[str, Any]]:
    if not os.path.exists(SIMULATION_LOG_FILE):
        return []
    try:
        df = pd.read_csv(SIMULATION_LOG_FILE)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.tail(limit)
        return df.dropna(axis=1, how="all").to_dict(orient="records")
    except Exception:
        return []
