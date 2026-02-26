import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Plot from "react-plotly.js";
import { postBacktest, type BacktestResponse } from "../api/client";
import { motion, type Variants } from "framer-motion";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants: Variants = {
  hidden: { y: 20, opacity: 0 },
  visible: { y: 0, opacity: 1, transition: { duration: 0.5, type: "spring" } },
};

export default function Backtest() {
  const [result, setResult] = useState<BacktestResponse | null>(null);

  const today = new Date();
  const sixMonthsAgo = new Date();
  sixMonthsAgo.setMonth(today.getMonth() - 6);
  const formatDate = (d: Date) => d.toISOString().split('T')[0];

  const [form, setForm] = useState({
    symbol: "BTC/USDT",
    timeframe: "1h",
    start_date: formatDate(sixMonthsAgo),
    end_date: formatDate(today),
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
  const benchmark = result?.benchmark_curve ?? [];

  // 简单的导出 CSV 功能
  const exportToCSV = () => {
    if (!result || result.trades.length === 0) return;
    const headers = ["Timestamp", "Action", "Price", "Amount", "Balance", "Unrealized PnL %", "Reason"];
    const rows = result.trades.map((t: any) => [
      t.timestamp ?? "",
      t.action ?? "",
      t.price ?? "",
      t.amount ?? "",
      t.balance ?? "",
      t.pnl_pct ? (t.pnl_pct * 100).toFixed(2) + "%" : "",
      t.reason ? `"${t.reason.replace(/"/g, '""')}"` : ""
    ]);
    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `kronos_${result.symbol.replace(/\//g, '_')}_backtest.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6 pb-20"
    >
      <motion.div variants={itemVariants} className="mb-6">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">回测分析</h1>
        <p className="text-slate-400 mt-1">基于 Kronos 预测的历史策略回测 · 净值曲线 · 绩效评估</p>
      </motion.div>

      <motion.form variants={itemVariants} onSubmit={handleSubmit} className="glass-panel p-6 rounded-2xl space-y-6 border-t border-l border-white/5">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <label className="flex flex-col space-y-1.5">
            <span className="text-sm text-slate-400 font-medium">交易对</span>
            <select
              className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
              value={form.symbol}
              onChange={(e) => setForm((f) => ({ ...f, symbol: e.target.value }))}
            >
              <option value="BTC/USDT">BTC/USDT</option>
              <option value="ETH/USDT">ETH/USDT</option>
              <option value="ES=F">SPX500</option>
              <option value="XAU/USDT">XAU/USDT（黄金永续）</option>
            </select>
          </label>
          <label className="flex flex-col space-y-1.5">
            <span className="text-sm text-slate-400 font-medium">时间周期</span>
            <select
              className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
              value={form.timeframe}
              onChange={(e) => setForm((f) => ({ ...f, timeframe: e.target.value }))}
            >
              <option value="15m">15m</option>
              <option value="1h">1h</option>
              <option value="4h">4h</option>
              <option value="1d">1d</option>
            </select>
          </label>
          <label className="flex flex-col space-y-1.5">
            <span className="text-sm text-slate-400 font-medium">开始日期</span>
            <input
              type="date"
              className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
              value={form.start_date}
              onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
            />
          </label>
          <label className="flex flex-col space-y-1.5">
            <span className="text-sm text-slate-400 font-medium">结束日期</span>
            <input
              type="date"
              className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
              value={form.end_date}
              onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
            />
          </label>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 pt-4 border-t border-white/5">
          <label className="flex flex-col space-y-1.5">
            <span className="text-sm text-slate-400 font-medium">初始资金 (USDT)</span>
            <input
              type="number"
              className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
              min={100}
              step={100}
              value={form.initial_capital}
              onChange={(e) => setForm((f) => ({ ...f, initial_capital: Number(e.target.value) }))}
            />
          </label>
          <label className="flex flex-col space-y-1.5">
            <span className="text-sm text-slate-400 font-medium">Lookback</span>
            <input
              type="number"
              className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
              min={100}
              max={500}
              value={form.lookback}
              onChange={(e) => setForm((f) => ({ ...f, lookback: Number(e.target.value) }))}
            />
          </label>
          <label className="flex flex-col space-y-1.5">
            <span className="text-sm text-slate-400 font-medium">Pred_len</span>
            <input
              type="number"
              className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
              min={6}
              max={48}
              value={form.pred_len}
              onChange={(e) => setForm((f) => ({ ...f, pred_len: Number(e.target.value) }))}
            />
          </label>
          <label className="flex flex-col space-y-1.5">
            <span className="text-sm text-slate-400 font-medium">Step_size</span>
            <input
              type="number"
              className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
              min={1}
              max={24}
              value={form.step_size}
              onChange={(e) => setForm((f) => ({ ...f, step_size: Number(e.target.value) }))}
            />
          </label>
          <label className="flex flex-col space-y-1.5">
            <span className="text-sm text-slate-400 font-medium">信号阈值 (%)</span>
            <input
              type="number"
              className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
              min={0.1}
              max={3}
              step={0.1}
              value={form.threshold}
              onChange={(e) => setForm((f) => ({ ...f, threshold: Number(e.target.value) }))}
            />
          </label>
        </div>

        <div className="flex items-center justify-between pt-4">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={runMutation.isPending}
            className="w-full md:w-auto px-8 py-3 rounded-xl font-medium tracking-wide bg-gradient-to-r from-neon-purple to-neon-cyan text-white shadow-lg shadow-neon-purple/20 disabled:opacity-50 transition-all"
          >
            {runMutation.isPending ? "全量历史回测中..." : "启动参数回测"}
          </motion.button>
        </div>

        {runMutation.isError && (
          <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-xl mt-4">
            ⚠️ 回测失败: {(runMutation.error as Error).message}
          </div>
        )}
      </motion.form>

      {result && (
        <motion.div variants={containerVariants} initial="hidden" animate="visible" className="space-y-6">
          <motion.h3 variants={itemVariants} className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
            <span className="w-1.5 h-6 bg-emerald-500 rounded-full inline-block" />
            绩效指标
          </motion.h3>
          <motion.div variants={itemVariants} className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-8 gap-4">
            <div className="glass-panel p-4 rounded-xl flex flex-col justify-center border-t border-white/5">
              <span className="text-xs text-slate-400 font-medium mb-1 line-clamp-1" title="总收益率">总收益率</span>
              <span className={`text-lg font-bold ${(metrics?.total_return ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                {(metrics?.total_return ?? 0).toFixed(2)}%
              </span>
            </div>
            <div className="glass-panel p-4 rounded-xl flex flex-col justify-center border-t border-white/5">
              <span className="text-xs text-slate-400 font-medium mb-1 line-clamp-1" title="年化收益率">年化收益率</span>
              <span className={`text-lg font-bold ${(metrics?.annual_return ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                {(metrics?.annual_return ?? 0).toFixed(2)}%
              </span>
            </div>
            <div className="glass-panel p-4 rounded-xl flex flex-col justify-center border-t border-white/5">
              <span className="text-xs text-slate-400 font-medium mb-1 line-clamp-1" title="夏普比率">夏普比率</span>
              <span className="text-lg font-bold text-white">{metrics?.sharpe_ratio?.toFixed(2) ?? "—"}</span>
            </div>
            <div className="glass-panel p-4 rounded-xl flex flex-col justify-center border-t border-white/5">
              <span className="text-xs text-slate-400 font-medium mb-1 line-clamp-1" title="最大回撤">最大回撤</span>
              <span className="text-lg font-bold text-rose-400">{metrics?.max_drawdown?.toFixed(2) ?? "—"}%</span>
            </div>
            <div className="glass-panel p-4 rounded-xl flex flex-col justify-center border-t border-white/5">
              <span className="text-xs text-slate-400 font-medium mb-1 line-clamp-1" title="回撤天数">回撤天数</span>
              <span className="text-lg font-bold text-slate-300">{metrics?.drawdown_days ?? "—"} 天</span>
            </div>
            <div className="glass-panel p-4 rounded-xl flex flex-col justify-center border-t border-white/5">
              <span className="text-xs text-slate-400 font-medium mb-1 line-clamp-1" title="盈亏比">盈亏比 (PnL)</span>
              <span className="text-lg font-bold text-amber-400">{metrics?.profit_factor?.toFixed(2) ?? "—"}x</span>
            </div>
            <div className="glass-panel p-4 rounded-xl flex flex-col justify-center border-t border-white/5">
              <span className="text-xs text-slate-400 font-medium mb-1 line-clamp-1" title="胜率">胜率</span>
              <span className="text-lg font-bold text-neon-cyan">{metrics?.win_rate?.toFixed(1) ?? "—"}%</span>
            </div>
            <div className="glass-panel p-4 rounded-xl flex flex-col justify-center border-t border-white/5">
              <span className="text-xs text-slate-400 font-medium mb-1 line-clamp-1" title="总交易数">总交易数</span>
              <span className="text-lg font-bold text-slate-300">{metrics?.total_trades ?? 0}</span>
            </div>
          </motion.div>

          {equity.length > 0 && (
            <motion.div variants={itemVariants} className="glass-panel p-4 md:p-6 rounded-2xl border-t border-white/5">
              <h3 className="text-lg font-bold text-white tracking-wide mb-4">净值曲线</h3>
              <div className="-mx-4 md:mx-0">
                <Plot
                  data={[
                    {
                      x: equity.map((p) => p.date),
                      y: equity.map((p) => p.value),
                      type: "scatter",
                      mode: "lines",
                      name: "策略净值 (AI)",
                      line: { color: "#00f0ff", width: 2.5 },
                      fill: "tozeroy",
                      fillcolor: "rgba(0,240,255,0.1)",
                    },
                    ...(benchmark.length > 0 ? [{
                      x: benchmark.map((p) => p.date),
                      y: benchmark.map((p) => p.value),
                      type: "scatter" as const,
                      mode: "lines" as const,
                      name: "基准净值 (Buy & Hold)",
                      line: { color: "#f59e0b", width: 1.5, dash: "dash" as const },
                    }] : []),
                  ]}
                  layout={{
                    template: "plotly_dark",
                    paper_bgcolor: "transparent",
                    plot_bgcolor: "transparent",
                    height: 400,
                    yaxis: { title: "净值 (USDT)", gridcolor: "#1e2a3a", zerolinecolor: "#1e2a3a" },
                    xaxis: { gridcolor: "#1e2a3a", zerolinecolor: "#1e2a3a" },
                    margin: { t: 24, b: 40, l: 60, r: 24 },
                    showlegend: true,
                    font: { family: "Inter, sans-serif", color: "#94a3b8" }
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: "100%" }}
                />
              </div>
            </motion.div>
          )}

          {result.trades.length > 0 && (
            <motion.div variants={itemVariants} className="space-y-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
                  <span className="w-1.5 h-6 bg-rose-500 rounded-full inline-block" />
                  交易明细
                </h3>
                <button
                  onClick={exportToCSV}
                  className="px-3 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white rounded-lg border border-white/10 transition-colors flex items-center gap-1.5"
                >
                  <span>⬇️</span> 导出 CSV
                </button>
              </div>
              <div className="glass-panel rounded-2xl overflow-hidden border-t border-white/10">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-slate-300">
                    <thead className="text-xs uppercase bg-slate-900/50 text-slate-400 border-b border-white/5">
                      <tr>
                        <th className="px-6 py-4 font-medium">时间</th>
                        <th className="px-6 py-4 font-medium">操作</th>
                        <th className="px-6 py-4 font-medium text-right">价格</th>
                        <th className="px-6 py-4 font-medium text-right">数量</th>
                        <th className="px-6 py-4 font-medium text-right">盈亏%</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {result.trades.slice(-30).reverse().map((t, i) => {
                        const actionStr = (t as { action?: string }).action ?? "—";
                        const isBuy = actionStr === "BUY";
                        const isSell = actionStr === "SELL";
                        const pnlPct = (t as { pnl_pct?: number }).pnl_pct;

                        return (
                          <motion.tr
                            key={i}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: i * 0.05 }}
                            className="hover:bg-white/5 transition-colors"
                          >
                            <td className="px-6 py-4 font-mono text-xs whitespace-nowrap">
                              {String((t as { timestamp?: string }).timestamp ?? "").slice(0, 19).replace('T', ' ')}
                            </td>
                            <td className="px-6 py-4">
                              <span className={`px-2 py-1 rounded text-xs font-bold ${isBuy ? 'bg-emerald-500/20 text-emerald-400' :
                                isSell ? 'bg-rose-500/20 text-rose-400' :
                                  'bg-slate-700 text-slate-300'
                                }`}>
                                {actionStr}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-right font-mono">${(t as { price?: number }).price?.toFixed(2) ?? "—"}</td>
                            <td className="px-6 py-4 text-right font-mono text-slate-400">{(t as { amount?: number }).amount?.toFixed(6) ?? "—"}</td>
                            <td className="px-6 py-4 text-right">
                              {pnlPct != null ? (
                                <span className={pnlPct >= 0 ? "text-emerald-400" : "text-rose-400"}>
                                  {pnlPct >= 0 ? "+" : ""}{(pnlPct * 100).toFixed(2)}%
                                </span>
                              ) : "—"}
                            </td>
                          </motion.tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </motion.div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
}
