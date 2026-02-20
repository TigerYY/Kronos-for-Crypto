"""
历史数据回测引擎

在历史 K 线数据上模拟完整的 Kronos 预测 → 信号生成 → 执行交易流程，
输出净值曲线和详细交易记录，用于评估策略有效性。
"""

import sys
import os
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from tqdm import tqdm

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import Kronos, KronosTokenizer, KronosPredictor
from trading.strategy import MultiTimeframeStrategy
from trading.risk_manager import RiskManager
from trading.data_fetcher import DataFetcher
from backtest.metrics import calc_metrics, format_metrics_table


@dataclass
class BacktestResult:
    """回测结果容器"""
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float
    equity_curve: pd.Series                # 净值曲线（以时间戳为索引）
    trades: List[Dict[str, Any]]           # 交易记录
    metrics: Dict[str, Any]               # 绩效指标
    signals: List[Dict[str, Any]] = field(default_factory=list)  # 信号记录

    def print_summary(self):
        """在控制台打印摘要"""
        print(f"\n{'='*50}")
        print(f"回测结果: {self.symbol} {self.timeframe}")
        print(f"区间: {self.start_date} ~ {self.end_date}")
        print(f"{'='*50}")
        for k, v in self.metrics.items():
            print(f"  {k:<20}: {v}")
        print(f"{'='*50}\n")


class Backtester:
    """
    Kronos 策略回测引擎

    工作流程：
    1. 从本地缓存或 Binance 拉取历史 OHLCV 数据
    2. 以滑动窗口方式遍历历史数据
    3. 每步调用 KronosPredictor 生成预测
    4. 通过 MultiTimeframeStrategy 确定买卖信号
    5. 通过 RiskManager 过滤信号后执行交易
    6. 记录净值和交易，最终计算绩效指标

    注意：单时间框架回测，不做多时框融合（历史数据拉取多时框成本过高）
    """

    def __init__(
        self,
        symbol: str = 'BTC/USDT',
        timeframe: str = '1h',
        start_date: str = '2024-01-01',
        end_date: str = '2024-06-01',
        initial_capital: float = 10000.0,
        lookback: int = 400,
        pred_len: int = 24,
        buy_pct: float = 0.15,
        threshold: float = 0.005,
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.08,
        model_name: str = 'NeoQuasar/Kronos-small',
        tokenizer_name: str = 'NeoQuasar/Kronos-Tokenizer-base',
        device: str = 'cpu',
        step_size: int = 6,  # 每隔多少根 K 线做一次预测（节省时间）
    ):
        """
        Args:
            symbol:          交易对
            timeframe:       时间周期
            start_date:      回测开始日期
            end_date:        回测结束日期
            initial_capital: 初始资金（USDT）
            lookback:        Kronos 输入历史 K 线数
            pred_len:        预测未来 K 线数
            buy_pct:         每次买入占总资产比例
            threshold:       触发买卖信号的涨跌幅阈值
            stop_loss_pct:   止损比例
            take_profit_pct: 止盈比例
            model_name:      Kronos 模型 HuggingFace ID
            tokenizer_name:  Kronos Tokenizer HuggingFace ID
            device:          计算设备 ('cpu', 'cuda', 'mps')
            step_size:       预测步长（每隔 N 根 K 线预测一次）
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.lookback = lookback
        self.pred_len = pred_len
        self.buy_pct = buy_pct
        self.step_size = step_size

        # 初始化组件
        self.data_fetcher = DataFetcher()
        self.strategy = MultiTimeframeStrategy(
            threshold=threshold,
            strong_threshold=threshold * 3,
        )
        self.risk_manager = RiskManager(
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            state_file=f"backtest_risk_state_{symbol.replace('/', '_')}.json",
        )

        # 加载 Kronos 模型
        print(f"[Backtester] 加载模型 {model_name} ...")
        import torch
        if device == 'auto':
            if torch.cuda.is_available():
                device = 'cuda'
            elif torch.backends.mps.is_available():
                device = 'mps'
            else:
                device = 'cpu'
        self.device = device

        self.tokenizer = KronosTokenizer.from_pretrained(tokenizer_name)
        self.model = Kronos.from_pretrained(model_name)
        self.predictor = KronosPredictor(
            self.model, self.tokenizer,
            device=self.device,
            max_context=self.lookback,
        )
        print(f"[Backtester] 模型加载完成，使用设备: {self.device}")

    def run(self) -> BacktestResult:
        """
        执行回测

        Returns:
            BacktestResult 对象
        """
        # ── 1. 获取历史数据 ────────────────────────────────────
        print(f"[Backtester] 获取历史数据: {self.symbol} {self.timeframe}")
        df = self.data_fetcher.fetch_historical(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
        )

        if len(df) < self.lookback + self.pred_len:
            raise ValueError(
                f"历史数据不足 {len(df)} 条，"
                f"至少需要 {self.lookback + self.pred_len} 条"
            )

        print(f"[Backtester] 获取到 {len(df)} 条数据，开始回测...")

        # ── 2. 初始化回测状态 ──────────────────────────────────
        balance = self.initial_capital
        holdings = {self.symbol: 0.0}          # 持有量（单位：币）
        equity_records = {}                     # 时间戳 → 净值
        trades = []
        signals = []

        # ── 3. 滑动窗口遍历 ────────────────────────────────────
        start_idx = self.lookback
        end_idx = len(df) - self.pred_len

        bar = tqdm(
            range(start_idx, end_idx, self.step_size),
            desc=f"回测中 {self.symbol}",
            unit="steps",
        )

        for i in bar:
            # 取当前时刻之前的 lookback 根 K 线
            window = df.iloc[i - self.lookback: i].copy()
            current_price = float(df['close'].iloc[i])
            current_ts = df['timestamps'].iloc[i]

            # 计算当前净值并记录
            total_value = balance + holdings[self.symbol] * current_price
            equity_records[current_ts] = total_value

            # 止盈止损检查（优先于信号）
            sl_tp = self.risk_manager.check_stop_loss_take_profit(self.symbol, current_price)
            if sl_tp == 'STOP_LOSS' and holdings[self.symbol] > 0:
                # 全部平仓止损
                sell_amount = holdings[self.symbol]
                recv_usdt = sell_amount * current_price
                balance += recv_usdt
                pnl_pct = self.risk_manager.get_unrealized_pnl_pct(self.symbol, current_price)
                self.risk_manager.record_sell(self.symbol, sell_amount)
                holdings[self.symbol] = 0.0
                trades.append({
                    'timestamp': current_ts,
                    'action': 'STOP_LOSS',
                    'price': current_price,
                    'amount': sell_amount,
                    'balance': balance,
                    'pnl_pct': pnl_pct,
                })
                bar.set_postfix({'Action': 'STOP_LOSS', 'Price': f'{current_price:.2f}'})
                continue

            elif sl_tp == 'TAKE_PROFIT' and holdings[self.symbol] > 0:
                # 卖出一半止盈
                sell_amount = holdings[self.symbol] * 0.5
                recv_usdt = sell_amount * current_price
                balance += recv_usdt
                pnl_pct = self.risk_manager.get_unrealized_pnl_pct(self.symbol, current_price)
                self.risk_manager.record_sell(self.symbol, sell_amount)
                holdings[self.symbol] -= sell_amount
                trades.append({
                    'timestamp': current_ts,
                    'action': 'TAKE_PROFIT',
                    'price': current_price,
                    'amount': sell_amount,
                    'balance': balance,
                    'pnl_pct': pnl_pct,
                })
                bar.set_postfix({'Action': 'TAKE_PROFIT', 'Price': f'{current_price:.2f}'})
                continue

            # ── Kronos 预测 ─────────────────────────────────
            try:
                x_df = window[['open', 'high', 'low', 'close', 'volume', 'amount']]
                x_ts = window['timestamps'].reset_index(drop=True)
                diff = x_ts.iloc[-1] - x_ts.iloc[-2]
                y_ts = pd.Series([x_ts.iloc[-1] + diff * (k + 1) for k in range(self.pred_len)])

                pred_df = self.predictor.predict(
                    df=x_df,
                    x_timestamp=x_ts,
                    y_timestamp=y_ts,
                    pred_len=self.pred_len,
                    T=0.8,
                    top_p=0.9,
                    sample_count=1,
                    verbose=False,
                )
                pred_price = float(pred_df['close'].iloc[-1])
            except Exception as e:
                # 预测失败，跳过本步
                continue

            # ── 生成信号 ────────────────────────────────────
            signal = self.strategy.generate_signal(
                predictions={self.timeframe: pred_price},
                current_price=current_price,
            )
            signals.append({
                'timestamp': current_ts,
                'action': signal.action,
                'confidence': signal.confidence,
                'change_pct': signal.change_pct,
            })

            # ── 执行交易 ────────────────────────────────────
            if signal.action == 'BUY' and signal.confidence > 0.4:
                # 买入检查
                want_usdt = balance * self.buy_pct
                allowed, reason, adj_usdt = self.risk_manager.check_buy(
                    symbol=self.symbol,
                    amount_usdt=want_usdt,
                    total_portfolio_value=total_value,
                    current_prices={self.symbol: current_price},
                    crypto_holdings=holdings,
                )
                if allowed and adj_usdt >= 10:
                    buy_amount = adj_usdt / current_price
                    balance -= adj_usdt
                    holdings[self.symbol] += buy_amount
                    self.risk_manager.record_buy(self.symbol, current_price, buy_amount)
                    trades.append({
                        'timestamp': current_ts,
                        'action': 'BUY',
                        'price': current_price,
                        'amount': buy_amount,
                        'balance': balance,
                        'pnl_pct': None,
                    })
                    bar.set_postfix({'Action': 'BUY', 'Price': f'{current_price:.2f}'})

            elif signal.action == 'SELL' and holdings[self.symbol] > 0 and signal.confidence > 0.4:
                # 全部卖出
                sell_amount = holdings[self.symbol]
                recv_usdt = sell_amount * current_price
                balance += recv_usdt
                pnl_pct = self.risk_manager.get_unrealized_pnl_pct(self.symbol, current_price)
                self.risk_manager.record_sell(self.symbol, sell_amount)
                holdings[self.symbol] = 0.0
                trades.append({
                    'timestamp': current_ts,
                    'action': 'SELL',
                    'price': current_price,
                    'amount': sell_amount,
                    'balance': balance,
                    'pnl_pct': pnl_pct,
                })
                bar.set_postfix({'Action': 'SELL', 'Price': f'{current_price:.2f}'})

        # ── 4. 计算最终净值 ────────────────────────────────────
        final_price = float(df['close'].iloc[-1])
        final_value = balance + holdings[self.symbol] * final_price
        equity_records[df['timestamps'].iloc[-1]] = final_value

        equity_curve = pd.Series(equity_records).sort_index()
        metrics = calc_metrics(equity_curve, trades, self.initial_capital)

        result = BacktestResult(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_capital=self.initial_capital,
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            signals=signals,
        )
        result.print_summary()
        return result
