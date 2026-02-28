import { useMemo } from "react";
import Plot from "react-plotly.js";
import type { OhlcvBar } from "../api/client";

type MiniKlineChartProps = {
    data: OhlcvBar[];
    predSeries?: number[];
    symbol: string;
    timeframe: string;
};

// 将时间字符串转为毫秒时间戳，与 K 线 x 轴一致
function parseToMs(ts: string): number {
    const d = new Date(ts.replace(" ", "T") + "Z");
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

export default function MiniKlineChart({ data, predSeries, symbol, timeframe }: MiniKlineChartProps) {
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

    const predCandleTrace = useMemo(() => {
        if (!predSeries?.length || !data?.length) return null;
        const lastTsStr = data[data.length - 1].timestamps;
        const lastClose = close.length ? close[close.length - 1] : 0;

        // 使用与 K 线一致的 x 轴：统一为时间戳（毫秒）
        let lastMs = parseToMs(lastTsStr);
        const predXMs: number[] = [];

        const pOpen: number[] = [];
        const pHigh: number[] = [];
        const pLow: number[] = [];
        const pClose: number[] = [];

        let prevClose = lastClose;

        for (let i = 0; i < predSeries.length; i++) {
            lastMs = addIntervalMs(lastMs, timeframe);
            predXMs.push(lastMs);

            const currPred = predSeries[i];
            pOpen.push(prevClose);
            pClose.push(currPred);
            pHigh.push(Math.max(prevClose, currPred));
            pLow.push(Math.min(prevClose, currPred));

            prevClose = currPred;
        }

        return {
            x: predXMs,
            open: pOpen,
            high: pHigh,
            low: pLow,
            close: pClose,
            type: "candlestick",
            name: "AI 预测",
            increasing: { line: { color: "rgba(52, 211, 153, 0.5)", width: 2 }, fillcolor: "rgba(52, 211, 153, 0.3)" },
            decreasing: { line: { color: "rgba(251, 113, 133, 0.5)", width: 2 }, fillcolor: "rgba(251, 113, 133, 0.3)" },
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
    if (predCandleTrace) traces.push(predCandleTrace);

    return (
        <Plot
            data={traces}
            layout={{
                template: "plotly_dark",
                paper_bgcolor: "rgba(0,0,0,0)",
                plot_bgcolor: "rgba(0,0,0,0)",
                dragmode: false,
                xaxis: {
                    type: "date",
                    rangeslider: { visible: false },
                    visible: false,
                    fixedrange: true,
                },
                yaxis: {
                    visible: false,
                    fixedrange: true,
                },
                margin: { t: 5, b: 5, l: 5, r: 5 },
                showlegend: false,
            }}
            config={{ displayModeBar: false, responsive: true, staticPlot: true }}
            style={{ width: "100%", height: "100%" }}
        />
    );
}
