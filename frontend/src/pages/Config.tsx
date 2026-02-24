import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getConfig, putConfig, type StrategyConfig } from "../api/client";
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

export default function Config() {
  const queryClient = useQueryClient();
  const { data: config, isLoading } = useQuery({
    queryKey: ["config"],
    queryFn: getConfig,
  });

  const saveMutation = useMutation({
    mutationFn: putConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["config"] });
      // Trigger a small delay before clearing success state if needed, here handled implicitly by react-query
    },
  });

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const data: StrategyConfig = {
      threshold: Number((form.querySelector("[name=threshold]") as HTMLInputElement)?.value) / 100,
      strong_threshold: Number((form.querySelector("[name=strong_threshold]") as HTMLInputElement)?.value) / 100,
      weights: {
        "5m": Number((form.querySelector("[name=w5m]") as HTMLInputElement)?.value),
        "15m": Number((form.querySelector("[name=w15m]") as HTMLInputElement)?.value),
        "1h": Number((form.querySelector("[name=w1h]") as HTMLInputElement)?.value),
      },
      buy_pct: Number((form.querySelector("[name=buy_pct]") as HTMLInputElement)?.value) / 100,
      max_exposure: Number((form.querySelector("[name=max_exposure]") as HTMLInputElement)?.value) / 100,
      stop_loss: Number((form.querySelector("[name=stop_loss]") as HTMLInputElement)?.value) / 100,
      take_profit: Number((form.querySelector("[name=take_profit]") as HTMLInputElement)?.value) / 100,
      min_confidence: Number((form.querySelector("[name=min_confidence]") as HTMLInputElement)?.value),
    };
    saveMutation.mutate(data);
  };

  if (isLoading || !config) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="text-neon-cyan animate-pulse tracking-widest text-lg font-medium">配置加载中...</span>
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6 pb-20"
    >
      <motion.div variants={itemVariants} className="mb-6">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">策略配置</h1>
        <p className="text-slate-400 mt-1">动态调整 Kronos 交易策略核心参数 · 仓位风控 · 信号融合</p>
      </motion.div>

      <motion.form variants={itemVariants} onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Signal Strategy Group */}
          <div className="glass-panel p-6 md:p-8 rounded-2xl border-t border-l border-white/5 space-y-6">
            <h3 className="text-xl font-bold text-white tracking-wide flex items-center gap-2 mb-4">
              <span className="w-1.5 h-6 bg-neon-cyan rounded-full inline-block" />
              信号策略权重
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <label className="flex flex-col space-y-1.5">
                <span className="text-sm text-slate-400 font-medium tracking-wide">常规信号阈值 (%)</span>
                <input
                  name="threshold"
                  type="number"
                  className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
                  min={0.1}
                  max={5}
                  step={0.1}
                  defaultValue={((config.threshold ?? 0.005) * 100).toFixed(1)}
                />
              </label>
              <label className="flex flex-col space-y-1.5">
                <span className="text-sm text-slate-400 font-medium tracking-wide">极值强信号阈值 (%)</span>
                <input
                  name="strong_threshold"
                  type="number"
                  className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-purple/50 transition-shadow"
                  min={0.5}
                  max={10}
                  step={0.5}
                  defaultValue={((config.strong_threshold ?? 0.015) * 100).toFixed(1)}
                />
              </label>
            </div>

            <div className="pt-4 border-t border-white/5 space-y-4">
              <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-widest">预测周期共振权重因子</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <label className="flex flex-col space-y-1.5">
                  <span className="text-xs text-slate-400 font-medium">5m 模型权重</span>
                  <input
                    name="w5m"
                    type="number"
                    className="bg-slate-950/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
                    min={0}
                    max={1}
                    step={0.05}
                    defaultValue={(config.weights as Record<string, number>)?.["5m"] ?? 0.2}
                  />
                </label>
                <label className="flex flex-col space-y-1.5">
                  <span className="text-xs text-slate-400 font-medium">15m 模型权重</span>
                  <input
                    name="w15m"
                    type="number"
                    className="bg-slate-950/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
                    min={0}
                    max={1}
                    step={0.05}
                    defaultValue={(config.weights as Record<string, number>)?.["15m"] ?? 0.3}
                  />
                </label>
                <label className="flex flex-col space-y-1.5">
                  <span className="text-xs text-slate-400 font-medium">1h 模型权重</span>
                  <input
                    name="w1h"
                    type="number"
                    className="bg-slate-950/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 transition-shadow"
                    min={0}
                    max={1}
                    step={0.05}
                    defaultValue={(config.weights as Record<string, number>)?.["1h"] ?? 0.5}
                  />
                </label>
              </div>
            </div>
          </div>

          {/* Risk Management Group */}
          <div className="glass-panel p-6 md:p-8 rounded-2xl border-t border-l border-white/5 space-y-6">
            <h3 className="text-xl font-bold text-white tracking-wide flex items-center gap-2 mb-4">
              <span className="w-1.5 h-6 bg-rose-500 rounded-full inline-block" />
              风控与资金管理
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <label className="flex flex-col space-y-1.5">
                <span className="text-sm text-slate-400 font-medium tracking-wide">单次买入规模 (%)</span>
                <input
                  name="buy_pct"
                  type="number"
                  className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow"
                  min={1}
                  max={50}
                  step={1}
                  defaultValue={((config.buy_pct ?? 0.15) * 100).toFixed(0)}
                />
              </label>
              <label className="flex flex-col space-y-1.5">
                <span className="text-sm text-slate-400 font-medium tracking-wide">组合敞口上限 (%)</span>
                <input
                  name="max_exposure"
                  type="number"
                  className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow"
                  min={10}
                  max={100}
                  step={5}
                  defaultValue={((config.max_exposure ?? 0.8) * 100).toFixed(0)}
                />
              </label>
              <label className="flex flex-col space-y-1.5">
                <span className="text-sm text-slate-400 font-medium tracking-wide">硬止损红线 (%)</span>
                <input
                  name="stop_loss"
                  type="number"
                  className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-rose-500/50 transition-shadow"
                  min={1}
                  max={20}
                  step={1}
                  defaultValue={((config.stop_loss ?? 0.03) * 100).toFixed(0)}
                />
              </label>
              <label className="flex flex-col space-y-1.5">
                <span className="text-sm text-slate-400 font-medium tracking-wide">移动止盈触发 (%)</span>
                <input
                  name="take_profit"
                  type="number"
                  className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-shadow"
                  min={2}
                  max={50}
                  step={1}
                  defaultValue={((config.take_profit ?? 0.08) * 100).toFixed(0)}
                />
              </label>
            </div>

            <div className="pt-4 border-t border-white/5">
              <label className="flex flex-col space-y-1.5 max-w-[50%]">
                <span className="text-sm text-slate-400 font-medium tracking-wide">最低模型共识置信度</span>
                <input
                  name="min_confidence"
                  type="number"
                  className="bg-slate-950/50 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-neon-purple/50 transition-shadow"
                  min={0.1}
                  max={0.9}
                  step={0.05}
                  defaultValue={config.min_confidence ?? 0.45}
                />
              </label>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-4 pt-4 border-t border-white/5">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={saveMutation.isPending}
            className="w-full sm:w-auto px-8 py-3 rounded-xl font-bold tracking-wide bg-white text-slate-950 shadow-[0_0_15px_rgba(255,255,255,0.2)] hover:shadow-[0_0_25px_rgba(255,255,255,0.4)] disabled:opacity-50 transition-all"
          >
            {saveMutation.isPending ? "全网同步中..." : "部署更新参量"}
          </motion.button>

          {saveMutation.isSuccess && (
            <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="text-emerald-400 font-medium flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              策略流已重组生效
            </motion.div>
          )}

          {saveMutation.isError && (
            <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="text-rose-400 font-medium flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              同步流中断: {(saveMutation.error as Error).message}
            </motion.div>
          )}
        </div>
      </motion.form>
    </motion.div>
  );
}
