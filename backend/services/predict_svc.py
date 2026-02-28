"""
Prediction service: lazy-loads CryptoSimulator, runs multi-timeframe predict + signal.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Import after path fix
from crypto_simulator import CryptoSimulator, LOOKBACK, PRED_LEN
from backend.services.rag_svc import RAGAnalyzer
from trading.news_scanner import NewsScanner
import time

_rag_cache = {"timestamp": 0, "decision": None}
_simulator: CryptoSimulator | None = None
DEFAULT_TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"]


def get_simulator() -> CryptoSimulator:
    global _simulator
    if _simulator is None:
        _simulator = CryptoSimulator()
    return _simulator


def run_predict(
    symbol: str,
    timeframes: list[str] | None = None,
) -> dict:
    """
    Fetch multi-timeframe data, run Kronos predict per timeframe, fuse signal.
    Returns: current_price, predictions dict, signal (action, confidence, change_pct, reasons),
             pred_series dict (timeframe -> list of pred close for chart).
    """
    tf_list = timeframes or DEFAULT_TIMEFRAMES
    sim = get_simulator()
    tf_data = sim.data_fetcher.fetch_multi_timeframe(symbol, tf_list, LOOKBACK)
    main_df = tf_data.get(tf_list[0]) if tf_list else None
    if main_df is None or len(main_df) < LOOKBACK:
        return {
            "error": "data_unavailable",
            "message": f"Could not load enough data for {symbol} (need {LOOKBACK} bars)",
        }

    current_price = float(main_df["close"].iloc[-1])
    predictions: dict[str, float | None] = {}
    pred_series: dict[str, list[float]] = {}

    rl_data = None
    for tf, df in tf_data.items():
        if df is None or len(df) < LOOKBACK:
            predictions[tf] = None
            continue
        try:
            pred_df, rl_res = sim.predict(df)
            predictions[tf] = float(pred_df["close"].iloc[-1])
            pred_series[tf] = pred_df["close"].astype(float).tolist()
            if rl_res is not None and rl_data is None:
                # Capture the RL result from the shortest timeframe available for prompt action
                rl_data = rl_res
        except Exception as e:
            import traceback
            print(f"[PredictSvc] Error in sim.predict for {tf}: {e}")
            traceback.print_exc()
            predictions[tf] = None

    signal = sim.strategy.generate_signal(predictions, current_price)

    # Fetch fundamental factors (Phase 2)
    try:
        fgi = sim.data_fetcher.fetch_fgi()
        funding_rate = sim.data_fetcher.fetch_funding_rate(symbol)
    except Exception as e:
        print(f"[PredictSvc] Error fetching fundamentals: {e}")
        fgi = {'value': '50', 'classification': 'Neutral'}
        funding_rate = 0.0

    # Macro RAG Intervention (Phase 3)
    global _rag_cache
    now = time.time()
    if _rag_cache["decision"] is None or (now - _rag_cache["timestamp"] > 300):
        try:
            scanner = NewsScanner()
            news = scanner.fetch_latest_news(hours_lookback=4)
            rag_analyzer = RAGAnalyzer()
            new_decision = rag_analyzer.analyze_news_sentiment(news)
            
            # Retain old events if the new fetch failed to produce any (e.g., LLM error)
            if "LLM Error" in new_decision.get("reason", "") or not new_decision.get("events"):
                old_events = _rag_cache["decision"].get("events", []) if _rag_cache["decision"] else []
                if old_events:
                    new_decision["events"] = old_events
                    
            _rag_cache["decision"] = new_decision
            _rag_cache["timestamp"] = now
        except Exception as e:
            print(f"[PredictSvc] RAG fetching error: {e}")
            old_events = _rag_cache["decision"].get("events", []) if _rag_cache["decision"] else []
            _rag_cache["decision"] = {"sentiment": "NEUTRAL", "override_signal": "NONE", "reason": "RAG Offline", "events": old_events}
            _rag_cache["timestamp"] = now
    
    rag_decision = _rag_cache["decision"]

    # System Override Logic
    intercepted_action = signal.action
    reasons = signal.reasons.copy()
    if rag_decision.get("override_signal") != "NONE":
        intercepted_action = rag_decision["override_signal"]
        reasons.insert(0, f"[MACRO RAG OVERRIDE] {rag_decision.get('reason')}")

    return {
        "current_price": current_price,
        "predictions": {k: v for k, v in predictions.items() if v is not None},
        "pred_series": pred_series,
        "signal": {
            "action": intercepted_action,
            "confidence": signal.confidence,
            "change_pct": signal.change_pct,
            "reasons": reasons,
        },
        "rl_alignment": rl_data,
        "fundamentals": {
            "fgi": fgi,
            "funding_rate": funding_rate,
        },
        "rag": rag_decision,
        "lookback": LOOKBACK,
        "pred_len": PRED_LEN,
    }
