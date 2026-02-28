import { useState, useEffect } from "react";
import { useQuery, useQueries, useQueryClient } from "@tanstack/react-query";
import {
  getOhlcv,
  getTrades,
  postPredict,
} from "../api/client";
import KlineChart from "../components/KlineChart";
import SignalCard from "../components/SignalCard";
import MetricCard from "../components/MetricCard";
import { motion, type Variants } from "framer-motion";

const SYMBOLS = ["BTC/USDT", "ETH/USDT", "ES=F", "XAU/USDT"];
const SYMBOL_LABELS: Record<string, string> = {
  "ES=F": "SPX500",
  "XAU/USDT": "XAU/USDT 🥇",
};
const TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"];
const INITIAL_BALANCE = 10000;
const REFRESH_INTERVAL_MS = 300000; // 5分钟

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
}

export default function Monitor() {
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [timeLeft, setTimeLeft] = useState(REFRESH_INTERVAL_MS / 1000);

  const queryClient = useQueryClient();

  // 1. 获取 OHLCV (受自动同步控制)
  const { data: ohlcv = [], isLoading: ohlcvLoading, isFetching: ohlcvFetching } = useQuery({
    queryKey: ["ohlcv", symbol, timeframe],
    queryFn: () => getOhlcv(symbol, timeframe, 512),
    refetchInterval: autoRefresh ? REFRESH_INTERVAL_MS : false,
  });

  // 2. 预测 AI 数据 (同样受自动同步控制)
  const predictQuery = useQuery({
    queryKey: ["predict", symbol],
    queryFn: () => postPredict(symbol, ["5m", "15m", "1h", "4h", "1d"]),
    refetchInterval: autoRefresh ? REFRESH_INTERVAL_MS : false,
  });

  // 3. 并发获取底部 4 张卡片的微型背景 K 线（只取 50 根）
  const cardTimeframes = ["15m", "1h", "4h", "1d"];
  const cardOhlcvQueries = useQueries({
    queries: cardTimeframes.map((tf) => ({
      queryKey: ["ohlcv", symbol, tf, "cards"],
      queryFn: () => getOhlcv(symbol, tf, 4),
      refetchInterval: autoRefresh ? REFRESH_INTERVAL_MS : false,
    })),
  });

  // 预测数据更新后，自动刷新账户资金与交易记录
  useEffect(() => {
    if (predictQuery.data) {
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      queryClient.invalidateQueries({ queryKey: ["trades"] });
    }
  }, [predictQuery.data, queryClient]);

  // 倒计时逻辑
  useEffect(() => {
    // 每次开始拉取新数据时重置倒计时
    if (ohlcvFetching) {
      setTimeLeft(REFRESH_INTERVAL_MS / 1000);
      return;
    }

    if (!autoRefresh) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : REFRESH_INTERVAL_MS / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [autoRefresh, ohlcvFetching]);

  const { data: trades = [], isLoading: tradesLoading } = useQuery({
    queryKey: ["trades"],
    queryFn: () => getTrades(50),
    refetchInterval: autoRefresh ? REFRESH_INTERVAL_MS : false,
  });

  const predictResult = predictQuery.data;

  const currentPrice = predictResult?.current_price;
  const predictedPrice = predictResult?.predictions?.[timeframe];
  const signal = predictResult?.signal;
  const rlAlignment = predictResult?.rl_alignment;
  const fundamentals = predictResult?.fundamentals;
  const rag = predictResult?.rag;
  const isRagAlert = rag && rag.override_signal !== "NONE";
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
                  {SYMBOL_LABELS[s] ?? s}
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
              onClick={() => {
                setAutoRefresh(!autoRefresh);
                if (!autoRefresh) setTimeLeft(REFRESH_INTERVAL_MS / 1000);
              }}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${autoRefresh ? "text-neon-cyan hover:bg-neon-cyan/10" : "text-slate-500 hover:bg-white/5"
                }`}
              title="开启后行情与交易记录每 5 分钟自动同步"
            >
              <div className="relative flex items-center justify-center w-2 h-2">
                {autoRefresh ? (
                  <>
                    <div className="absolute inline-flex w-full h-full rounded-full bg-neon-cyan opacity-75 animate-ping" />
                    <div className="relative inline-flex w-1.5 h-1.5 rounded-full bg-neon-cyan" />
                  </>
                ) : (
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-600" />
                )}
              </div>
              <div className="flex flex-col items-start -space-y-0.5 min-w-[3.5rem]">
                <span>自动同步</span>
                {autoRefresh && (
                  <span className="text-[10px] font-mono text-neon-cyan/70 tracking-tighter">
                    {Math.floor(timeLeft / 60).toString().padStart(2, '0')}:{(timeLeft % 60).toString().padStart(2, '0')}
                  </span>
                )}
              </div>
            </button>
          </div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="px-6 py-2.5 rounded-xl font-medium tracking-wide bg-gradient-to-r from-neon-cyan to-blue-500 text-slate-950 shadow-[0_0_15px_rgba(0,240,255,0.4)] disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-[0_0_25px_rgba(0,240,255,0.6)] transition-all duration-300"
            onClick={() => {
              setTimeLeft(REFRESH_INTERVAL_MS / 1000);
              predictQuery.refetch();
              queryClient.invalidateQueries({ queryKey: ["ohlcv", symbol, timeframe] });
            }}
            disabled={predictQuery.isFetching}
          >
            {predictQuery.isFetching ? "全时空预测演算中..." : "启动 AI 预测"}
          </motion.button>
        </div>
      </motion.div>

      {predictQuery.isError && (
        <motion.div variants={itemVariants} className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-xl">
          ⚠️ 预测系统加载失败: {(predictQuery.error as Error).message}
        </motion.div>
      )}

      {/* RAG Macro Intervention Radar */}
      {rag && (
        <motion.div
          variants={itemVariants}
          animate={isRagAlert ? { scale: [1, 1.02, 1], boxShadow: ["0px 0px 0px rgba(225,29,72,0)", "0px 0px 30px rgba(225,29,72,0.6)", "0px 0px 0px rgba(225,29,72,0)"] } : {}}
          transition={isRagAlert ? { repeat: Infinity, duration: 2 } : {}}
          className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all duration-500 ${isRagAlert ? 'bg-rose-950/40 border-rose-500/50 shadow-[0_0_15px_rgba(225,29,72,0.3)]' : 'bg-slate-900/40 border-slate-700/50'}`}
        >
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${isRagAlert ? 'bg-rose-500 animate-pulse' : 'bg-emerald-500'}`} />
            <div>
              <h3 className={`text-sm tracking-widest uppercase font-bold ${isRagAlert ? 'text-rose-400' : 'text-slate-400'}`}>
                {isRagAlert ? "MACRO RAG INTERVENTION ACTIVE" : "Macro RAG Radar: Neural System Safe"}
              </h3>
              {isRagAlert && (
                <p className="text-white mt-1 text-sm">{rag.reason || "Extreme macro volatility detected."}</p>
              )}
            </div>
          </div>
          {isRagAlert && (
            <div className="px-4 py-1.5 rounded bg-rose-500/20 text-rose-400 font-bold tracking-widest text-sm border border-rose-500/30">
              OVERRIDE: {rag.override_signal}
            </div>
          )}
        </motion.div>
      )}

      {/* KPI Metrics */}
      <motion.div variants={itemVariants} className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-2 lg:gap-3">
        <MetricCard
          label="当前标记价格"
          value={
            currentPrice != null
              ? `$${currentPrice.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : "—"
          }
        />
        <MetricCard
          label={`${timeframe} 预测目标价`}
          value={
            predictedPrice != null
              ? `$${predictedPrice.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
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
            <div className="w-full h-full glass-panel rounded-2xl p-4 lg:p-5 flex flex-col justify-center items-center opacity-70">
              <div className="text-xs font-medium tracking-widest uppercase mb-1">综合信号</div>
              <div className="text-2xl font-black tracking-tight text-slate-500">—</div>
            </div>
          )}
        </div>
        <MetricCard
          label="组合实时净值"
          value={
            totalValue != null
              ? `$${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : portfolio?.balance != null
                ? `$${portfolio.balance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
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
        {/* Custom FGI Card with Visual Gauge */}
        <div className="glass-panel p-3 lg:p-4 rounded-xl flex flex-col justify-between border-t border-white/10 relative overflow-hidden group">
          <div className="flex justify-between items-center z-10">
            <span className="text-[11px] font-medium text-slate-400 tracking-wide">全球恐慌贪婪</span>
          </div>
          <div className="mt-1.5 md:mt-2 z-10 flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <span className={`text-lg lg:text-xl font-bold tabular-nums tracking-tighter ${fundamentals?.fgi?.value != null ? 'text-white' : 'text-slate-500'}`}>
                {fundamentals?.fgi?.value != null ? fundamentals.fgi.value : "—"}
              </span>
              {fundamentals?.fgi?.value != null && (
                <span className={`text-[9px] lg:text-[10px] uppercase font-bold px-1.5 py-0.5 rounded-sm ${Number(fundamentals.fgi.value) < 25 ? 'bg-rose-500/20 text-rose-500' :
                  Number(fundamentals.fgi.value) < 45 ? 'bg-orange-500/20 text-orange-500' :
                    Number(fundamentals.fgi.value) < 55 ? 'bg-yellow-500/20 text-yellow-500' :
                      Number(fundamentals.fgi.value) < 75 ? 'bg-emerald-400/20 text-emerald-400' :
                        'bg-green-400/20 text-green-400'
                  }`}>
                  {fundamentals.fgi.classification || "获取中"}
                </span>
              )}
            </div>
            <div className="w-full relative h-[6px] mt-1">
              {/* Gradient background track */}
              <div className="absolute inset-0 rounded-full bg-gradient-to-r from-rose-500 via-yellow-500 to-green-500 opacity-70" />
              {/* Indicator thumb */}
              {fundamentals?.fgi?.value != null && (
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-2 h-2.5 bg-white border border-slate-800 rounded-[2px] shadow-sm shadow-black/50 transition-all duration-700 ease-out z-10"
                  style={{ left: `calc(${Math.min(100, Math.max(0, Number(fundamentals.fgi.value)))}% - 4px)` }}
                />
              )}
            </div>
          </div>
        </div>
        <MetricCard
          label="永续资金费率"
          value={
            fundamentals?.funding_rate != null
              ? `${(fundamentals.funding_rate * 100).toFixed(4)}%`
              : "—"
          }
          delta={
            fundamentals?.funding_rate != null
              ? (fundamentals.funding_rate > 0 ? "多付空" : fundamentals.funding_rate < 0 ? "空付多" : "基准")
              : undefined
          }
          positive={
            fundamentals?.funding_rate != null ? fundamentals.funding_rate <= 0 : undefined
          }
        />
        {/* Custom RL Value Card with Visual Gauge */}
        <div className="glass-panel p-3 lg:p-4 rounded-xl flex flex-col justify-between border-t border-white/10 relative overflow-hidden group">
          <div className="flex justify-between items-center z-10">
            <span className="text-[11px] font-medium text-slate-400 tracking-wide">RL 风控期望</span>
          </div>
          <div className="mt-1.5 md:mt-2 z-10 flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <span className={`text-lg lg:text-xl font-bold tracking-tighter ${rlAlignment != null ? 'text-white' : 'text-slate-500'}`}>
                {rlAlignment != null
                  ? (rlAlignment.action === 0 ? "做空 (S)" : rlAlignment.action === 1 ? "观望 (H)" : "做多 (L)")
                  : "未对齐"}
              </span>
              {rlAlignment != null && (
                <span className={`text-[9px] lg:text-[10px] font-bold px-1.5 py-0.5 rounded-sm tabular-nums tracking-wide ${rlAlignment.value > 0.05 ? 'bg-emerald-500/20 text-emerald-400' :
                  rlAlignment.value < -0.05 ? 'bg-rose-500/20 text-rose-500' :
                    'bg-slate-500/20 text-slate-300'
                  }`}>
                  V: {rlAlignment.value > 0 ? "+" : ""}{rlAlignment.value.toFixed(4)}
                </span>
              )}
            </div>
            <div className="w-full relative h-[6px] mt-1">
              {/* Gradient background track */}
              <div className="absolute inset-0 rounded-full bg-gradient-to-r from-rose-500 via-slate-500 to-emerald-500 opacity-70" />
              {/* Indicator thumb: Value mapped from [-1.0, 1.0] to [0%, 100%] */}
              {rlAlignment != null && (
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-2 h-2.5 bg-white border border-slate-800 rounded-[2px] shadow-sm shadow-black/50 transition-all duration-700 ease-out z-10"
                  style={{ left: `calc(${Math.min(100, Math.max(0, ((rlAlignment.value + 1) / 2) * 100))}% - 4px)` }}
                />
              )}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Multi-Timeframe Signals */}
      <motion.div variants={itemVariants} className="space-y-4">
        <h3 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
          <span className="w-1.5 h-6 bg-neon-purple rounded-full inline-block" />
          多时间框架信号
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {cardTimeframes.map((tf, index) => {
            const predTarget = predictResult?.predictions?.[tf];
            const series = predictResult?.pred_series?.[tf];
            const tfOhlcv = cardOhlcvQueries[index].data || [];

            if (predTarget == null) {
              return (
                <div key={tf} className="glass-panel py-3 px-4 rounded-xl flex flex-col items-center justify-center border-t border-white/10 opacity-50 relative overflow-hidden h-28">
                  <span className="text-xs text-slate-400 font-semibold mb-1 uppercase tracking-wider relative z-10">{tf} 模型</span>
                  <span className="text-lg font-bold text-slate-500 mb-0.5 relative z-10">—</span>
                  <span className="text-xs font-medium text-slate-500 relative z-10">—</span>
                </div>
              );
            }
            const chg =
              currentPrice != null
                ? ((predTarget - currentPrice) / currentPrice) * 100
                : 0;
            const isPos = chg >= 0;

            return (
              <div key={tf} className="glass-panel p-4 rounded-xl flex flex-col border-t border-white/10 hover:bg-white/5 transition-colors relative h-28 overflow-hidden group">
                <div className="flex justify-between items-start w-full relative z-10">
                  <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">{tf} 预测</span>
                  <div className="flex flex-col items-end">
                    <span className="text-sm font-bold text-white leading-tight drop-shadow-md">
                      ${predTarget.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm mt-0.5 ${isPos ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                      {isPos ? "+" : ""}{chg.toFixed(2)}%
                    </span>
                  </div>
                </div>

                <div className="absolute inset-x-0 bottom-0 w-full h-[70%] opacity-90 pointer-events-none">
                  {tfOhlcv.length > 0 && (
                    <KlineChart
                      data={tfOhlcv}
                      predSeries={series}
                      symbol={symbol}
                      timeframe={tf}
                      minimal={true}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>


      </motion.div>

      {/* Main Chart Area */}
      <motion.div variants={itemVariants} className="glass-panel rounded-2xl p-4 md:p-6 overflow-hidden border-t border-l border-white/5">
        <div className="flex items-center justify-between mb-2">
          <div className="flex flex-col gap-1">
            <h3 className="text-lg font-bold text-white tracking-wide">时空结构演化图谱</h3>
            {ohlcvLoading && <span className="text-sm text-neon-cyan animate-pulse">实时同步中...</span>}
          </div>

          {/* Signal Confidence floating indicator */}
          <div className="flex flex-col items-end gap-1.5 min-w-[140px]">
            <span className="text-xs text-slate-400 font-medium tracking-widest uppercase">模型置信度</span>
            {signal ? (
              <div className="flex items-center gap-3 w-full justify-end">
                <div className="w-24 bg-slate-800 rounded-full h-1.5 overflow-hidden flex-shrink-0">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${signal.confidence * 100}%` }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    className="bg-gradient-to-r from-neon-purple to-neon-cyan h-1.5 rounded-full"
                  />
                </div>
                <span className="text-sm font-bold text-neon-cyantabular-nums">
                  {(signal.confidence * 100).toFixed(1)}%
                </span>
              </div>
            ) : (
              <span className="text-sm font-bold text-slate-600">—</span>
            )}
          </div>
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


        </div>
      </motion.div>

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
