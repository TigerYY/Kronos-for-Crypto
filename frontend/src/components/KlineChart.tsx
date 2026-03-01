import { useEffect, useRef } from "react";
import { createChart, ColorType, CrosshairMode, CandlestickSeries, HistogramSeries } from "lightweight-charts";
import type { Time } from "lightweight-charts";
import type { OhlcvBar } from "../api/client";

type KlineChartProps = {
  data: OhlcvBar[];
  predSeries?: { open: number; high: number; low: number; close: number }[];
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
        volume: b.volume || 0,
      }));
      // lightweight-charts requires data to be strictly sorted by time ascending
      tvData.sort((a, b) => (a.time as number) - (b.time as number));
      candleSeries.setData(tvData);

      // Add Volume Series at the bottom
      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: {
          type: "volume",
        },
        priceScaleId: "", // Sets as an overlay without sharing main price scale
      });

      // Position the volume histogram at the bottom 25% of the screen
      chart.priceScale("").applyOptions({
        scaleMargins: {
          top: 0.75, // Leave top 75% for candles
          bottom: 0,
        },
      });

      const volumeData = tvData.map((d) => ({
        time: d.time,
        value: d.volume,
        color: d.close >= d.open ? "#10b98180" : "#f43f5e80", // 50% opacity emerald/rose
      }));
      volumeSeries.setData(volumeData);
    }

    // 3. Add AI Prediction Bars (T1-T4: high confidence, T5-T8: low confidence)
    if (!minimal && predSeries && predSeries.length > 0 && data && data.length > 0) {
      const lastCandle = data[data.length - 1];
      const lastUnix = parseToUnix(lastCandle.timestamps) as number;

      // 整体趋势决定预测区间的统一颜色，避免单根 bar 色系杂乱
      const finalBar = predSeries[predSeries.length - 1];
      const isUpward = finalBar.close >= lastCandle.close;
      const NEAR_COLOR = isUpward ? "#00f0ff" : "#f97316";                   // 近期实色
      const FAR_COLOR = isUpward ? "rgba(0, 240, 255, 0.30)" : "rgba(249, 115, 22, 0.30)";  // 远期淡色

      const nearBars = predSeries.slice(0, 4);  // T1-T4: 高置信度
      const farBars = predSeries.slice(4, 8);  // T5-T8: 中置信度

      // 将索引区间内的 bars 映射为 lightweight-charts OHLC 点
      const buildBarData = (bars: typeof predSeries, startUnix: number) => {
        let unix = startUnix;
        return bars.map((b) => {
          unix = addIntervalSeconds(unix, timeframe);
          return { time: unix as Time, open: b.open, high: b.high, low: b.low, close: b.close };
        });
      };

      // upColor 和 downColor 设为相同值，让每根 bar 无论自身涨跌都统一使用趋势色
      const addPredSeries = (bars: typeof predSeries, startUnix: number, color: string) => {
        const series = chart.addSeries(CandlestickSeries, {
          upColor: color,
          downColor: color,
          borderUpColor: color,
          borderDownColor: color,
          wickUpColor: color,
          wickDownColor: color,
          borderVisible: true,
        });
        const barData = buildBarData(bars, startUnix);
        if (barData.length > 0) series.setData(barData);
        return barData;
      };

      // 渲染近期预测（T1-T4）
      const nearData = addPredSeries(nearBars, lastUnix, NEAR_COLOR);
      // 渲染远期预测（T5-T8），起点从最后一根近期 bar 的时间戳开始
      const nearEndUnix = nearData.length > 0 ? (nearData[nearData.length - 1].time as number) : lastUnix;
      addPredSeries(farBars, nearEndUnix, FAR_COLOR);
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
