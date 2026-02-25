import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getPortfolio } from "../api/client";
import { motion } from "framer-motion";

export default function Layout() {
  const { data: portfolio } = useQuery({
    queryKey: ["portfolio"],
    queryFn: getPortfolio,
    refetchInterval: 30_000,
  });

  const navItems = [
    { to: "/", label: "实时预测" },
    { to: "/backtest", label: "回测分析" },
    { to: "/config", label: "策略配置" },
    { to: "/doc", label: "K进化纪元" },
  ];

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-200">
      {/* Sidebar */}
      <aside className="w-64 flex-none glass-panel m-4 rounded-2xl flex flex-col pt-8 pb-6 px-4">
        <div className="mb-10 px-2">
          <h2 className="text-2xl font-bold bg-gradient-to-r from-neon-cyan to-neon-purple bg-clip-text text-transparent">
            Kronos Trading
          </h2>
          <p className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-semibold">
            模型驱动 · 实时预测
          </p>
        </div>

        <nav className="flex-1 space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-4 py-3 rounded-xl transition-all duration-200 relative overflow-hidden group ${isActive
                  ? "text-white font-medium bg-white/5"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="active-nav-bg"
                      className="absolute inset-0 bg-gradient-to-r from-neon-cyan/20 to-transparent shadow-[inset_4px_0_0_0_var(--color-neon-cyan)]"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                  <span className="relative z-10">{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto px-4 pt-6 border-t border-white/10">
          <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-2">
            组合概览
          </p>
          <div className="text-xl font-bold text-white tracking-tight mb-1">
            ${portfolio?.balance?.toLocaleString("en-US", { minimumFractionDigits: 2 }) ?? "—"}
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            UPDATED: {portfolio?.last_update?.slice(11, 19) ?? "—"}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-4 lg:p-8 overflow-y-auto">
        <div className="max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
