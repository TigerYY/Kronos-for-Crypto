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
    # 设计逻辑：1d/4h 中长期趋势权重最高，15m 短期噪音最大权重最低
    TIMEFRAME_WEIGHTS = {
        '15m': 0.15,
        '1h':  0.25,
        '4h':  0.30,
        '1d':  0.30,
    }

    # 预测长度固定为 12 根 K 线。为了解决不同时间框架的“尺度错位 (Scale Mismatch)”问题，
    # 我们将所有时框的预测涨跌幅统一缩放到 12 小时（即 1h 模型预测的总时长）的基准尺度。
    # 这样能让 15m 的短期爆发力和 1d 的大趋势在同一数量级底座上进行线性加权。
    TF_SCALE_FACTORS = {
        '5m':  12.0 / 1.0,    # 12 根 5m = 1 小时，缩放到 12 小时需放大 12 倍
        '15m': 12.0 / 3.0,    # 12 根 15m = 3 小时，缩放到 12 小时需放大 4 倍
        '1h':  12.0 / 12.0,   # 基准 12 小时，倍数 1
        '4h':  12.0 / 48.0,   # 12 根 4h = 48 小时，缩放到 12 小时需缩小 4 倍倒数 (0.25)
        '1d':  12.0 / 288.0,  # 12 根 1d = 288 小时，倍数 1/24 ≈ 0.04167
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

            # 若时框不在预设权重表，给默认权重 0.5（支持回测中自定义时框）
            weight = self.TIMEFRAME_WEIGHTS.get(tf, 0.5)
            
            # 基础涨跌幅
            raw_change_pct = (pred_price - current_price) / current_price
            
            # 时框对齐：缩放到基准 12 小时的波动率尺度
            scale = self.TF_SCALE_FACTORS.get(tf, 1.0)
            change_pct = raw_change_pct * scale

            weighted_change += change_pct * weight
            total_weight += weight
            valid_count += 1

            direction = "↑" if raw_change_pct > 0 else "↓"
            reasons.append(f"{tf}={direction}{raw_change_pct:.2%}(基准化:{change_pct:.2%})")

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

        信心度计算公式（渐进式）：
        - 单时框：置信度 = base × 0.80（保底 80% 比例，确保能触发交易）
        - 双时框：置信度 = base × 0.90
        - 三时框：置信度 = base × 1.00（满时框最高）
        - 避免单时框因除以3导致置信度过低（<0.4）无法触发任何交易
        """
        abs_change = abs(change_pct)
        total_tf = len(self.TIMEFRAME_WEIGHTS)  # 3

        if abs_change < self.threshold:
            # 信号不足，持仓观望
            return 'HOLD', 0.0

        # 计算基础信心度（阈值~强阈值区间线性插值）
        if abs_change >= self.strong_threshold:
            base_confidence = 0.85
        else:
            ratio = (abs_change - self.threshold) / (self.strong_threshold - self.threshold)
            base_confidence = 0.5 + ratio * 0.35  # 0.5 ~ 0.85

        # 渐进式多时框加成：1框=0.8，2框=0.9，3框=1.0
        # 保证单时框下 base=0.5 → confidence=0.40，能触发交易
        data_factor = 0.8 + 0.2 * (valid_count / total_tf)
        confidence = round(base_confidence * data_factor, 2)

        action = 'BUY' if change_pct > 0 else 'SELL'
        return action, confidence

    def update_thresholds(self, threshold: float, strong_threshold: float):
        """动态更新阈值（供 Dashboard 调用）"""
        self.threshold = threshold
        self.strong_threshold = strong_threshold
