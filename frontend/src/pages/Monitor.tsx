import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getOhlcv,
  getTrades,
  postPredict,
  type PredictResponse,
} from "../api/client";
import KlineChart from "../components/KlineChart";
import SignalCard from "../components/SignalCard";
import MetricCard from "../components/MetricCard";
import "./Monitor.css";

const SYMBOLS = ["BTC/USDT", "ETH/USDT", "ES=F"];
const TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"];
const INITIAL_BALANCE = 10000;

export default function Monitor() {
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [predictResult, setPredictResult] = useState<PredictResponse | null>(null);

  const queryClient = useQueryClient();

  const { data: ohlcv = [], isLoading: ohlcvLoading } = useQuery({
    queryKey: ["ohlcv", symbol, timeframe],
    queryFn: () => getOhlcv(symbol, timeframe, 512),
  });

  const { data: trades = [], isLoading: tradesLoading } = useQuery({
    queryKey: ["trades"],
    queryFn: () => getTrades(50),
  });

  const predictMutation = useMutation({
    mutationFn: () => postPredict(symbol, ["5m", "15m", "1h", "4h", "1d"]),
    onSuccess: (data) => {
      setPredictResult(data);
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      queryClient.invalidateQueries({ queryKey: ["trades"] });
    },
  });

  const currentPrice = predictResult?.current_price;
  const predictedPrice = predictResult?.predictions?.[timeframe];
  const signal = predictResult?.signal;
  const predSeries = predictResult?.pred_series?.[timeframe];
  const portfolio = queryClient.getQueryData(["portfolio"]) as
    | { balance: number; positions: Record<string, number> }
    | undefined;
  const totalValue =
    portfolio && currentPrice != null
      ? portfolio.balance +
        Object.entries(portfolio.positions || {}).reduce(
          (sum, [sym, amt]) => sum + (sym === symbol ? amt * currentPrice : 0),
          0
        )
      : portfolio?.balance ?? null;

  return (
    <div className="monitor">
      <header className="main-header">
        <h1>实时监控</h1>
        <p>Kronos 多时间框架预测 · 实时行情 · 信号生成</p>
      </header>

      <div className="controls">
        <label>
          交易对
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          >
            {SYMBOLS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          时间周期
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
          >
            {TIMEFRAMES.map((tf) => (
              <option key={tf} value={tf}>
                {tf}
              </option>
            ))}
          </select>
        </label>
        <button
          className="btn-primary"
          onClick={() => predictMutation.mutate()}
          disabled={predictMutation.isPending}
        >
          {predictMutation.isPending ? "预测中…" : "立即预测"}
        </button>
      </div>

      {predictMutation.isError && (
        <div className="error-banner">
          {(predictMutation.error as Error).message}
        </div>
      )}

      <div className="metrics-row">
        <MetricCard
          label="当前价格"
          value={
            currentPrice != null
              ? `$${currentPrice.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
              : "—"
          }
        />
        <MetricCard
          label="预测价格"
          value={
            predictedPrice != null
              ? `$${predictedPrice.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
              : "—"
          }
          delta={
            currentPrice != null && predictedPrice != null
              ? `${((predictedPrice - currentPrice) / currentPrice * 100).toFixed(2)}%`
              : undefined
          }
          positive={currentPrice != null && predictedPrice != null ? predictedPrice >= currentPrice : undefined}
        />
        <div className="metric-slot">
          {signal ? (
            <SignalCard action={signal.action} />
          ) : (
            <div className="metric-card">
              <div className="metric-label">信号</div>
              <div className="metric-value">—</div>
            </div>
          )}
        </div>
        <MetricCard
          label="组合总值"
          value={
            totalValue != null
              ? `$${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
              : portfolio?.balance != null
                ? `$${portfolio.balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
                : "—"
          }
          delta={
            totalValue != null
              ? `${(((totalValue - INITIAL_BALANCE) / INITIAL_BALANCE) * 100).toFixed(2)}%`
              : undefined
          }
          positive={
            totalValue != null ? totalValue >= INITIAL_BALANCE : undefined
          }
        />
      </div>

      <div className="chart-section">
        {ohlcvLoading ? (
          <p>加载 K 线…</p>
        ) : (
          <KlineChart
            data={ohlcv}
            predSeries={predSeries}
            symbol={symbol}
            timeframe={timeframe}
          />
        )}
      </div>

      {signal && (
        <>
          <h3 className="section-title">多时间框架信号</h3>
          <div className="tf-cards">
            {["15m", "1h", "4h", "1d"].map((tf) => {
              const pred = predictResult?.predictions?.[tf];
              if (pred == null) return null;
              const chg =
                currentPrice != null
                  ? ((pred - currentPrice) / currentPrice) * 100
                  : 0;
              return (
                <div key={tf} className="tf-card">
                  <div className="metric-label">{tf}</div>
                  <div className="metric-value">
                    ${pred.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </div>
                  <div
                    className={chg >= 0 ? "metric-delta positive" : "metric-delta negative"}
                  >
                    {chg >= 0 ? "+" : ""}{chg.toFixed(2)}%
                  </div>
                </div>
              );
            })}
          </div>
          <p className="signal-confidence">
            信号置信度: {(signal.confidence * 100).toFixed(1)}%
          </p>
          <progress value={signal.confidence} max={1} className="confidence-bar" />
          <p className="signal-reasons">{signal.reasons.join(" · ")}</p>
        </>
      )}

      <h3 className="section-title">近期交易记录</h3>
      {tradesLoading ? (
        <p>加载中…</p>
      ) : trades.length === 0 ? (
        <p className="muted">暂无交易记录</p>
      ) : (
        <div className="trades-table-wrap">
          <table className="trades-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>标的</th>
                <th>操作</th>
                <th>价格</th>
                <th>数量</th>
                <th>组合净值</th>
                <th>原因</th>
              </tr>
            </thead>
            <tbody>
              {[...trades].reverse().slice(0, 15).map((t, i) => (
                <tr key={i}>
                  <td>{t.timestamp != null ? String(t.timestamp).slice(0, 19) : "—"}</td>
                  <td>{t.symbol ?? "—"}</td>
                  <td>{t.action ?? "—"}</td>
                  <td>{t.price != null ? t.price.toFixed(2) : "—"}</td>
                  <td>{t.amount != null ? t.amount.toFixed(6) : "—"}</td>
                  <td>{t.portfolio_value != null ? t.portfolio_value.toFixed(2) : "—"}</td>
                  <td>{t.reason ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
