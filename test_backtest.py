import sys
import traceback
from backend.services.backtest_svc import run_backtest

try:
    res = run_backtest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_date="2024-01-01",
        end_date="2024-06-01",
        initial_capital=10000.0,
        lookback=400,
        pred_len=12,
        step_size=6,
        threshold=0.005,
        device="auto"
    )
    print("Success")
except Exception as e:
    traceback.print_exc()
