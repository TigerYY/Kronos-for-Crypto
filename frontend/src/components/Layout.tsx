import { Link, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getPortfolio } from "../api/client";
import "./Layout.css";

export default function Layout() {
  const { data: portfolio } = useQuery({
    queryKey: ["portfolio"],
    queryFn: getPortfolio,
    refetchInterval: 30_000,
  });

  return (
    <div className="layout">
      <aside className="sidebar">
        <h2 className="sidebar-title">Kronos Trading</h2>
        <p className="sidebar-caption">多时间框架预测 · 实时监控</p>
        <nav className="sidebar-nav">
          <Link to="/">实时监控</Link>
          <Link to="/backtest">回测分析</Link>
          <Link to="/config">策略配置</Link>
          <Link to="/doc">多时间框架说明</Link>
        </nav>
        <div className="sidebar-divider" />
        <div className="sidebar-portfolio">
          <strong>组合概览</strong>
          <div className="sidebar-metric">
            可用余额: ${portfolio?.balance?.toLocaleString("en-US", { minimumFractionDigits: 2 }) ?? "—"}
          </div>
          <small>{portfolio?.last_update?.slice(0, 19) ?? "—"}</small>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
