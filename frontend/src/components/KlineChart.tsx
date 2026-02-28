import { useEffect, useRef } from "react";
import { createChart, ColorType, CrosshairMode, CandlestickSeries, LineSeries } from "lightweight-charts";
import type { Time } from "lightweight-charts";
import type { OhlcvBar } from "../api/client";

type KlineChartProps = {
  data: OhlcvBar[];
  predSeries?: number[];
  symbol: string;
  timeframe: string;
  minimal?: boolean;
};

// Utilities for time manipulation (UTC)
function parseToUnix(ts: string): Time {
  // Ensure the timestamp string is treated as UTC
  const d = new Date(ts.replace(" ", "T") + "Z");
  return (isNaN(d.getTime()) ? 0 : Math.floor(d.getTime() / 1000)) as Time;
}

function addIntervalSeconds(unixTime: number, timeframe: string): number {
  const map: Record<string, number> = {
    "5m": 5 * 60,
    "15m": 15 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
  };
  const step = map[timeframe] ?? 3600;
  return unixTime + step;
}

export default function KlineChart({ data, predSeries, symbol, timeframe, minimal = false }: KlineChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // 1. Initialize TradingView Chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: minimal ? "transparent" : "#0d1117" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: minimal ? "transparent" : "#1e2a3a" },
        horzLines: { color: minimal ? "transparent" : "#1e2a3a" },
      },
      crosshair: {
        mode: minimal ? CrosshairMode.Hidden : CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: "#1e2a3a",
        visible: !minimal,
      },
      timeScale: {
        borderColor: "#1e2a3a",
        timeVisible: true,
        secondsVisible: false,
        visible: !minimal,
      },
      handleScroll: !minimal,
      handleScale: !minimal,
    });

    // 2. Add Main Candlestick Series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",    // emerald-500
      downColor: "#f43f5e",  // rose-500
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#f43f5e",
    });

    // Parse main K-line data
    if (data && data.length > 0) {
      const tvData = data.map((b) => ({
        time: parseToUnix(b.timestamps),
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }));
      // lightweight-charts requires data to be strictly sorted by time ascending
      tvData.sort((a, b) => (a.time as number) - (b.time as number));
      candleSeries.setData(tvData);
    }

    // 3. Add AI Prediction Projection Overlay (Line)
    if (!minimal && predSeries && predSeries.length > 0 && data && data.length > 0) {
      const predLineSeries = chart.addSeries(LineSeries, {
        color: "#00f0ff", // neon-cyan
        lineWidth: 2,
        lineStyle: 1, // Dashed
        crosshairMarkerVisible: true,
        lastPriceAnimation: 1,
      });

      const lastCandle = data[data.length - 1];
      const lastUnix = parseToUnix(lastCandle.timestamps) as number;
      const lastClose = lastCandle.close;

      const predTvData: { time: Time; value: number }[] = [];

      // Start the prediction line from the most recent close
      predTvData.push({ time: lastUnix as Time, value: lastClose });

      let currentUnix = lastUnix;
      predSeries.forEach((predValue) => {
        currentUnix = addIntervalSeconds(currentUnix, timeframe);
        predTvData.push({ time: currentUnix as Time, value: predValue });
      });

      predLineSeries.setData(predTvData);
    }

    // Fit content
    chart.timeScale().fitContent();

    // Responsive Canvas
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length === 0 || entries[0].target !== chartContainerRef.current) return;
      const newRect = entries[0].contentRect;
      chart.applyOptions({ width: newRect.width, height: newRect.height });
    });
    resizeObserver.observe(chartContainerRef.current);

    // Cleanup
    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [data, predSeries, minimal, timeframe]);

  return (
    <div className="absolute inset-0 z-0">
      <div
        ref={chartContainerRef}
        className="w-full h-full relative z-10"
        style={{ userSelect: "none", WebkitUserSelect: "none" }}
      />
      {!minimal && (
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center z-20">
          <div className="text-[6rem] font-black text-white/5 uppercase tracking-widest text-center leading-none">
            {symbol}<br />{timeframe}
          </div>
        </div>
      )}
    </div>
  );
}
