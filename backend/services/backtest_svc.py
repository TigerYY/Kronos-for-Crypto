"""
Backtest service: run Backtester and return JSON-serializable result.
"""
import os
import sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backtest.backtester import Backtester


def run_backtest(
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    start_date: str = "2024-01-01",
    end_date: str = "2024-06-01",
    initial_capital: float = 10000.0,
    lookback: int = 400,
    pred_len: int = 12,
    step_size: int = 6,
    threshold: float = 0.005,
    device: str = "auto",
) -> dict:
    """
    Run backtest and return dict with equity_curve (list of {date, value}), trades, metrics.
    """
    bt = Backtester(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        lookback=lookback,
        pred_len=pred_len,
        step_size=step_size,
        threshold=threshold,
        device=device,
    )
    result = bt.run()

    # Serialize equity curve: index (timestamp) -> str, values -> float
    equity = result.equity_curve
    benchmark = result.benchmark_curve

    equity_curve = []
    benchmark_curve = []
    
    for i in range(len(equity)):
        date_str = str(equity.index[i])
        equity_curve.append({"date": date_str, "value": float(equity.iloc[i])})
        benchmark_curve.append({"date": date_str, "value": float(benchmark.iloc[i])})

    # Trades: ensure timestamps are strings
    trades = []
    for t in result.trades:
        row = dict(t)
        if "timestamp" in row and hasattr(row["timestamp"], "isoformat"):
            row["timestamp"] = str(row["timestamp"])
        trades.append(row)

    return {
        "symbol": result.symbol,
        "timeframe": result.timeframe,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "initial_capital": result.initial_capital,
        "equity_curve": equity_curve,
        "benchmark_curve": benchmark_curve,
        "trades": trades,
        "metrics": result.metrics,
    }
