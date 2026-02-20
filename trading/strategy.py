"""
多时间框架融合交易策略模块

核心思路：将 5m/15m/1h 三个周期的 Kronos 预测结果
通过加权投票融合，提高信号可靠性，减少单周期噪声干扰。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class Signal:
    """交易信号数据类"""
    action: str          # 'BUY' | 'SELL' | 'HOLD'
    confidence: float    # 信心度 0.0 ~ 1.0
    change_pct: float    # 综合预测涨跌幅（百分比，如 0.02 = +2%）
    reasons: List[str] = field(default_factory=list)  # 信号来源说明

    def __str__(self):
        reasons_str = " | ".join(self.reasons)
        return f"[{self.action}] 信心度={self.confidence:.1%} 涨跌={self.change_pct:.2%} 原因: {reasons_str}"


class MultiTimeframeStrategy:
    """
    多时间框架信号融合策略

    对每个时间周期的 Kronos 预测，计算预测涨跌幅，
    然后按时框权重加权平均，得到综合信号。

    权重设计逻辑：
    - 1h 权重最高：中期趋势更稳定，噪声少
    - 15m 次之：兼顾趋势与短期动量
    - 5m 权重最低：噪声多，但提供短期入场时机
    """

    # 各时间周期对应的权重
    TIMEFRAME_WEIGHTS = {
        '5m':  0.2,
        '15m': 0.3,
        '1h':  0.5,
    }

    def __init__(
        self,
        threshold: float = 0.005,
        strong_threshold: float = 0.015,
    ):
        """
        Args:
            threshold: 产生信号的最低涨跌幅阈值（默认 0.5%）
            strong_threshold: 高信心信号阈值（默认 1.5%）
        """
        self.threshold = threshold
        self.strong_threshold = strong_threshold

    def generate_signal(
        self,
        predictions: Dict[str, Optional[float]],
        current_price: float,
    ) -> Signal:
        """
        根据多时框预测结果生成交易信号

        Args:
            predictions: 各时框的预测末价，格式: {'5m': price, '15m': price, '1h': price}
                         值可以为 None（该时框获取数据失败时）
            current_price: 当前实时价格

        Returns:
            Signal 对象
        """
        weighted_change = 0.0
        total_weight = 0.0
        reasons = []
        valid_count = 0

        for tf, pred_price in predictions.items():
            if pred_price is None:
                reasons.append(f"{tf}=N/A")
                continue

            weight = self.TIMEFRAME_WEIGHTS.get(tf, 0.0)
            change_pct = (pred_price - current_price) / current_price

            weighted_change += change_pct * weight
            total_weight += weight
            valid_count += 1

            direction = "↑" if change_pct > 0 else "↓"
            reasons.append(f"{tf}={direction}{change_pct:.2%}")

        # 如果所有时框都失败，返回 HOLD
        if total_weight == 0:
            return Signal(action='HOLD', confidence=0.0, change_pct=0.0,
                          reasons=['所有时框数据获取失败'])

        # 归一化加权涨跌幅（只用有效时框的权重）
        normalized_change = weighted_change / total_weight

        # 根据信号强度确定动作和信心度
        action, confidence = self._classify_signal(normalized_change, valid_count)

        return Signal(
            action=action,
            confidence=confidence,
            change_pct=normalized_change,
            reasons=reasons,
        )

    def _classify_signal(self, change_pct: float, valid_count: int) -> tuple:
        """
        将加权涨跌幅转化为具体动作和信心度

        信心度计算：
        - 在阈值和强阈值之间线性插值为 0.5~0.8
        - 超过强阈值为 0.8~1.0
        - 有效时框越多，信心度越高
        """
        abs_change = abs(change_pct)

        if abs_change < self.threshold:
            # 信号不足，持仓观望
            confidence = 1.0 - (abs_change / self.threshold) * 0.5  # 0.5~1.0 之间
            return 'HOLD', round(confidence * (valid_count / 3), 2)

        # 计算基础信心度（阈值~强阈值区间线性插值）
        if abs_change >= self.strong_threshold:
            base_confidence = 0.85
        else:
            ratio = (abs_change - self.threshold) / (self.strong_threshold - self.threshold)
            base_confidence = 0.5 + ratio * 0.35  # 0.5 ~ 0.85

        # 有效数据时框越多，信心度越高
        data_factor = valid_count / len(self.TIMEFRAME_WEIGHTS)
        confidence = round(base_confidence * data_factor, 2)

        action = 'BUY' if change_pct > 0 else 'SELL'
        return action, confidence

    def update_thresholds(self, threshold: float, strong_threshold: float):
        """动态更新阈值（供 Dashboard 调用）"""
        self.threshold = threshold
        self.strong_threshold = strong_threshold
