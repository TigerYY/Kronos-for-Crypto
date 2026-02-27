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
      className="glass-panel rounded-2xl p-5 lg:p-6 flex flex-col justify-center relative overflow-hidden group h-full w-full"
    >
      <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full blur-3xl -mr-10 -mt-10 transition-transform group-hover:scale-150 duration-500" />
      <div className="text-sm text-slate-400 font-medium tracking-wide mb-2 relative z-10">{label}</div>
      <div className="text-2xl lg:text-3xl font-bold text-white tracking-tight relative z-10 truncate" title={value}>{value}</div>
      {delta != null && (
        <div
          className={`text-sm font-semibold mt-2 relative z-10 flex items-center ${positive ? "text-neon-cyan" : "text-rose-400"
            }`}
        >
          {positive ? "↑" : "↓"} {delta}
        </div>
      )}
    </motion.div>
  );
}
