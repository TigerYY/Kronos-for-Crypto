"""
绩效指标计算模块

提供量化交易中常用的策略评估指标：
- 总收益率 / 年化收益率
- 夏普比率（Sharpe Ratio）
- 最大回撤（Maximum Drawdown）
- 胜率（Win Rate）
- 盈亏比（Profit/Loss Ratio）
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any


def calc_metrics(
    equity_curve: pd.Series,
    trades: List[Dict[str, Any]],
    initial_capital: float,
    risk_free_rate: float = 0.03,
) -> Dict[str, Any]:
    """
    计算完整的策略绩效指标

    Args:
        equity_curve:    按时间排序的组合净值序列（USDT）
        trades:          交易记录列表，每条包含 {action, price, amount, timestamp}
        initial_capital: 初始资金（USDT）
        risk_free_rate:  年化无风险利率（默认 3%，用于夏普比率分母计算）

    Returns:
        包含所有绩效指标的字典
    """
    if equity_curve.empty or len(equity_curve) < 2:
        return _empty_metrics()

    final_value = equity_curve.iloc[-1]

    # ── 收益率 ──────────────────────────────────────────────
    total_return = (final_value - initial_capital) / initial_capital
    n_days = max((equity_curve.index[-1] - equity_curve.index[0]).days, 1)
    annual_return = (1 + total_return) ** (365 / n_days) - 1

    # ── 日收益率（用于夏普）──────────────────────────────────
    daily_returns = equity_curve.resample('D').last().pct_change().dropna()
    daily_rf = risk_free_rate / 365

    if len(daily_returns) > 1 and daily_returns.std() > 0:
        sharpe = (daily_returns.mean() - daily_rf) / daily_returns.std() * np.sqrt(365)
    else:
        sharpe = 0.0

    # ── 最大回撤 ─────────────────────────────────────────────
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_drawdown = drawdown.min()  # 负值，如 -0.12 表示最大回撤 12%

    # 回撤期间（从峰值到谷底的天数）
    drawdown_start = drawdown.idxmin()
    peak_before = equity_curve[:drawdown_start].idxmax() if not equity_curve[:drawdown_start].empty else drawdown_start
    drawdown_days = max((drawdown_start - peak_before).days, 0)

    # ── 交易统计 ─────────────────────────────────────────────
    buy_trades = [t for t in trades if t.get('action') == 'BUY']
    sell_trades = [t for t in trades if t.get('action') in ('SELL', 'STOP_LOSS', 'TAKE_PROFIT')]

    total_trades = len(buy_trades) + len(sell_trades)

    # 计算胜率（卖出时收益为正的比例）
    wins = 0
    losses = 0
    profits = []
    for trade in trades:
        pnl = trade.get('pnl_pct', None)
        if pnl is not None:
            if pnl > 0:
                wins += 1
                profits.append(pnl)
            elif pnl < 0:
                losses += 1
                profits.append(pnl)

    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0.0

    # 盈亏比：平均盈利 / 平均亏损
    winning_profits = [p for p in profits if p > 0]
    losing_profits = [abs(p) for p in profits if p < 0]
    avg_win = np.mean(winning_profits) if winning_profits else 0.0
    avg_loss = np.mean(losing_profits) if losing_profits else 0.0
    profit_factor = avg_win / avg_loss if avg_loss > 0 else (999.99 if avg_win > 0 else 0.0)

    return {
        'total_return':    round(total_return * 100, 2),       # %
        'annual_return':   round(annual_return * 100, 2),      # %
        'sharpe_ratio':    round(sharpe, 3),
        'max_drawdown':    round(max_drawdown * 100, 2),       # % （负值）
        'drawdown_days':   drawdown_days,
        'total_trades':    total_trades,
        'buy_trades':      len(buy_trades),
        'sell_trades':     len(sell_trades),
        'win_rate':        round(win_rate * 100, 2),           # %
        'profit_factor':   round(profit_factor, 2),
        'final_value':     round(final_value, 2),
        'initial_capital': round(initial_capital, 2),
        'n_days':          n_days,
    }


def _empty_metrics() -> Dict[str, Any]:
    """返回空指标（数据不足时）"""
    return {
        'total_return': 0.0,
        'annual_return': 0.0,
        'sharpe_ratio': 0.0,
        'max_drawdown': 0.0,
        'drawdown_days': 0,
        'total_trades': 0,
        'buy_trades': 0,
        'sell_trades': 0,
        'win_rate': 0.0,
        'profit_factor': 0.0,
        'final_value': 0.0,
        'initial_capital': 0.0,
        'n_days': 0,
    }


def format_metrics_table(metrics: Dict[str, Any]) -> pd.DataFrame:
    """将指标字典格式化为易读的 DataFrame（用于 Dashboard）"""
    rows = [
        ('💰 初始资金',     f"${metrics['initial_capital']:,.2f}"),
        ('💵 最终净值',     f"${metrics['final_value']:,.2f}"),
        ('📈 总收益率',     f"{metrics['total_return']:+.2f}%"),
        ('📅 年化收益率',   f"{metrics['annual_return']:+.2f}%"),
        ('⚡ 夏普比率',     f"{metrics['sharpe_ratio']:.3f}"),
        ('📉 最大回撤',     f"{metrics['max_drawdown']:.2f}%"),
        ('📆 回撤持续天数', f"{metrics['drawdown_days']} 天"),
        ('🔄 总交易次数',   f"{metrics['total_trades']} 次"),
        ('🎯 胜率',         f"{metrics['win_rate']:.1f}%"),
        ('⚖️ 盈亏比',       f"{metrics['profit_factor']:.2f}x"),
        ('📊 回测天数',     f"{metrics['n_days']} 天"),
    ]
    return pd.DataFrame(rows, columns=['指标', '数值'])
