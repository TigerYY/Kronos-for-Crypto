"""
风险管理模块

负责仓位控制、止盈止损，确保在极端行情下不会被爆仓。
设计原则：宁可少赚，不可大亏。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import json
import os


@dataclass
class PositionRecord:
    """持仓记录，用于止盈止损计算"""
    symbol: str
    entry_price: float       # 开仓均价
    amount: float            # 持有数量（单位：币）
    entry_value_usdt: float  # 开仓时 USDT 价值


class RiskManager:
    """
    仓位与风险管理器

    核心规则：
    1. 单次买入上限：总资产的 max_position_pct（默认 20%）
    2. 止损：持仓浮亏超过 stop_loss_pct（默认 3%）则强制卖出
    3. 止盈：持仓浮盈超过 take_profit_pct（默认 8%）则卖出一半
    4. 最大仓位：所有币种合计不超过总资产的 max_total_exposure（默认 80%）
    5. 最小交易量：单次交易至少 10 USDT
    """

    def __init__(
        self,
        max_position_pct: float = 0.20,
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.08,
        max_total_exposure: float = 0.80,
        min_trade_usdt: float = 10.0,
        state_file: Optional[str] = "risk_state.json",
    ):
        self.max_position_pct = max_position_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_total_exposure = max_total_exposure
        self.min_trade_usdt = min_trade_usdt
        self.state_file = state_file

        # key: symbol, value: PositionRecord
        self.positions: Dict[str, PositionRecord] = {}
        self._load_state()

    # ------------------------------------------------------------------ #
    # 买入检查
    # ------------------------------------------------------------------ #

    def check_buy(
        self,
        symbol: str,
        amount_usdt: float,
        total_portfolio_value: float,
        current_prices: Dict[str, float],
        crypto_holdings: Dict[str, float],
    ) -> Tuple[bool, str, float]:
        """
        检查是否允许执行买入

        Returns:
            (allowed, reason, adjusted_amount_usdt)
            - allowed: 是否允许
            - reason: 不允许的原因 / 允许的说明
            - adjusted_amount_usdt: 调整后的买入金额（可能小于请求值）
        """
        if amount_usdt < self.min_trade_usdt:
            return False, f"交易金额 {amount_usdt:.2f} USDT 低于最小限额 {self.min_trade_usdt} USDT", 0.0

        # 检查总仓位比例上限
        total_crypto_value = sum(
            crypto_holdings.get(sym, 0.0) * price
            for sym, price in current_prices.items()
        )
        exposure = total_crypto_value / total_portfolio_value if total_portfolio_value > 0 else 0.0

        if exposure >= self.max_total_exposure:
            return False, (
                f"总仓位比例 {exposure:.1%} 已超过上限 {self.max_total_exposure:.1%}，"
                "需先平仓再买入"
            ), 0.0

        # 限制单次买入不超过总资产的 max_position_pct
        max_allowed = total_portfolio_value * self.max_position_pct

        # 同时不超过剩余可用空间（避免总仓位超标）
        remaining_room = (self.max_total_exposure - exposure) * total_portfolio_value
        max_allowed = min(max_allowed, remaining_room)

        if max_allowed < self.min_trade_usdt:
            return False, f"剩余可用仓位空间 {max_allowed:.2f} USDT 不足", 0.0

        adjusted = min(amount_usdt, max_allowed)
        if adjusted < amount_usdt:
            reason = f"买入金额从 {amount_usdt:.2f} 调整为 {adjusted:.2f} USDT（仓位上限）"
        else:
            reason = f"允许买入 {adjusted:.2f} USDT"

        return True, reason, adjusted

    # ------------------------------------------------------------------ #
    # 止盈止损检查
    # ------------------------------------------------------------------ #

    def check_stop_loss_take_profit(
        self,
        symbol: str,
        current_price: float,
    ) -> Optional[str]:
        """
        检查止盈止损条件

        Returns:
            'STOP_LOSS' | 'TAKE_PROFIT' | None
        """
        record = self.positions.get(symbol)
        if record is None or record.amount <= 0:
            return None

        change_pct = (current_price - record.entry_price) / record.entry_price

        if change_pct <= -self.stop_loss_pct:
            return 'STOP_LOSS'

        if change_pct >= self.take_profit_pct:
            return 'TAKE_PROFIT'

        return None

    def get_unrealized_pnl(self, symbol: str, current_price: float) -> float:
        """获取当前未实现盈亏（USDT）"""
        record = self.positions.get(symbol)
        if record is None or record.amount <= 0:
            return 0.0
        return (current_price - record.entry_price) * record.amount

    def get_unrealized_pnl_pct(self, symbol: str, current_price: float) -> float:
        """获取当前未实现盈亏百分比"""
        record = self.positions.get(symbol)
        if record is None or record.amount <= 0 or record.entry_price <= 0:
            return 0.0
        return (current_price - record.entry_price) / record.entry_price

    # ------------------------------------------------------------------ #
    # 持仓记录更新
    # ------------------------------------------------------------------ #

    def record_buy(self, symbol: str, price: float, amount_crypto: float):
        """记录买入，更新持仓均价"""
        if symbol in self.positions and self.positions[symbol].amount > 0:
            # 已有持仓，计算新均价（加权平均）
            old = self.positions[symbol]
            total_amount = old.amount + amount_crypto
            total_cost = old.entry_price * old.amount + price * amount_crypto
            new_avg_price = total_cost / total_amount
            self.positions[symbol] = PositionRecord(
                symbol=symbol,
                entry_price=new_avg_price,
                amount=total_amount,
                entry_value_usdt=total_cost,
            )
        else:
            self.positions[symbol] = PositionRecord(
                symbol=symbol,
                entry_price=price,
                amount=amount_crypto,
                entry_value_usdt=price * amount_crypto,
            )
        self._save_state()

    def record_sell(self, symbol: str, amount_crypto: float):
        """记录卖出，更新或清除持仓"""
        if symbol not in self.positions:
            return
        record = self.positions[symbol]
        record.amount -= amount_crypto
        if record.amount <= 1e-8:  # 浮点数精度容忍
            record.amount = 0.0
        self._save_state()

    # ------------------------------------------------------------------ #
    # 状态持久化
    # ------------------------------------------------------------------ #

    def _save_state(self):
        """将持仓记录保存到 JSON 文件"""
        if not self.state_file:
            return
            
        data = {
            sym: {
                'entry_price': rec.entry_price,
                'amount': rec.amount,
                'entry_value_usdt': rec.entry_value_usdt,
            }
            for sym, rec in self.positions.items()
        }
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_state(self):
        """从 JSON 文件恢复持仓记录"""
        if not self.state_file or not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            for sym, rec in data.items():
                self.positions[sym] = PositionRecord(
                    symbol=sym,
                    entry_price=rec.get('entry_price', 0.0),
                    amount=rec.get('amount', 0.0),
                    entry_value_usdt=rec.get('entry_value_usdt', 0.0),
                )
        except Exception as e:
            print(f"[RiskManager] 加载持仓状态失败: {e}")

    def get_position_summary(self, current_prices: Dict[str, float]) -> list:
        """返回持仓摘要（用于 Dashboard 展示）"""
        summary = []
        for sym, rec in self.positions.items():
            if rec.amount <= 1e-8:
                continue
            current = current_prices.get(sym, rec.entry_price)
            pnl_pct = (current - rec.entry_price) / rec.entry_price
            summary.append({
                'symbol': sym,
                'amount': rec.amount,
                'entry_price': rec.entry_price,
                'current_price': current,
                'pnl_pct': pnl_pct,
                'pnl_usdt': (current - rec.entry_price) * rec.amount,
            })
        return summary

    def update_params(
        self,
        max_position_pct: float = None,
        stop_loss_pct: float = None,
        take_profit_pct: float = None,
    ):
        """动态更新风险参数（供 Dashboard 调用）"""
        if max_position_pct is not None:
            self.max_position_pct = max_position_pct
        if stop_loss_pct is not None:
            self.stop_loss_pct = stop_loss_pct
        if take_profit_pct is not None:
            self.take_profit_pct = take_profit_pct
