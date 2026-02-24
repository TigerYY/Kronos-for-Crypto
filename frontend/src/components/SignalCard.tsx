import { motion } from "framer-motion";

type SignalCardProps = {
  action: string;
};

export default function SignalCard({ action }: SignalCardProps) {
  const isBuy = action === "BUY";
  const isSell = action === "SELL";
  const label = isBuy ? "BUY" : isSell ? "SELL" : "HOLD";

  const colorClasses = isBuy
    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.3)]"
    : isSell
      ? "bg-rose-500/10 text-rose-400 border-rose-500/50 shadow-[0_0_15px_rgba(244,63,94,0.3)]"
      : "bg-slate-500/10 text-slate-400 border-slate-500/50";

  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      className={`rounded-2xl border p-6 flex flex-col justify-center items-center backdrop-blur-md ${colorClasses}`}
    >
      <div className="text-sm font-medium tracking-widest uppercase opacity-80 mb-1">Signal</div>
      <div className="text-3xl font-black tracking-tight flex items-center gap-2">
        {isBuy && <span>▲</span>}
        {isSell && <span>▼</span>}
        {!isBuy && !isSell && <span>◆</span>}
        {label}
      </div>
    </motion.div>
  );
}
