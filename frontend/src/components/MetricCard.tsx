import { motion } from "framer-motion";

type MetricCardProps = {
  label: string;
  value: string;
  delta?: string;
  positive?: boolean;
};

export default function MetricCard({ label, value, delta, positive }: MetricCardProps) {
  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.02 }}
      className="glass-panel rounded-xl p-3 lg:p-4 flex flex-col justify-center relative overflow-hidden group h-full w-full"
    >
      <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full blur-3xl -mr-10 -mt-10 transition-transform group-hover:scale-150 duration-500" />
      <div className="text-[11px] text-slate-400 font-medium tracking-wide mb-1 relative z-10">{label}</div>
      <div className="text-lg lg:text-xl font-bold text-white tracking-tighter relative z-10 truncate" title={value}>{value}</div>
      {delta != null && (
        <div
          className={`text-[10px] font-semibold mt-1.5 relative z-10 flex items-center ${positive ? "text-neon-cyan" : "text-rose-400"
            }`}
        >
          {positive ? "↑" : "↓"} {delta}
        </div>
      )}
    </motion.div>
  );
}
