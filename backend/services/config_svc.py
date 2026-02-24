"""
Strategy/config service: read and write strategy_config.json (same format as Streamlit).
"""
import os
import json
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(ROOT, "strategy_config.json")

DEFAULT_CONFIG = {
    "threshold": 0.005,
    "strong_threshold": 0.015,
    "weights": {"5m": 0.2, "15m": 0.3, "1h": 0.5},
    "buy_pct": 0.15,
    "max_exposure": 0.8,
    "stop_loss": 0.03,
    "take_profit": 0.08,
    "min_confidence": 0.45,
}


def get_config() -> dict[str, Any]:
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
        out = DEFAULT_CONFIG.copy()
        out.update(data)
        return out
    except Exception:
        return DEFAULT_CONFIG.copy()


def put_config(data: dict[str, Any]) -> dict[str, Any]:
    current = get_config()
    allowed = {
        "threshold", "strong_threshold", "weights",
        "buy_pct", "max_exposure", "stop_loss", "take_profit", "min_confidence",
    }
    for k, v in data.items():
        if k in allowed:
            current[k] = v
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return current
