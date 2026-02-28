import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getPortfolio } from "../api/client";
import { motion, AnimatePresence } from "framer-motion";

export default function Layout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

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
    <div className="flex min-h-screen bg-slate-950 text-slate-200 overflow-hidden">
      {/* Sidebar */}
      <AnimatePresence initial={false}>
        {isSidebarOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0, marginLeft: 0 }}
            animate={{ width: "17rem", opacity: 1, marginLeft: "1rem" }}
            exit={{ width: 0, opacity: 0, marginLeft: 0 }}
            transition={{ type: "spring", bounce: 0, duration: 0.3 }}
            className="flex-none z-40 my-4 flex"
          >
            <aside className="w-64 glass-panel rounded-2xl flex flex-col pt-8 pb-6 px-4 relative shadow-2xl overflow-hidden min-h-[calc(100vh-2rem)]">
              {/* Close Button */}
              <button
                onClick={() => setIsSidebarOpen(false)}
                className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors z-50"
                title="折叠菜单"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>

              <div className="mb-10 px-2 mt-2">
                <h2 className="text-2xl font-bold bg-gradient-to-r from-neon-cyan to-neon-purple bg-clip-text text-transparent truncate">
                  Kronos Trading
                </h2>
                <p className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-semibold truncate">
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
                        <span className="relative z-10 whitespace-nowrap">{item.label}</span>
                      </>
                    )}
                  </NavLink>
                ))}
              </nav>

              <div className="mt-auto px-4 pt-6 border-t border-white/10">
                <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-2">
                  组合概览
                </p>
                <div className="text-xl font-bold text-white tracking-tight mb-1 truncate">
                  ${portfolio?.balance?.toLocaleString("en-US", { minimumFractionDigits: 2 }) ?? "—"}
                </div>
                <div className="text-[10px] text-slate-500 font-mono truncate">
                  UPDATED: {portfolio?.last_update?.slice(11, 19) ?? "—"}
                </div>
              </div>
            </aside>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <main className="flex-1 p-4 lg:p-8 h-screen overflow-y-auto relative w-full">
        <div className="max-w-7xl mx-auto flex flex-col min-h-full">
          {/* Header Row for Toggle Button when Sidebar is collapsed */}
          <div className="mb-4 flex items-center min-h-12 w-full">
            <AnimatePresence>
              {!isSidebarOpen && (
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.2 }}
                  className="flex items-center"
                >
                  <button
                    onClick={() => setIsSidebarOpen(true)}
                    className="p-2 mr-4 glass-panel rounded-xl hover:bg-white/10 transition-colors text-slate-300 hover:text-white shadow-lg flex-shrink-0"
                    title="展开菜单"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                  </button>

                  <div className="flex flex-col">
                    <h2 className="text-xl font-bold bg-gradient-to-r from-neon-cyan to-neon-purple bg-clip-text text-transparent">
                      Kronos Trading
                    </h2>
                    <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                      模型驱动 · 实时预测
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Right side spacer or future header content */}
            <div className="flex-1"></div>
          </div>

          {/* Outlet Container */}
          <div className="flex-1 relative">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
