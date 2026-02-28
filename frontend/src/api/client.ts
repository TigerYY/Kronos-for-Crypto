const API_BASE = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";
const API_PREFIX = `${API_BASE}/api`;

export type PortfolioState = {
  balance: number;
  positions: Record<string, number>;
  last_update: string;
};

export type TradeRecord = {
  timestamp?: string;
  symbol?: string;
  action?: string;
  price?: number;
  amount?: number;
  balance?: number;
  portfolio_value?: number;
  reason?: string;
};

export type OhlcvBar = {
  timestamps: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount?: number;
};

export type PredictResponse = {
  current_price: number;
  predictions: Record<string, number>;
  pred_series: Record<string, number[]>;
  signal: {
    action: string;
    confidence: number;
    change_pct: number;
    reasons: string[];
  };
  fundamentals?: {
    fgi: {
      value: string;
      classification: string;
    };
    funding_rate: number;
  };
  lookback: number;
  pred_len: number;
};

export async function getPortfolio(): Promise<PortfolioState> {
  const r = await fetch(`${API_PREFIX}/portfolio`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getTrades(limit = 100): Promise<TradeRecord[]> {
  const r = await fetch(`${API_PREFIX}/portfolio/trades?limit=${limit}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getOhlcv(
  symbol: string,
  timeframe: string,
  limit = 512
): Promise<OhlcvBar[]> {
  const params = new URLSearchParams({ symbol, timeframe, limit: String(limit) });
  const r = await fetch(`${API_PREFIX}/data/ohlcv?${params}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function postPredict(
  symbol: string,
  timeframes?: string[]
): Promise<PredictResponse> {
  const r = await fetch(`${API_PREFIX}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, timeframes }),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error((e as { detail?: string }).detail || "Predict failed");
  }
  return r.json();
}

export type StrategyConfig = {
  threshold?: number;
  strong_threshold?: number;
  weights?: { "5m"?: number; "15m"?: number; "1h"?: number };
  buy_pct?: number;
  max_exposure?: number;
  stop_loss?: number;
  take_profit?: number;
  min_confidence?: number;
  lora_adapter?: string;
};

export async function getConfig(): Promise<StrategyConfig & Record<string, unknown>> {
  const r = await fetch(`${API_PREFIX}/config`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function putConfig(data: StrategyConfig): Promise<StrategyConfig & Record<string, unknown>> {
  const r = await fetch(`${API_PREFIX}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type BacktestRequest = {
  symbol?: string;
  timeframe?: string;
  start_date?: string;
  end_date?: string;
  initial_capital?: number;
  lookback?: number;
  pred_len?: number;
  step_size?: number;
  threshold?: number;
  device?: string;
};

export type BacktestResponse = {
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  equity_curve: { date: string; value: number }[];
  benchmark_curve?: { date: string; value: number }[];
  trades: Record<string, unknown>[];
  metrics: Record<string, number>;
};

export async function postBacktest(body: BacktestRequest): Promise<BacktestResponse> {
  const r = await fetch(`${API_PREFIX}/backtest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error((e as { detail?: string }).detail || "Backtest failed");
  }
  return r.json();
}
