import { useMemo } from "react";
import Plot from "react-plotly.js";
import type { OhlcvBar } from "../api/client";

type KlineChartProps = {
  data: OhlcvBar[];
  predSeries?: number[];
  symbol: string;
  timeframe: string;
  minimal?: boolean;
};

// 将时间字符串转为毫秒时间戳，与 K 线 x 轴一致
function parseToMs(ts: string): number {
  const d = new Date(ts.replace(" ", "T"));
  return isNaN(d.getTime()) ? 0 : d.getTime();
}

// 按周期计算下一根 K 线的时间戳（毫秒）
function addIntervalMs(ms: number, timeframe: string): number {
  const d = new Date(ms);
  const map: Record<string, number> = {
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
  };
  const step = map[timeframe] ?? 60 * 60 * 1000;
  return d.getTime() + step;
}

export default function KlineChart({ data, predSeries, symbol, timeframe, minimal = false }: KlineChartProps) {
  const { xMs, open, high, low, close } = useMemo(() => {
    if (!data?.length)
      return { xMs: [] as number[], open: [], high: [], low: [], close: [] };
    const xMs = data.map((b) => parseToMs(b.timestamps));
    return {
      xMs,
      open: data.map((b) => b.open),
      high: data.map((b) => b.high),
      low: data.map((b) => b.low),
      close: data.map((b) => b.close),
    };
  }, [data]);

  const predTrace = useMemo(() => {
    if (!predSeries?.length || !data?.length) return null;
    const lastTsStr = data[data.length - 1].timestamps;
    const lastClose = close.length ? close[close.length - 1] : 0;
    // 使用与 K 线一致的 x 轴：统一为时间戳（毫秒），避免格式混用导致错位与断裂
    let lastMs = parseToMs(lastTsStr);
    const predXMs: number[] = [lastMs];
    for (let i = 0; i < predSeries.length; i++) {
      lastMs = addIntervalMs(lastMs, timeframe);
      predXMs.push(lastMs);
    }
    const predY = [lastClose, ...predSeries];
    return {
      x: predXMs,
      y: predY,
      type: "scatter",
      mode: "lines",
      name: "Kronos 预测",
      line: { color: "#f39c12", width: minimal ? 4 : 2.5, dash: "dash" },
      connectgaps: true,
    };
  }, [predSeries, data, close, timeframe]);

  const traces: object[] = [
    {
      x: xMs,
      open,
      high,
      low,
      close,
      type: "candlestick",
      name: "OHLC",
      increasing: { line: { color: "#00ff88" } },
      decreasing: { line: { color: "#ff4757" } },
    },
  ];
  if (predTrace) traces.push(predTrace);

  return (
    <Plot
      data={traces}
      layout={{
        template: "plotly_dark",
        paper_bgcolor: minimal ? "rgba(0,0,0,0)" : "#0d1117",
        plot_bgcolor: minimal ? "rgba(0,0,0,0)" : "#0d1117",
        height: minimal ? 180 : 500,
        title: minimal ? undefined : `${symbol} · ${timeframe}`,
        xaxis: {
          type: "date",
          rangeslider: { visible: false },
          gridcolor: "#1e2a3a",
          visible: !minimal,
        },
        yaxis: {
          gridcolor: "#1e2a3a",
          visible: !minimal,
        },
        margin: minimal ? { t: 5, b: 5, l: 5, r: 5 } : { t: 40, b: 40, l: 60, r: 40 },
        showlegend: false,
      }}
      config={minimal ? { displayModeBar: false, responsive: true } : { responsive: true }}
      style={{ width: "100%" }}
    />
  );
}
