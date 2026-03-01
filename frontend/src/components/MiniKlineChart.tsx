import { useMemo } from "react";
import Plot from "react-plotly.js";
import type { OhlcvBar } from "../api/client";

type PredBar = { open: number; high: number; low: number; close: number };

type MiniKlineChartProps = {
    data: OhlcvBar[];
    predSeries?: PredBar[];
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

    // 将预测 bars 分为近期(T1-T4)和远期(T5-T8)两组
    const predTraces = useMemo(() => {
        if (!predSeries?.length || !data?.length) return [];
        const lastTsStr = data[data.length - 1].timestamps;
        const lastClose = data[data.length - 1].close;

        // 整体趋势决定统一颜色，让预测区域色系纯净
        const finalBar = predSeries[predSeries.length - 1];
        const isUpward = finalBar.close >= lastClose;
        const NEAR_COLOR = isUpward ? "#00f0ff" : "#f97316";
        const FAR_COLOR = isUpward ? "rgba(0,240,255,0.30)" : "rgba(249,115,22,0.30)";

        let lastMs = parseToMs(lastTsStr);

        const buildGroup = (bars: PredBar[]) => {
            const xMs: number[] = [];
            const pOpen: number[] = [];
            const pHigh: number[] = [];
            const pLow: number[] = [];
            const pClose: number[] = [];

            bars.forEach((b) => {
                lastMs = addIntervalMs(lastMs, timeframe);
                xMs.push(lastMs);
                pOpen.push(b.open);
                pHigh.push(b.high);   // 已由后端收口，无上影线
                pLow.push(b.low);    // 已由后端收口，无下影线
                pClose.push(b.close);
            });
            return { x: xMs, open: pOpen, high: pHigh, low: pLow, close: pClose };
        };

        const nearGroup = buildGroup(predSeries.slice(0, 4));
        const farGroup = buildGroup(predSeries.slice(4, 8));

        // increasing 和 decreasing 都设为同一颜色，不按单根涨跌着色
        const makeTrace = (group: ReturnType<typeof buildGroup>, color: string, suffix: string) => ({
            ...group,
            type: "candlestick",
            name: `AI预测_${suffix}`,
            increasing: { line: { color, width: 1 }, fillcolor: color },
            decreasing: { line: { color, width: 1 }, fillcolor: color },
        });

        return [
            makeTrace(nearGroup, NEAR_COLOR, "near"),
            makeTrace(farGroup, FAR_COLOR, "far"),
        ];
    }, [predSeries, data, timeframe]);

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
    // 追加两组预测 bars
    predTraces.forEach(t => traces.push(t));

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
