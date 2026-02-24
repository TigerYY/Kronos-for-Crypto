import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Plot from "react-plotly.js";
import { postBacktest, type BacktestResponse } from "../api/client";
import "./Backtest.css";

export default function Backtest() {
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [form, setForm] = useState({
    symbol: "BTC/USDT",
    timeframe: "1h",
    start_date: "2024-01-01",
    end_date: "2024-06-01",
    initial_capital: 10000,
    lookback: 400,
    pred_len: 12,
    step_size: 6,
    threshold: 0.5,
    device: "auto",
  });

  const runMutation = useMutation({
    mutationFn: () =>
      postBacktest({
        ...form,
        threshold: form.threshold / 100,
      }),
    onSuccess: (data) => setResult(data),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runMutation.mutate();
  };

  const metrics = result?.metrics;
  const equity = result?.equity_curve ?? [];

  return (
    <div className="backtest-page">
      <header className="main-header">
        <h1>回测分析</h1>
        <p>基于 Kronos 预测的历史策略回测 · 净值曲线 · 绩效评估</p>
      </header>

      <form onSubmit={handleSubmit} className="backtest-form">
        <div className="form-row">
          <label>
            交易对
            <select
              value={form.symbol}
              onChange={(e) => setForm((f) => ({ ...f, symbol: e.target.value }))}
            >
              <option value="BTC/USDT">BTC/USDT</option>
              <option value="ETH/USDT">ETH/USDT</option>
              <option value="ES=F">ES=F</option>
            </select>
          </label>
          <label>
            时间周期
            <select
              value={form.timeframe}
              onChange={(e) => setForm((f) => ({ ...f, timeframe: e.target.value }))}
            >
              <option value="15m">15m</option>
              <option value="1h">1h</option>
              <option value="4h">4h</option>
              <option value="1d">1d</option>
            </select>
          </label>
          <label>
            开始日期
            <input
              type="date"
              value={form.start_date}
              onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
            />
          </label>
          <label>
            结束日期
            <input
              type="date"
              value={form.end_date}
              onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            初始资金 (USDT)
            <input
              type="number"
              min={100}
              step={100}
              value={form.initial_capital}
              onChange={(e) =>
                setForm((f) => ({ ...f, initial_capital: Number(e.target.value) }))
              }
            />
          </label>
          <label>
            lookback
            <input
              type="number"
              min={100}
              max={500}
              value={form.lookback}
              onChange={(e) => setForm((f) => ({ ...f, lookback: Number(e.target.value) }))}
            />
          </label>
          <label>
            pred_len
            <input
              type="number"
              min={6}
              max={48}
              value={form.pred_len}
              onChange={(e) => setForm((f) => ({ ...f, pred_len: Number(e.target.value) }))}
            />
          </label>
          <label>
            step_size
            <input
              type="number"
              min={1}
              max={24}
              value={form.step_size}
              onChange={(e) => setForm((f) => ({ ...f, step_size: Number(e.target.value) }))}
            />
          </label>
          <label>
            信号阈值 (%)
            <input
              type="number"
              min={0.1}
              max={3}
              step={0.1}
              value={form.threshold}
              onChange={(e) => setForm((f) => ({ ...f, threshold: Number(e.target.value) }))}
            />
          </label>
        </div>
        <button type="submit" className="btn-primary" disabled={runMutation.isPending}>
          {runMutation.isPending ? "回测中…（可能需数分钟）" : "开始回测"}
        </button>
        {runMutation.isError && (
          <div className="error-banner">{(runMutation.error as Error).message}</div>
        )}
      </form>

      {result && (
        <>
          <h3 className="section-title">绩效指标</h3>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">总收益率</div>
              <div className={`metric-value ${(metrics?.total_return ?? 0) >= 0 ? "positive" : "negative"}`}>
                {(metrics?.total_return ?? 0).toFixed(2)}%
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">年化收益率</div>
              <div className={`metric-value ${(metrics?.annual_return ?? 0) >= 0 ? "positive" : "negative"}`}>
                {(metrics?.annual_return ?? 0).toFixed(2)}%
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">夏普比率</div>
              <div className="metric-value">{metrics?.sharpe_ratio?.toFixed(3) ?? "—"}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">最大回撤</div>
              <div className="metric-value negative">{metrics?.max_drawdown?.toFixed(2) ?? "—"}%</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">胜率</div>
              <div className="metric-value">{metrics?.win_rate?.toFixed(1) ?? "—"}%</div>
            </div>
          </div>

          <h3 className="section-title">净值曲线</h3>
          {equity.length > 0 && (
            <Plot
              data={[
                {
                  x: equity.map((p) => p.date),
                  y: equity.map((p) => p.value),
                  type: "scatter",
                  mode: "lines",
                  name: "策略净值",
                  line: { color: "#f39c12", width: 2 },
                  fill: "tozeroy",
                  fillcolor: "rgba(243,156,18,0.1)",
                },
              ]}
              layout={{
                template: "plotly_dark",
                paper_bgcolor: "#0d1117",
                plot_bgcolor: "#0d1117",
                height: 400,
                yaxis: { title: "净值 (USDT)", gridcolor: "#1e2a3a" },
                xaxis: { gridcolor: "#1e2a3a" },
                margin: { t: 24, b: 40, l: 60, r: 24 },
                showlegend: true,
              }}
              config={{ responsive: true }}
              style={{ width: "100%" }}
            />
          )}

          {result.trades.length > 0 && (
            <>
              <h3 className="section-title">交易明细</h3>
              <div className="trades-table-wrap">
                <table className="trades-table">
                  <thead>
                    <tr>
                      <th>时间</th>
                      <th>操作</th>
                      <th>价格</th>
                      <th>数量</th>
                      <th>盈亏%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.slice(-30).reverse().map((t, i) => (
                      <tr key={i}>
                        <td>{String((t as { timestamp?: string }).timestamp ?? "").slice(0, 19)}</td>
                        <td>{(t as { action?: string }).action ?? "—"}</td>
                        <td>{(t as { price?: number }).price?.toFixed(2) ?? "—"}</td>
                        <td>{(t as { amount?: number }).amount?.toFixed(6) ?? "—"}</td>
                        <td>
                          {(t as { pnl_pct?: number }).pnl_pct != null
                            ? `${((t as { pnl_pct?: number }).pnl_pct! * 100).toFixed(2)}%`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
