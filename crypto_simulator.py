"""
Kronos 虚拟货币交易模拟器（重构版）

集成：
- MultiTimeframeStrategy：多时间框架信号融合
- RiskManager：仓位控制、止盈止损
- DataFetcher：Binance 数据获取（含缓存）
- VirtualPortfolio：虚拟持仓状态持久化

运行方式：
    python crypto_simulator.py
"""

import os
import sys
import time
import json
import pandas as pd
from datetime import datetime

try:
    import torch
    from model import Kronos, KronosTokenizer, KronosPredictor
    from peft import PeftModel
    MODEL_AVAILABLE = True
except ImportError:
    MODEL_AVAILABLE = False
    print("[Simulator] Warning: PyTorch or Kronos model cannot be imported, will use simulated functionality")

from trading.strategy import MultiTimeframeStrategy
from trading.risk_manager import RiskManager
from trading.data_fetcher import DataFetcher

# ────────────────────────────────────────────────────────
# 全局配置
# ────────────────────────────────────────────────────────
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'ES=F', 'XAU/USDT']
TIMEFRAMES = ['15m', '1h', '4h', '1d']
LOOKBACK = 400        # Kronos 输入 K 线数
PRED_LEN = 12         # 预测未来 K 线数
INITIAL_BALANCE = 10000.0  # 初始 USDT
SIMULATION_LOG_FILE = "simulation_log.csv"
PORTFOLIO_STATE_FILE = "portfolio_state.json"
BUY_PCT = 0.15        # 每次买入使用总资产的 15%
LOOP_INTERVAL = 60    # 循环间隔（秒）


# ────────────────────────────────────────────────────────
# 虚拟组合（支持状态持久化）
# ────────────────────────────────────────────────────────
class VirtualPortfolio:
    """
    虚拟资金组合，支持从 JSON 文件恢复状态，
    防止重启后余额丢失。
    """

    def __init__(self, initial_balance: float = INITIAL_BALANCE):
        self.balance = initial_balance
        self.positions = {sym: 0.0 for sym in SYMBOLS}
        self._load_state()
        self._ensure_log_file()

    def _load_state(self):
        """从持久化文件恢复余额和持仓"""
        if os.path.exists(PORTFOLIO_STATE_FILE):
            try:
                with open(PORTFOLIO_STATE_FILE, 'r') as f:
                    state = json.load(f)
                self.balance = state.get('balance', self.balance)
                saved_pos = state.get('positions', {})
                for sym in SYMBOLS:
                    self.positions[sym] = saved_pos.get(sym, 0.0)
                print(f"[Portfolio] 恢复状态 - 余额: {self.balance:.2f} USDT")
            except Exception as e:
                print(f"[Portfolio] 加载状态失败: {e}，使用默认初始值")

    def _save_state(self):
        """将当前状态保存到文件"""
        state = {
            'balance': self.balance,
            'positions': dict(self.positions),
            'last_update': datetime.utcnow().isoformat(),
        }
        with open(PORTFOLIO_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)

    def _ensure_log_file(self):
        """确保交易日志文件存在且有表头"""
        if not os.path.exists(SIMULATION_LOG_FILE):
            with open(SIMULATION_LOG_FILE, 'w') as f:
                f.write("timestamp,symbol,action,price,amount,balance,portfolio_value,reason\n")

    def log_trade(self, symbol: str, action: str, price: float, amount: float,
                  current_prices: dict, reason: str = ""):
        """记录交易到 CSV 日志"""
        timestamp = datetime.utcnow().isoformat()
        portfolio_val = self.get_total_value(current_prices)
        with open(SIMULATION_LOG_FILE, 'a') as f:
            f.write(f"{timestamp},{symbol},{action},{price:.6f},{amount:.6f},"
                    f"{self.balance:.2f},{portfolio_val:.2f},{reason}\n")
        print(f"  [{action}] {symbol} @ {price:.2f} | 数量: {amount:.6f} | "
              f"余额: {self.balance:.2f} USDT | 原因: {reason}")

    def buy(self, symbol: str, price: float, amount_usdt: float,
            current_prices: dict, reason: str = "") -> bool:
        """执行买入"""
        if self.balance < amount_usdt or amount_usdt < 10:
            return False
        amount_crypto = amount_usdt / price
        self.balance -= amount_usdt
        self.positions[symbol] = self.positions.get(symbol, 0.0) + amount_crypto
        self.log_trade(symbol, 'BUY', price, amount_crypto, current_prices, reason)
        self._save_state()
        return True

    def sell(self, symbol: str, price: float, amount_crypto: float = None,
             current_prices: dict = None, reason: str = "") -> bool:
        """执行卖出（默认全部卖出）"""
        current_pos = self.positions.get(symbol, 0.0)
        if amount_crypto is None:
            amount_crypto = current_pos
        if current_pos < amount_crypto or amount_crypto <= 1e-8:
            return False
        recv_usdt = amount_crypto * price
        self.balance += recv_usdt
        self.positions[symbol] = current_pos - amount_crypto
        self.log_trade(symbol, 'SELL', price, amount_crypto,
                       current_prices or {symbol: price}, reason)
        self._save_state()
        return True

    def get_total_value(self, current_prices: dict) -> float:
        """计算总资产（USDT）"""
        val = self.balance
        for sym, amt in self.positions.items():
            val += amt * current_prices.get(sym, 0.0)
        return val


# ────────────────────────────────────────────────────────
# 主模拟器
# ────────────────────────────────────────────────────────
class CryptoSimulator:
    """
    Kronos 驱动的虚拟货币交易模拟器

    每个循环：
    1. 拉取多交易对、多时框的实时 K 线
    2. 用 Kronos 预测每个时框的未来价格
    3. MultiTimeframeStrategy 融合信号
    4. RiskManager 过滤（检查止盈止损 + 仓位限制）
    5. 执行买卖并更新 VirtualPortfolio
    """

    def __init__(
        self,
        model_name: str | None = None,
        tokenizer_name: str | None = None,
        threshold: float = 0.005,
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.08,
    ):
        if MODEL_AVAILABLE:
            if torch.cuda.is_available():
                self.device = 'cuda'
            elif torch.backends.mps.is_available():
                self.device = 'mps'
            else:
                self.device = 'cpu'
            print(f"[Simulator] 使用设备: {self.device}")

            # 允许通过环境变量或参数覆盖模型路径（支持本地微调模型目录）
            env_model = os.getenv("KRONOS_MODEL_ID")
            env_tokenizer = os.getenv("KRONOS_TOKENIZER_ID")
            env_adapter = os.getenv("KRONOS_ADAPTER_ID") # 支持读取我们刚训练好的 LoRA Adapter
            
            resolved_model_name = model_name or env_model or "NeoQuasar/Kronos-small"
            resolved_tokenizer_name = tokenizer_name or env_tokenizer or "NeoQuasar/Kronos-Tokenizer-base"
            resolved_adapter_path = env_adapter # 如果没有配置就不加载

            print(f"[Simulator] 加载基础主干模型: {resolved_model_name}")
            print(f"[Simulator] 使用 tokenizer: {resolved_tokenizer_name}")
            self.tokenizer = KronosTokenizer.from_pretrained(resolved_tokenizer_name)
            self.model_obj = Kronos.from_pretrained(resolved_model_name)
            
            # Record original base model for hot-unloading
            if not hasattr(self, '_base_model_obj'):
                self._base_model_obj = self.model_obj
                
            self.load_lora_adapter(resolved_adapter_path)
            self.load_rl_heads()
            
            self.predictor = KronosPredictor(
                self.model_obj, self.tokenizer,
                device=self.device,
                max_context=LOOKBACK,
            )
            print("[Simulator] 交易预测引擎组装完成！")
        else:
            self.device = 'cpu'
            print("[Simulator] 当前以无模型轻量模式运行，预测功能将被降级为模拟值")

        # 初始化子组件
        self.data_fetcher = DataFetcher(exchange_id='binance')
        self.strategy = MultiTimeframeStrategy(
            threshold=threshold,
            strong_threshold=threshold * 3,
        )
        self.risk_manager = RiskManager(
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
        )
        self.portfolio = VirtualPortfolio()

    def load_lora_adapter(self, adapter_path: str | None):
        """动态卸载/加载 LoRA 权重，实现热重载"""
        if not MODEL_AVAILABLE or not hasattr(self, '_base_model_obj'):
            return
            
        current_is_peft = isinstance(self.model_obj, PeftModel)
        
        # Scenario 1: Switch back to Foundation Model (unload adapter)
        if not adapter_path:
            if current_is_peft:
                print(f"[Simulator] 🔄 卸载特定领域强化配置，回退至全局大盘全能 Foundation Model")
                self.model_obj = self._base_model_obj
                # Re-bind predictor to the base model
                if hasattr(self, 'predictor'):
                    self.predictor.model = self.model_obj
            return
            
        # Scenario 2: Load or Switch LoRA Adapter
        print(f"[Simulator] 👑 接收到指令: 挂载领域大模型特化权重: {adapter_path}")
        try:
            # Always wrap from the clean base model to avoid stacking adapters
            self.model_obj = PeftModel.from_pretrained(self._base_model_obj, adapter_path)
            if hasattr(self, 'predictor'):
                self.predictor.model = self.model_obj
            print("[Simulator] ✅ 绝境病毒注射成功，当前化身为特定标的走势杀手！")
        except Exception as e:
            print(f"[Simulator] ❌ LoRA 权重加载失败: {e}，将保持主干模型运行")
            self.model_obj = self._base_model_obj
            if hasattr(self, 'predictor'):
                self.predictor.model = self.model_obj

    def load_rl_heads(self):
        """尝试挂载强化学习风控脑 (Actor/Critic)"""
        if not MODEL_AVAILABLE:
            return
            
        actor_path = "outputs/rl_heads/actor_head.pth"
        value_path = "outputs/rl_heads/value_head.pth"
        
        if os.path.exists(actor_path) and os.path.exists(value_path):
            try:
                # Add heads to model object if not already there
                if not hasattr(self.model_obj, "actor_head"):
                    d_model = self.model_obj.config.d_model
                    self.model_obj.actor_head = torch.nn.Linear(d_model, 3).to(self.device)
                    self.model_obj.value_head = torch.nn.Linear(d_model, 1).to(self.device)
                    
                self.model_obj.actor_head.load_state_dict(torch.load(actor_path, map_location=self.device))
                self.model_obj.value_head.load_state_dict(torch.load(value_path, map_location=self.device))
                
                # Ensure they match the dtype of the main model
                self.model_obj.actor_head = self.model_obj.actor_head.to(torch.float32)
                self.model_obj.value_head = self.model_obj.value_head.to(torch.float32)
                
                # Force entire model to float32 to prevent any MPS autocasting mixed-type bugs
                self.model_obj = self.model_obj.float()
                
                print("[Simulator] 🧠 RL 对齐强化脑已加载，开启绝对收益风控模式！")
            except Exception as e:
                print(f"[Simulator] ❌ RL 权重加载失败: {e}")
        else:
            print("[Simulator] ℹ️ 未检测到 RL 对齐权重，将使用纯预训练策略")

    def predict(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict | None]:
        """对单时框 DataFrame 做 Kronos 预测"""
        x_df = df[['open', 'high', 'low', 'close', 'volume', 'amount']].copy()
        
        # Ensure timestamps are parsed as datetime to support arithmetic
        if df['timestamps'].dtype == object or isinstance(df['timestamps'].iloc[0], str):
            x_ts = pd.to_datetime(df['timestamps']).reset_index(drop=True)
        else:
            x_ts = df['timestamps'].reset_index(drop=True)
            
        diff = x_ts.iloc[-1] - x_ts.iloc[-2]
        y_ts = pd.Series([x_ts.iloc[-1] + diff * (i + 1) for i in range(PRED_LEN)])

        if not MODEL_AVAILABLE or not hasattr(self, 'predictor'):
            # Vercel fallback/mock logic
            # Produce mock dataframe containing previous 'close' with slight random noise
            mock_data = []
            last_close = float(df['close'].iloc[-1])
            import random
            for i in range(PRED_LEN):
                variation = last_close * random.uniform(-0.02, 0.02)
                mock_close = last_close + variation
                mock_data.append({
                    'open': mock_close,
                    'high': mock_close * 1.01,
                    'low': mock_close * 0.99,
                    'close': mock_close,
                    'volume': 0,
                    'amount': 0
                })
            return pd.DataFrame(mock_data), None

        pred_df = self.predictor.predict(
            df=x_df,
            x_timestamp=x_ts,
            y_timestamp=y_ts,
            pred_len=PRED_LEN,
            T=0.01,         # Stabilize UX: Low temperature
            top_k=1,        # Stabilize UX: Greedy decoding
            top_p=1.0,
            sample_count=1,
            verbose=False,
        )
        
        # Check if RL Heads exist
        rl_data = None
        if hasattr(self.model_obj, "actor_head") and hasattr(self.model_obj, "value_head"):
            try:
                action, value = self.predictor.predict_rl(x_df, x_ts)
                rl_data = {"action": action, "value": value}
            except Exception as e:
                print(f"[Simulator] Error during RL predict: {e}")
                
        return pred_df, rl_data

    def run_once(self):
        """执行一轮完整的分析 + 交易"""
        print(f"\n{'='*55}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始新一轮分析...")
        print(f"{'='*55}")

        current_prices = {}

        for symbol in SYMBOLS:
            print(f"\n📊 分析: {symbol}")

            # ── 1. 获取多时框数据和预测 ──────────────────
            predictions_per_tf = {}
            tf_dfs = self.data_fetcher.fetch_multi_timeframe(symbol, TIMEFRAMES, LOOKBACK)

            for tf, df in tf_dfs.items():
                if df is None or len(df) < LOOKBACK:
                    predictions_per_tf[tf] = None
                    print(f"  [{tf}] 数据不足，跳过")
                    continue
                try:
                    pred_df, rl_data = self.predict(df)
                    predictions_per_tf[tf] = float(pred_df['close'].iloc[-1])
                    current_prices[symbol] = float(df['close'].iloc[-1])
                    print(f"  [{tf}] 当前: {current_prices[symbol]:.2f} → "
                          f"预测: {predictions_per_tf[tf]:.2f} "
                          f"({(predictions_per_tf[tf]-current_prices[symbol])/current_prices[symbol]:+.2%})")
                    if rl_data:
                        rl_action_str = ['SHORT', 'HOLD', 'LONG'][rl_data['action']]
                        print(f"  [{tf}] RL Head 决策: {rl_action_str} | 预期胜率差: {rl_data['value']:.4f}")
                except Exception as e:
                    predictions_per_tf[tf] = None
                    print(f"  [{tf}] 预测失败: {e}")

            if symbol not in current_prices:
                print(f"  无法获取 {symbol} 当前价格，跳过")
                continue

            price = current_prices[symbol]
            total_val = self.portfolio.get_total_value(current_prices)

            # ── 2. 止盈止损检查（优先）──────────────────
            sl_tp = self.risk_manager.check_stop_loss_take_profit(symbol, price)
            if sl_tp == 'STOP_LOSS' and self.portfolio.positions.get(symbol, 0) > 0:
                pnl_pct = self.risk_manager.get_unrealized_pnl_pct(symbol, price)
                self.portfolio.sell(symbol, price, current_prices=current_prices,
                                    reason=f"止损 {pnl_pct:.2%}")
                self.risk_manager.record_sell(symbol, self.portfolio.positions.get(symbol, 0))
                continue

            elif sl_tp == 'TAKE_PROFIT' and self.portfolio.positions.get(symbol, 0) > 0:
                half_amt = self.portfolio.positions[symbol] * 0.5
                pnl_pct = self.risk_manager.get_unrealized_pnl_pct(symbol, price)
                self.portfolio.sell(symbol, price, half_amt, current_prices,
                                    reason=f"止盈50% {pnl_pct:.2%}")
                self.risk_manager.record_sell(symbol, half_amt)
                continue

            # ── 3. 生成融合信号 ─────────────────────────
            signal = self.strategy.generate_signal(predictions_per_tf, price)
            print(f"  🎯 信号: {signal}")

            # ── 4. 执行交易 ─────────────────────────────
            if signal.action == 'BUY' and signal.confidence > 0.45:
                want_usdt = total_val * BUY_PCT
                allowed, reason, adj_usdt = self.risk_manager.check_buy(
                    symbol=symbol,
                    amount_usdt=want_usdt,
                    total_portfolio_value=total_val,
                    current_prices=current_prices,
                    crypto_holdings=self.portfolio.positions,
                )
                if allowed:
                    bought = self.portfolio.buy(
                        symbol, price, adj_usdt, current_prices,
                        reason=f"信号买入 conf={signal.confidence:.2f}")
                    if bought:
                        self.risk_manager.record_buy(symbol, price, adj_usdt / price)
                else:
                    print(f"  ⛔ 买入被风控拦截: {reason}")

            elif signal.action == 'SELL' and self.portfolio.positions.get(symbol, 0) > 0:
                if signal.confidence > 0.45:
                    pos = self.portfolio.positions[symbol]
                    sold = self.portfolio.sell(
                        symbol, price, pos, current_prices,
                        reason=f"信号卖出 conf={signal.confidence:.2f}")
                    if sold:
                        self.risk_manager.record_sell(symbol, pos)

        # ── 5. 打印组合摘要 ─────────────────────────────
        total_val = self.portfolio.get_total_value(current_prices)
        print(f"\n💼 组合总值: ${total_val:,.2f} USDT | 余额: ${self.portfolio.balance:,.2f}")
        for sym, amt in self.portfolio.positions.items():
            if amt > 1e-8:
                val = amt * current_prices.get(sym, 0)
                pnl_pct = self.risk_manager.get_unrealized_pnl_pct(sym, current_prices.get(sym, 0))
                print(f"  {sym}: {amt:.6f} ≈ ${val:.2f} | 浮盈: {pnl_pct:+.2%}")


# ────────────────────────────────────────────────────────
# 入口
# ────────────────────────────────────────────────────────
if __name__ == "__main__":
    sim = CryptoSimulator()
    print("\n🚀 Kronos 交易模拟器已启动（Ctrl+C 停止）")

    try:
        while True:
            sim.run_once()
            print(f"\n⏰ 等待 {LOOP_INTERVAL} 秒后进行下一轮...")
            time.sleep(LOOP_INTERVAL)
    except KeyboardInterrupt:
        print("\n✅ 模拟器已停止，组合状态已保存。")
