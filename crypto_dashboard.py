"""
Kronos Crypto Dashboard（升级版）

多页面 Streamlit 应用，包含：
1. 📊 实时监控  - K线 + 多时框预测 + 买卖信号 + 组合净值
2. 🔬 回测分析  - 历史回测 + 净值曲线 + 绩效指标表
3. ⚙️ 策略配置  - 动态调整策略和风险参数

运行方式：
    streamlit run crypto_dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os
import sys
import time
import json
import torch
from datetime import datetime, timedelta

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ────────────────────────────────────────────────────────
# 页面配置
# ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kronos Crypto Trading",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ────────────────────────────────────────────────────────
# 全局 CSS
# ────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 20px 24px;
        border-radius: 12px;
        margin-bottom: 24px;
    }
    .main-header h1 { color: #e94560; margin: 0; font-size: 1.8em; }
    .main-header p  { color: #a8b2d8; margin: 4px 0 0; font-size: 0.9em; }
    
    .signal-card {
        padding: 16px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid;
    }
    .signal-buy   { background: #0d2414; border-color: #00ff88; }
    .signal-sell  { background: #2e0d0d; border-color: #ff4757; }
    .signal-hold  { background: #1a1a2e; border-color: #ffa502; }
    
    .metric-card {
        background: #1a1a2e;
        border: 1px solid #2d3561;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .metric-label { color: #8892b0; font-size: 0.8em; text-transform: uppercase; }
    .metric-value { color: #e6f1ff; font-size: 1.4em; font-weight: 700; margin-top: 4px; }
    .metric-pos   { color: #00ff88; }
    .metric-neg   { color: #ff4757; }
    
    .section-title {
        color: #ccd6f6;
        font-size: 1.1em;
        font-weight: 600;
        padding-bottom: 6px;
        border-bottom: 1px solid #2d3561;
        margin-bottom: 16px;
    }
    
    div[data-testid="stMetric"] {
        background: #1a1a2e;
        border: 1px solid #2d3561;
        border-radius: 10px;
        padding: 12px 16px;
    }
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────
# 工具函数
# ────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def load_simulator():
    """加载模拟器（缓存，避免重启重新加载模型）"""
    from crypto_simulator import CryptoSimulator
    return CryptoSimulator()


def load_portfolio_state():
    """读取组合状态文件"""
    state_file = "portfolio_state.json"
    default = {'balance': 10000.0, 'positions': {}, 'last_update': '—'}
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                return json.load(f)
        except Exception:
            pass
    return default


def load_trade_log():
    """读取交易日志"""
    log_file = "simulation_log.csv"
    if os.path.exists(log_file):
        try:
            df = pd.read_csv(log_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=['timestamp', 'symbol', 'action', 'price',
                                  'amount', 'balance', 'portfolio_value', 'reason'])


def make_candle_chart(df: pd.DataFrame, pred_df=None, symbol="", timeframe="") -> go.Figure:
    """创建 K 线图 + 预测线"""
    # 转为上海时区显示
    display_df = df.copy()
    display_df['ts_local'] = pd.to_datetime(display_df['timestamps'])\
        .dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai')

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    # K 线
    fig.add_trace(go.Candlestick(
        x=display_df['ts_local'],
        open=display_df['open'],
        high=display_df['high'],
        low=display_df['low'],
        close=display_df['close'],
        name='OHLC',
        increasing_line_color='#00ff88',
        decreasing_line_color='#ff4757',
    ), row=1, col=1)

    # 成交量柱
    colors = ['#00ff88' if c >= o else '#ff4757'
              for c, o in zip(display_df['close'], display_df['open'])]
    fig.add_trace(go.Bar(
        x=display_df['ts_local'],
        y=display_df['volume'],
        name='成交量',
        marker_color=colors,
        opacity=0.6,
    ), row=2, col=1)

    # 预测曲线
    if pred_df is not None and len(pred_df) > 0:
        last_ts = display_df['ts_local'].iloc[-1]
        freq_map = {'5m': '5min', '15m': '15min', '1h': '1h', '4h': '4h', '1d': '1D'}
        freq = freq_map.get(timeframe, '1h')
        future_ts = pd.date_range(start=last_ts, periods=len(pred_df) + 1, freq=freq)[1:]

        # 平滑连接点：在历史最后一根 close 和预测之间加过渡
        pred_close = [float(display_df['close'].iloc[-1])] + pred_df['close'].tolist()
        ts_with_anchor = [last_ts] + list(future_ts)

        fig.add_trace(go.Scatter(
            x=ts_with_anchor,
            y=pred_close,
            mode='lines',
            line=dict(color='#f39c12', width=2, dash='dash'),
            name='Kronos 预测',
        ), row=1, col=1)

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0d1117',
        plot_bgcolor='#0d1117',
        height=580,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10),
        title=dict(text=f"{symbol} · {timeframe}", font=dict(color='#ccd6f6')),
    )
    fig.update_xaxes(gridcolor='#1e2a3a')
    fig.update_yaxes(gridcolor='#1e2a3a')
    return fig


# ────────────────────────────────────────────────────────
# 侧边栏
# ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🪐 Kronos Trading")
    page = st.radio(
        "导航",
        ["📊 实时监控", "🔬 回测分析", "⚙️ 策略配置"],
        label_visibility='collapsed',
    )
    st.divider()

    # 组合摘要（始终显示）
    state = load_portfolio_state()
    st.markdown("**💼 组合概览**")
    st.metric("可用余额", f"${state['balance']:,.2f}")
    st.caption(f"最后更新: {state.get('last_update', '—')[:19]}")


# ════════════════════════════════════════════════════════
# 页面 1：实时监控
# ════════════════════════════════════════════════════════
if page == "📊 实时监控":

    st.markdown("""
    <div class="main-header">
        <h1>📊 实时监控</h1>
        <p>Kronos 多时间框架预测 · 实时行情 · 信号生成</p>
    </div>
    """, unsafe_allow_html=True)

    # 控制栏
    col_sym, col_tf, col_btn = st.columns([2, 2, 1])
    with col_sym:
        symbol = st.selectbox("交易对", ['BTC/USDT', 'ETH/USDT'], key='sym')
    with col_tf:
        timeframe = st.selectbox("时间周期", ['5m', '15m', '1h'], key='tf')
    with col_btn:
        st.write("")
        run_btn = st.button("🔄 立即预测", use_container_width=True, type="primary")

    auto_refresh = st.checkbox("⏱ 自动刷新（60s）", value=False)

    # 加载模拟器并执行预测
    with st.spinner("加载 Kronos 模型中...（首次需要下载，约1~2分钟）"):
        try:
            sim = load_simulator()
            model_loaded = True
        except Exception as e:
            st.error(f"模型加载失败: {e}")
            model_loaded = False

    if model_loaded:
        with st.spinner(f"正在拉取 {symbol} {timeframe} 行情并预测..."):
            try:
                from crypto_simulator import LOOKBACK, PRED_LEN

                # 获取不同时框数据（并行展示）
                tf_data = sim.data_fetcher.fetch_multi_timeframe(symbol, ['5m', '15m', '1h'], LOOKBACK)
                main_df = tf_data.get(timeframe)

                if main_df is None:
                    st.error("数据获取失败，请检查网络连接")
                else:
                    current_price = float(main_df['close'].iloc[-1])

                    # 各时框预测
                    predictions = {}
                    pred_dfs = {}
                    for tf, df in tf_data.items():
                        if df is not None and len(df) >= LOOKBACK:
                            try:
                                p = sim.predict(df)
                                predictions[tf] = float(p['close'].iloc[-1])
                                pred_dfs[tf] = p
                            except Exception:
                                predictions[tf] = None
                        else:
                            predictions[tf] = None

                    # 生成信号
                    signal = sim.strategy.generate_signal(predictions, current_price)

                    # ── 顶部指标行 ─────────────────────────────
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("当前价格", f"${current_price:,.2f}")
                    with m2:
                        predicted = predictions.get(timeframe)
                        if predicted:
                            chg = (predicted - current_price) / current_price
                            st.metric("预测价格", f"${predicted:,.2f}",
                                      delta=f"{chg:+.2%}")
                    with m3:
                        signal_html = {
                            'BUY': '<div class="signal-card signal-buy"><div style="color:#00ff88;font-size:1.8em;font-weight:800">▲ BUY</div></div>',
                            'SELL': '<div class="signal-card signal-sell"><div style="color:#ff4757;font-size:1.8em;font-weight:800">▼ SELL</div></div>',
                            'HOLD': '<div class="signal-card signal-hold"><div style="color:#ffa502;font-size:1.8em;font-weight:800">◆ HOLD</div></div>',
                        }
                        st.markdown(signal_html.get(signal.action, ''), unsafe_allow_html=True)
                    with m4:
                        val = sim.portfolio.get_total_value({symbol: current_price})
                        initial = 10000.0
                        st.metric("组合总值", f"${val:,.2f}",
                                  delta=f"{(val-initial)/initial:+.2%}")

                    # ── K 线图 ──────────────────────────────────
                    pred_df_main = pred_dfs.get(timeframe)
                    fig = make_candle_chart(main_df, pred_df_main, symbol, timeframe)

                    # 叠加交易标记
                    log_df = load_trade_log()
                    if not log_df.empty:
                        sym_trades = log_df[log_df['symbol'] == symbol].copy()
                        sym_trades['ts_local'] = sym_trades['timestamp']\
                            .dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai')
                        min_ts = pd.to_datetime(main_df['timestamps'].min(),utc=True)\
                            .tz_convert('Asia/Shanghai')
                        sym_trades = sym_trades[sym_trades['ts_local'] >= min_ts]

                        buys = sym_trades[sym_trades['action'] == 'BUY']
                        sells = sym_trades[sym_trades['action'].isin(['SELL','STOP_LOSS','TAKE_PROFIT'])]

                        if not buys.empty:
                            fig.add_trace(go.Scatter(
                                x=buys['ts_local'], y=buys['price'],
                                mode='markers',
                                marker=dict(symbol='triangle-up', size=14, color='#00ff88'),
                                name='买入点',
                            ), row=1, col=1)
                        if not sells.empty:
                            fig.add_trace(go.Scatter(
                                x=sells['ts_local'], y=sells['price'],
                                mode='markers',
                                marker=dict(symbol='triangle-down', size=14, color='#ff4757'),
                                name='卖出点',
                            ), row=1, col=1)

                    st.plotly_chart(fig, use_container_width=True)

                    # ── 多时框信号详情 ────────────────────────
                    st.markdown('<div class="section-title">📡 多时间框架信号</div>', unsafe_allow_html=True)
                    tf_cols = st.columns(3)
                    for idx, tf in enumerate(['5m', '15m', '1h']):
                        with tf_cols[idx]:
                            pred_price = predictions.get(tf)
                            if pred_price is not None:
                                chg = (pred_price - current_price) / current_price
                                color = '#00ff88' if chg > 0 else '#ff4757'
                                st.markdown(f"""
                                <div class="metric-card">
                                    <div class="metric-label">{tf}</div>
                                    <div class="metric-value">${pred_price:,.2f}</div>
                                    <div style="color:{color};font-size:0.85em;margin-top:4px">{chg:+.2%}</div>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div class="metric-card">
                                    <div class="metric-label">{tf}</div>
                                    <div class="metric-value" style="color:#666">N/A</div>
                                </div>
                                """, unsafe_allow_html=True)

                    # ── 信号置信度条 ────────────────────────────
                    st.markdown(f"**信号置信度: {signal.confidence:.1%}**")
                    st.progress(signal.confidence)
                    st.caption(" · ".join(signal.reasons))

            except Exception as e:
                st.error(f"预测出错: {e}")
                import traceback; st.code(traceback.format_exc())

    # ── 近期交易记录 ───────────────────────────────────────
    st.markdown('<div class="section-title">📋 近期交易记录</div>', unsafe_allow_html=True)
    log_df = load_trade_log()
    if not log_df.empty:
        display_cols = ['timestamp', 'symbol', 'action', 'price', 'amount', 'portfolio_value', 'reason']
        available = [c for c in display_cols if c in log_df.columns]
        st.dataframe(log_df[available].tail(15).sort_index(ascending=False),
                     use_container_width=True, hide_index=True)
    else:
        st.info("暂无交易记录，等待模拟器运行...")

    if auto_refresh:
        time.sleep(60)
        st.rerun()


# ════════════════════════════════════════════════════════
# 页面 2：回测分析
# ════════════════════════════════════════════════════════
elif page == "🔬 回测分析":

    st.markdown("""
    <div class="main-header">
        <h1>🔬 回测分析</h1>
        <p>基于 Kronos 预测的历史策略回测 · 净值曲线 · 绩效评估</p>
    </div>
    """, unsafe_allow_html=True)

    # 参数配置
    with st.expander("⚙️ 回测参数配置", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            bt_symbol = st.selectbox("交易对", ['BTC/USDT', 'ETH/USDT'], key='bt_sym')
            bt_timeframe = st.selectbox("时间周期", ['1h', '4h', '15m'], key='bt_tf')
            bt_device = st.selectbox("计算设备", ['cpu', 'mps', 'cuda'], key='bt_dev')
        with c2:
            bt_start = st.date_input("开始日期", value=pd.Timestamp('2024-01-01'))
            bt_end = st.date_input("结束日期", value=pd.Timestamp('2024-06-01'))
            bt_capital = st.number_input("初始资金 (USDT)", value=10000.0, min_value=100.0, step=100.0)
        with c3:
            bt_lookback = st.slider("历史 K 线数 (lookback)", 100, 400, 200, 50)
            bt_pred_len = st.slider("预测 K 线数 (pred_len)", 6, 48, 12, 6)
            bt_step = st.slider("预测步长 (step)", 1, 24, 6, 1,
                               help="每隔多少根 K 线做一次预测，越小越精细但越慢")
            bt_threshold = st.slider("信号阈值 (%)", 0.1, 3.0, 0.5, 0.1) / 100

    run_backtest = st.button("🚀 开始回测", type="primary", use_container_width=True)

    if run_backtest:
        with st.spinner(f"回测中：{bt_symbol} {bt_timeframe} {bt_start}~{bt_end} ..."):
            try:
                from backtest import Backtester
                from backtest.metrics import format_metrics_table

                bt = Backtester(
                    symbol=bt_symbol,
                    timeframe=bt_timeframe,
                    start_date=str(bt_start),
                    end_date=str(bt_end),
                    initial_capital=bt_capital,
                    lookback=bt_lookback,
                    pred_len=bt_pred_len,
                    threshold=bt_threshold,
                    device=bt_device,
                    step_size=bt_step,
                )
                result = bt.run()
                st.session_state['backtest_result'] = result
                st.success(f"✅ 回测完成！共 {len(result.trades)} 笔交易")

            except Exception as e:
                st.error(f"回测出错: {e}")
                import traceback; st.code(traceback.format_exc())

    # 展示回测结果
    if 'backtest_result' in st.session_state:
        result = st.session_state['backtest_result']

        # 绩效指标卡片
        st.markdown('<div class="section-title">📊 绩效指标</div>', unsafe_allow_html=True)
        m = result.metrics
        cols = st.columns(5)
        metrics_display = [
            ("总收益率", f"{m['total_return']:+.2f}%", m['total_return'] > 0),
            ("年化收益率", f"{m['annual_return']:+.2f}%", m['annual_return'] > 0),
            ("夏普比率", f"{m['sharpe_ratio']:.3f}", m['sharpe_ratio'] > 1),
            ("最大回撤", f"{m['max_drawdown']:.2f}%", False),
            ("胜率", f"{m['win_rate']:.1f}%", m['win_rate'] > 50),
        ]
        for col, (label, value, positive) in zip(cols, metrics_display):
            color_class = 'metric-pos' if positive else 'metric-neg'
            col.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value {color_class}">{value}</div>
            </div>
            """, unsafe_allow_html=True)

        # 完整指标表
        with st.expander("查看完整指标"):
            from backtest.metrics import format_metrics_table
            st.dataframe(format_metrics_table(m), use_container_width=True, hide_index=True)

        # 净值曲线
        st.markdown('<div class="section-title">📈 净值曲线</div>', unsafe_allow_html=True)
        equity = result.equity_curve

        fig_eq = go.Figure()

        # 买入持有基准（BTC）
        if len(equity) > 1:
            bnh_values = result.initial_capital * (equity / equity.iloc[0])
            # 这里用实际净值曲线代表策略
            fig_eq.add_trace(go.Scatter(
                x=equity.index, y=equity.values,
                mode='lines', name='Kronos 策略净值',
                line=dict(color='#f39c12', width=2),
                fill='tozeroy', fillcolor='rgba(243,156,18,0.1)',
            ))

            # 添加初始资金参考线
            fig_eq.add_hline(
                y=result.initial_capital,
                line_dash='dash', line_color='#8892b0',
                annotation_text=f"初始资金 ${result.initial_capital:,.0f}",
            )

        fig_eq.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0d1117',
            plot_bgcolor='#0d1117',
            height=400,
            yaxis_title='净值 (USDT)',
            xaxis_title='日期',
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig_eq, use_container_width=True)

        # 交易记录表
        if result.trades:
            st.markdown('<div class="section-title">📋 交易明细</div>', unsafe_allow_html=True)
            trades_df = pd.DataFrame(result.trades)
            trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
            st.dataframe(trades_df, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════
# 页面 3：策略配置
# ════════════════════════════════════════════════════════
elif page == "⚙️ 策略配置":

    st.markdown("""
    <div class="main-header">
        <h1>⚙️ 策略配置</h1>
        <p>动态调整 Kronos 交易策略 · 风险管理 · 参数说明</p>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 🎯 信号策略参数")

        threshold = st.slider(
            "买卖信号阈值（%）",
            min_value=0.1, max_value=5.0, value=0.5, step=0.1,
            help="预测涨跌幅超过此阈值才产生 BUY/SELL 信号"
        )
        strong_threshold = st.slider(
            "强信号阈值（%）",
            min_value=0.5, max_value=10.0, value=1.5, step=0.5,
            help="超过此阈值的信号置信度更高（建议为普通阈值的3倍）"
        )

        st.divider()
        st.markdown("**多时框权重配置**")
        w_5m = st.slider("5m 权重", 0.0, 1.0, 0.2, 0.05)
        w_15m = st.slider("15m 权重", 0.0, 1.0, 0.3, 0.05)
        w_1h = st.slider("1h 权重", 0.0, 1.0, 0.5, 0.05)

        total_w = w_5m + w_15m + w_1h
        if abs(total_w - 1.0) > 0.05:
            st.warning(f"⚠️ 权重之和为 {total_w:.2f}，建议总和接近 1.0")

    with col_right:
        st.markdown("### 🛡️ 风险管理参数")

        buy_pct = st.slider(
            "单次买入比例（%）",
            min_value=1, max_value=50, value=15, step=1,
            help="每次买入信号触发时，使用总资产的比例"
        )
        max_exposure = st.slider(
            "最大仓位比例（%）",
            min_value=10, max_value=100, value=80, step=5,
            help="所有加密货币持仓合计不超过总资产的比例"
        )
        stop_loss = st.slider(
            "止损比例（%）",
            min_value=1, max_value=20, value=3, step=1,
            help="持仓浮亏超过此比例时强制平仓"
        )
        take_profit = st.slider(
            "止盈比例（%）",
            min_value=2, max_value=50, value=8, step=1,
            help="持仓浮盈超过此比例时卖出一半"
        )
        min_confidence = st.slider(
            "最小信号置信度",
            min_value=0.1, max_value=0.9, value=0.45, step=0.05,
            help="低于此置信度的信号不执行"
        )

    st.divider()

    if st.button("💾 应用配置", type="primary"):
        # 保存到 session state，供下次预测使用
        st.session_state['strategy_config'] = {
            'threshold': threshold / 100,
            'strong_threshold': strong_threshold / 100,
            'weights': {'5m': w_5m, '15m': w_15m, '1h': w_1h},
            'buy_pct': buy_pct / 100,
            'max_exposure': max_exposure / 100,
            'stop_loss': stop_loss / 100,
            'take_profit': take_profit / 100,
            'min_confidence': min_confidence,
        }
        with open("strategy_config.json", 'w') as f:
            json.dump(st.session_state['strategy_config'], f, indent=2)
        st.success("✅ 配置已保存！下次预测时自动生效。")

    # 参数说明
    st.markdown("---")
    st.markdown("### 📖 参数说明")
    st.markdown("""
    | 参数 | 含义 | 建议范围 |
    |------|------|---------|
    | **信号阈值** | Kronos 预测的最低涨跌幅，才触发买卖 | 0.3%~1% |
    | **强信号阈值** | 高置信度信号要求的涨跌幅 | 阈值的 2-4 倍 |
    | **单次买入比例** | 控制每次买入不超过总资产多少 | 10%~20% |
    | **最大仓位** | 防止满仓一种资产 | 60%~80% |
    | **止损** | 亏损多少强制割肉 | 2%~5% |
    | **止盈** | 盈利多少卖出一半锁定利润 | 5%~15% |

    > **💡 提示**：加密货币波动大，建议止损设 2-3%，止盈设 6-10%。
    > 信号阈值过小会产生过多噪音交易，过大则错过机会。
    """)

    # 当前持仓详情
    st.markdown("### 💼 当前持仓明细")
    state = load_portfolio_state()
    positions = state.get('positions', {})

    if any(v > 1e-8 for v in positions.values()):
        try:
            # 拉取实时价格显示持仓
            sim = load_simulator()
            cur_prices = {}
            for sym in positions:
                if positions[sym] > 1e-8:
                    try:
                        cur_prices[sym] = sim.data_fetcher.get_current_price(sym)
                    except Exception:
                        cur_prices[sym] = 0.0

            pos_summary = sim.risk_manager.get_position_summary(cur_prices)
            if pos_summary:
                pos_df = pd.DataFrame(pos_summary)
                pos_df['pnl_pct'] = pos_df['pnl_pct'].apply(lambda x: f"{x:+.2%}")
                pos_df['pnl_usdt'] = pos_df['pnl_usdt'].apply(lambda x: f"${x:+.2f}")
                st.dataframe(pos_df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"加载持仓详情需要初始化模拟器: {e}")
    else:
        st.info("当前暂无持仓")
