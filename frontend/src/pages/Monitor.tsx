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
import { motion, type Variants } from "framer-motion";

const SYMBOLS = ["BTC/USDT", "ETH/USDT", "ES=F"];
const TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"];
const INITIAL_BALANCE = 10000;

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

export default function Monitor() {
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [predictResult, setPredictResult] = useState<PredictResponse | null>(null);

  const queryClient = useQueryClient();

  const { data: ohlcv = [], isLoading: ohlcvLoading } = useQuery({
    queryKey: ["ohlcv", symbol, timeframe],
    queryFn: () => getOhlcv(symbol, timeframe, 512),
    refetchInterval: autoRefresh ? 300000 : false,
  });

  const { data: trades = [], isLoading: tradesLoading } = useQuery({
    queryKey: ["trades"],
    queryFn: () => getTrades(50),
    refetchInterval: autoRefresh ? 300000 : false,
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
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6 pb-20"
    >
      {/* Header & Controls */}
      <motion.div variants={itemVariants} className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            实时预测大盘
          </h1>
          <p className="text-slate-400 mt-1">深度学习驱动的多时间框架预测系统</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2 bg-slate-900/50 p-1.5 rounded-xl border border-white/5">
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="bg-transparent border-none text-white focus:ring-0 cursor-pointer outline-none rounded-lg px-3 py-1.5 hover:bg-white/5 transition-colors"
            >
              {SYMBOLS.map((s) => (
                <option key={s} value={s} className="bg-slate-900 text-white">
                  {s}
                </option>
              ))}
            </select>
            <div className="w-px h-6 bg-white/10" />
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="bg-transparent border-none text-white focus:ring-0 cursor-pointer outline-none rounded-lg px-3 py-1.5 hover:bg-white/5 transition-colors"
            >
              {TIMEFRAMES.map((tf) => (
                <option key={tf} value={tf} className="bg-slate-900 text-white">
                  {tf}
                </option>
              ))}
            </select>
            <div className="w-px h-6 bg-white/10 mx-1" />
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-semibold transition-colors ${autoRefresh ? "text-neon-cyan/90 hover:text-neon-cyan" : "text-slate-500 hover:text-slate-300"
                }`}
              title="开启后行情与交易记录每 5 分钟自动同步"
            >
              <div className={`w-1.5 h-1.5 rounded-full ${autoRefresh ? "bg-neon-cyan animate-pulse shadow-[0_0_5px_rgba(0,240,255,0.8)]" : "bg-slate-600"}`} />
              自动同步
            </button>
          </div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="px-6 py-2.5 rounded-xl font-medium tracking-wide bg-gradient-to-r from-neon-cyan to-blue-500 text-slate-950 shadow-[0_0_15px_rgba(0,240,255,0.4)] disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-[0_0_25px_rgba(0,240,255,0.6)] transition-all duration-300"
            onClick={() => predictMutation.mutate()}
            disabled={predictMutation.isPending}
          >
            {predictMutation.isPending ? "全时空预测演算中..." : "启动 AI 预测"}
          </motion.button>
        </div>
      </motion.div>

      {predictMutation.isError && (
        <motion.div variants={itemVariants} className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-xl">
          ⚠️ 预测系统加载失败: {(predictMutation.error as Error).message}
        </motion.div>
      )}

      {/* KPI Metrics */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="当前标记价格"
          value={
            currentPrice != null
              ? `$${currentPrice.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
              : "—"
          }
        />
        <MetricCard
          label={`${timeframe} 预测目标价`}
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
        <div className="flex h-full">
          {signal ? (
            <div className="w-full h-full flex flex-col justify-stretch">
              <SignalCard action={signal.action} />
            </div>
          ) : (
            <div className="w-full h-full glass-panel rounded-2xl p-6 flex flex-col justify-center items-center opacity-70">
              <div className="text-sm font-medium tracking-widest uppercase mb-1">综合信号</div>
              <div className="text-3xl font-black tracking-tight text-slate-500">—</div>
            </div>
          )}
        </div>
        <MetricCard
          label="组合实时净值"
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
      </motion.div>

      {/* Main Chart Area */}
      <motion.div variants={itemVariants} className="glass-panel rounded-2xl p-4 md:p-6 overflow-hidden border-t border-l border-white/5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-white tracking-wide">时空结构演化图谱</h3>
          {ohlcvLoading && <span className="text-sm text-neon-cyan animate-pulse">实时同步中...</span>}
        </div>
        <div className="w-full relative h-[500px] -mx-4 md:mx-0">
          {!ohlcvLoading && (
            <div className="absolute inset-0">
              <KlineChart
                data={ohlcv}
                predSeries={predSeries}
                symbol={symbol}
                timeframe={timeframe}
              />
            </div>
          )}

          {/* AI Prediction Zoom Inset */}
          {!ohlcvLoading && predSeries && predSeries.length > 0 && ohlcv.length > 0 && (
            <div className="absolute top-4 left-16 md:left-24 w-48 md:w-72 h-36 md:h-56 glass-panel rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.8)] border border-white/20 z-50 flex flex-col p-2 pointer-events-none bg-[#0d1117]/80 backdrop-blur-md">
              <div className="flex items-center justify-between px-2 pt-1 mb-1">
                <span className="text-xs font-bold text-neon-cyan tracking-wider flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-pulse"></span>
                  预测特写 🔍
                </span>
                <span className="text-[10px] text-slate-400 font-mono bg-white/5 px-2 py-0.5 rounded">{timeframe}</span>
              </div>
              <div className="flex-1 w-full overflow-hidden relative">
                <KlineChart
                  data={ohlcv.slice(-15)}
                  predSeries={predSeries}
                  symbol={symbol}
                  timeframe={timeframe}
                  minimal={true}
                />
              </div>
            </div>
          )}
        </div>
      </motion.div>

      {/* Multi-Timeframe Signals */}
      {signal && (
        <motion.div variants={itemVariants} className="space-y-4">
          <h3 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
            <span className="w-1.5 h-6 bg-neon-purple rounded-full inline-block" />
            多重分形预测矩阵
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {["15m", "1h", "4h", "1d"].map((tf) => {
              const pred = predictResult?.predictions?.[tf];
              if (pred == null) return null;
              const chg =
                currentPrice != null
                  ? ((pred - currentPrice) / currentPrice) * 100
                  : 0;
              const isPos = chg >= 0;
              return (
                <div key={tf} className="glass-panel p-4 rounded-xl flex flex-col items-center justify-center border-t border-white/10 hover:bg-white/5 transition-colors">
                  <span className="text-sm text-slate-400 font-semibold mb-1 uppercase tracking-wider">{tf} 模型</span>
                  <span className="text-xl font-bold text-white mb-1">${pred.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
                  <span className={`text-sm font-medium ${isPos ? 'text-neon-cyan' : 'text-rose-400'}`}>
                    {isPos ? "+" : ""}{chg.toFixed(2)}%
                  </span>
                </div>
              );
            })}
          </div>

          <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row items-center gap-6 mt-4">
            <div className="flex-1 w-full">
              <div className="flex justify-between items-end mb-2">
                <span className="text-sm text-slate-400 tracking-wide font-medium">模型综合置信度评估</span>
                <span className="text-lg font-bold text-neon-purple">{(signal.confidence * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${signal.confidence * 100}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="bg-gradient-to-r from-neon-purple to-neon-cyan h-2.5 rounded-full"
                />
              </div>
            </div>

            <div className="flex-1 w-full">
              <span className="text-sm text-slate-400 tracking-wide font-medium block mb-2">决策归因因子 (Feature Attribution)</span>
              <div className="flex flex-wrap gap-2">
                {signal.reasons.map((r, i) => (
                  <span key={i} className="px-3 py-1 bg-white/5 border border-white/10 rounded-md text-xs text-slate-300">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Recent Trades Table */}
      <motion.div variants={itemVariants} className="space-y-4">
        <h3 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
          <span className="w-1.5 h-6 bg-blue-500 rounded-full inline-block" />
          系统决策账单
        </h3>

        <div className="glass-panel rounded-2xl overflow-hidden border-t border-white/10">
          <div className="overflow-x-auto">
            {tradesLoading ? (
              <div className="p-8 text-center text-slate-400 animate-pulse">同步交易记录中...</div>
            ) : trades.length === 0 ? (
              <div className="p-8 text-center text-slate-500">当前周期暂无新策略成交</div>
            ) : (
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="text-xs uppercase bg-slate-900/50 text-slate-400 border-b border-white/5">
                  <tr>
                    <th scope="col" className="px-6 py-4 font-medium">时间 (UTC)</th>
                    <th scope="col" className="px-6 py-4 font-medium">标的</th>
                    <th scope="col" className="px-6 py-4 font-medium">AI 决策</th>
                    <th scope="col" className="px-6 py-4 font-medium text-right">均价</th>
                    <th scope="col" className="px-6 py-4 font-medium text-right">规模数量</th>
                    <th scope="col" className="px-6 py-4 font-medium text-right">快照净值</th>
                    <th scope="col" className="px-6 py-4 font-medium">触发诱因归因</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {[...trades].reverse().slice(0, 15).map((t, i) => (
                    <motion.tr
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="hover:bg-white/5 transition-colors"
                    >
                      <td className="px-6 py-4 font-mono text-xs whitespace-nowrap">{t.timestamp != null ? String(t.timestamp).slice(0, 19).replace('T', ' ') : "—"}</td>
                      <td className="px-6 py-4 font-medium text-white">{t.symbol ?? "—"}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-bold ${t.action === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' :
                          t.action === 'SELL' ? 'bg-rose-500/20 text-rose-400' :
                            'bg-slate-700 text-slate-300'
                          }`}>
                          {t.action ?? "—"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-mono">${t.price != null ? t.price.toFixed(2) : "—"}</td>
                      <td className="px-6 py-4 text-right font-mono text-slate-400">{t.amount != null ? t.amount.toFixed(6) : "—"}</td>
                      <td className="px-6 py-4 text-right font-mono">${t.portfolio_value != null ? t.portfolio_value.toFixed(2) : "—"}</td>
                      <td className="px-6 py-4 text-xs text-slate-400 truncate max-w-[200px]" title={t.reason}>{t.reason ?? "—"}</td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
