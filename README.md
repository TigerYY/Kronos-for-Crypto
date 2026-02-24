<div align="center">
  <img src="./figures/logo.png" width="80" alt="Kronos Logo">
  <h1>Kronos for Crypto</h1>
  <p><b>金融 K 线基础模型 × AI 加密货币量化交易系统</b></p>
  <p><i>A Foundation Model for Financial Markets · Full-Stack Crypto Trading Platform</i></p>
</div>

<div align="center">

[![Hugging Face](https://img.shields.io/badge/🤗-HuggingFace-yellow)](https://huggingface.co/NeoQuasar)
[![Original Paper](https://img.shields.io/badge/�-arXiv-red)](https://arxiv.org/abs/2508.02739)
[![AAAI 2026](https://img.shields.io/badge/🏆-AAAI_2026-purple)](https://aaai.org/conference/aaai/aaai-26/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-red?logo=pytorch)](https://pytorch.org/)
[![License](https://img.shields.io/github/license/shiyu-coder/Kronos?color=green)](./LICENSE)

</div>

---

## 📖 关于本项目

本仓库基于 [Kronos](https://github.com/shiyu-coder/Kronos)（AAAI 2026）—— 首个面向金融 K 线的开源基础模型，在其之上构建了一套**完整的加密货币量化交易工程系统**。

**Kronos 做什么？**  
将 K 线序列（OHLCV）视为一种「金融语言」，通过在 45+ 全球交易所预训练的 Transformer，实现对未来 K 线走势的自回归预测。

**本仓库扩展了什么？**

| 模块 | 文件 | 功能 |
|------|------|------|
| 🤖 **交易模拟器** | `crypto_simulator.py` | 实盘模拟：信号生成 + 自动买卖 + 持仓管理 |
| 🔬 **回测引擎** | `backtest/backtester.py` | 历史回测：滑动窗口 + 绩效评估 |
| 📡 **数据获取** | `trading/data_fetcher.py` | ccxt（Binance）+ yfinance（ES=F 期货）|
| 🧠 **策略模块** | `trading/strategy.py` | 多时框加权信号融合（5m/15m/1h/4h/1d）|
| 🛡️ **风险管理** | `trading/risk_manager.py` | 止损 / 止盈 / 仓位控制 |
| 🔌 **统一后端 API** | `backend/main.py` | FastAPI：组合 / 数据 / 预测 / 回测 / 配置 |
| 🌐 **交互前端** | `frontend/` | React + TypeScript + Vite 单页应用 |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- macOS / Linux（Apple Silicon MPS 加速可选）
- NVIDIA GPU（CUDA 可选）

### 一键启动（推荐）

```bash
# 1. 克隆本仓库
git clone https://github.com/TigerYY/Kronos-for-Crypto.git
cd Kronos-for-Crypto

# 2. 授予执行权限（首次）
chmod +x start.sh

# 3. 启动（任选一种）
./start.sh        # 默认：构建前端并启动 FastAPI 全栈应用（同端口）
./start.sh dev    # 开发：启动 FastAPI(8000) 和前端 dev(5173) 双服务
./start.sh api    # 纯享：仅启动 FastAPI 后端 API（端口 8000）
```

> 💡 首次运行自动创建 `.venv` 虚拟环境并安装全部依赖（含 PyTorch CPU 版），约需 **3~8 分钟**。  
> 使用默认的 全栈模式 或 `dev` 模式前请先确保本机环境能够正常支持 `npm install`。

启动后访问：

| 模式 | 地址 | 说明 |
|------|------|------|
| 🌐 **全栈应用（默认）** | <http://localhost:8000> | 这是您监控和策略操作的主界面 |
| 🔌 **开发：前端** | <http://localhost:5173> | `./start.sh dev` 时前端开发的热更新端口 |
| 🔌 **开发：API 文档** | <http://localhost:8000/docs> | 自动生成的 OpenAPI 交互文档 |

### 手动安装

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 安装 PyTorch（CPU 版，Mac/Linux 均可）
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 安装其余依赖
pip install -r requirements.txt

# 启动后端程序
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

#### Apple Silicon（MPS 加速）

```bash
# M 系列芯片安装完整 PyTorch（含 MPS）
pip install torch torchvision torchaudio
pip install -r requirements.txt
```

---

## ☁️ 一键部署 (Vercel)

本项目中的 **前后端分离架构** 完全适配 Vercel Serverless 环境，并实现了动态引入，支持一键零配置免费部署展示版本。

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FTigerYY%2FKronos-for-Crypto)

> **⚠️ Vercel 部署说明及限制**
>
> - **体积限制**：Vercel Serverless Function 免费版最大支持 250MB，因此无法打包庞大的 PyTorch 及 Kronos 模型。我们通过异常捕获软引入的方式解决了这一报错限制。
> - **功能降级**：Vercel 部署版为**展示轻量版**。你可以正常访问该项目的 UI 及历史流数据，但**无法执行实时推断预测**，因为底层模型未加载。
> - **完整体验**：如需体验实际的加密货币自动交易、真实回测及 AI 预测推断，请务必在本地或独立 GPU 机器上部署运行。

---

## 🖥️ 界面功能

### 📊 实时监控

```
┌──────────────────────────────────────────────────────────────┐
│  当前价格         预测价格         信号          组合总值      │
│  $95,420.00      $95,838.00     ▲ BUY         $10,248.35    │
│                  (+0.44%)      （置信 72%）   (+2.48%)       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ████ BTC/USDT · 1h — K线图 + Kronos预测线 + 成交量         │
│  ▲买入点  ▼卖出点                                            │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│   15m: $95,780   1h: $95,838   4h: $96,200   1d: $97,100   │
│  （多时框信号详情）                   置信度: ██████░░ 72%    │
└──────────────────────────────────────────────────────────────┘
```

- 支持交易对：`BTC/USDT`、`ETH/USDT`、`ES=F`（期货）
- 支持时间周期：`5m / 15m / 1h / 4h / 1d`
- 自动刷新（60s）模式

### 🔬 回测分析

```bash
# 参数示例
交易对:   BTC/USDT
时间周期: 1h
时间段:   2024-01-01 ~ 2024-06-01
初始资金: $10,000
lookback: 400 根 K 线
预测长度: 12 根 K 线
预测步长: 6（每 6 根做一次预测）
```

输出指标：

| 指标 | 说明 |
|------|------|
| 总收益率 | 回测区间策略总盈亏 |
| 年化收益率 | 折合年化的收益率 |
| 夏普比率 | 风险调整后收益（>1 优，>2 卓越）|
| 最大回撤 | 历史最大亏损幅度 |
| 胜率 | 盈利交易占所有交易的比例 |
| 交易次数 | 买卖操作总次数 |

### ⚙️ 策略配置

所有参数可在 Dashboard 中实时调整并持久化：

```
信号策略
  ├─ 买卖信号阈值    0.5%   （超过此涨跌幅才触发信号）
  └─ 强信号阈值      1.5%   （高置信度信号）

多时框权重
  ├─ 5m  权重 0.20
  ├─ 15m 权重 0.30
  └─ 1h  权重 0.50

风险管理
  ├─ 单次买入比例   15%
  ├─ 最大仓位上限   80%
  ├─ 止损比例        3%
  └─ 止盈比例        8%（触发后卖出 50%）
```

---

## 🏗️ 项目结构

```
Kronos-for-Crypto/
│
├── 🚀 start.sh                  # 一键启动脚本（主入口）
├── 🤖 crypto_simulator.py       # 交易模拟器（实盘模拟循环）
├── 📄 requirements.txt          # 主环境依赖清单
│
├── api/                         # Vercel Serverless 专属配置
│   ├── index.py                 # Vercel Function 入口（桥接至 backend）
│   └── requirements.txt         # Vercel 专用轻量依赖
│
├── backend/                     # FastAPI 统一后端（核心 API）
│   ├── main.py                  # API 路由主入口、SPA 静态文件伺服
│   ├── routers/                 # portfolio, data, predict, config, backtest
│   └── services/                # 薄服务封装层（连通引擎与 API）
│
├── frontend/                    # React + TypeScript + Vite 前端
│   ├── src/pages/               # Monitor, Backtest, Config, Doc
│   └── src/api/                 # API client (Axios/Fetch)
│
├── trading/                     # 交易系统核心引擎
│   ├── __init__.py
│   ├── data_fetcher.py          # 多源数据获取（ccxt + yfinance + 缓存）
│   ├── strategy.py              # MultiTimeframeStrategy 多时框信号融合
│   └── risk_manager.py          # RiskManager（止损 / 止盈 / 仓位控制）
│
├── backtest/                    # 回测引擎
│   ├── __init__.py
│   ├── backtester.py            # Backtester（滑动窗口历史回测）
│   └── metrics.py               # 绩效指标计算（夏普、MDD、胜率等）
│
├── model/                       # Kronos 模型定义（上游）
├── data/                        # K 线数据（.csv / .feather）
├── finetune/                    # 微调脚本（上游）
└── examples/                    # 使用示例（上游）
```

---

## 🤖 Kronos 模型

### 可用模型

| 模型 | 参数量 | 上下文长度 | 推荐场景 |
|------|--------|-----------|---------|
| `Kronos-mini` | 4.1M | 2048 tokens | 轻量快速推断 |
| `Kronos-small` | 24.7M | 512 tokens | 平衡性能（默认）|
| `Kronos-base` | 102.3M | 512 tokens | 最高精度 |

模型托管于 [HuggingFace / NeoQuasar](https://huggingface.co/NeoQuasar)，首次运行**自动下载**，无需手动操作。

### 推断流程

```
原始 OHLCV 数据（400 根 K 线）
        │
        ▼
 KronosTokenizer
 归一化 → 分桶 → Token 序列
        │
        ▼
 Kronos Transformer
 自回归预测（预测 12~120 根 K 线）
        │
        ▼
 反归一化 → 预测 OHLCV 序列
        │
        ▼
 MultiTimeframeStrategy
 多时框加权投票 → BUY / SELL / HOLD
        │
        ▼
 RiskManager
 止损止盈过滤 + 仓位控制 → 执行交易
```

### 代码调用示例

```python
from model import Kronos, KronosTokenizer, KronosPredictor
import pandas as pd

# 加载模型（首次自动下载）
tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
predictor = KronosPredictor(model, tokenizer, device="mps", max_context=400)

# 准备输入（需含 open/high/low/close/volume 列）
df = pd.read_csv("data/BTC_USDT_1h.csv")
x_df = df[["open", "high", "low", "close", "volume"]].tail(400)
x_ts = df["timestamps"].tail(400).reset_index(drop=True)

# 构建预测时间戳
diff = x_ts.iloc[-1] - x_ts.iloc[-2]
y_ts = pd.Series([x_ts.iloc[-1] + diff * (i + 1) for i in range(12)])

# 执行预测
pred_df = predictor.predict(
    df=x_df, x_timestamp=x_ts, y_timestamp=y_ts,
    pred_len=12, T=1.0, top_p=0.9, sample_count=1
)
print(pred_df[["open", "high", "low", "close"]])
```

---

## ⚙️ 配置说明

### 模拟器参数（`crypto_simulator.py`）

```python
SYMBOLS        = ['BTC/USDT', 'ETH/USDT', 'ES=F']  # 交易标的
TIMEFRAMES     = ['15m', '1h', '4h', '1d']           # 参与预测的时间框架
LOOKBACK       = 400    # Kronos 输入 K 线数
PRED_LEN       = 12     # 预测未来 K 线数
INITIAL_BALANCE= 10000  # 初始虚拟资金（USDT）
BUY_PCT        = 0.15   # 每次买入使用总资产的 15%
LOOP_INTERVAL  = 60     # 预测循环间隔（秒）
```

### 风险管理默认值

```python
stop_loss_pct   = 0.03   # 浮亏 3% 止损平仓
take_profit_pct = 0.08   # 浮盈 8% 止盈（卖出 50%）
max_exposure    = 0.80   # 加密货币持仓不超过总资产的 80%
```

### 运行时文件

| 文件 | 说明 |
|------|------|
| `portfolio_state.json` | 虚拟组合持仓状态（重启后自动恢复）|
| `simulation_log.csv` | 交易流水记录 |
| `strategy_config.json` | 策略参数配置（Dashboard 保存）|
| `backtest_risk_state_*.json` | 回测过程中的风险状态快照 |

---

## 🔌 REST API（FastAPI）

统一后端 API 分为多个模块路径，全量文档启动后可在 `http://localhost:8000/docs` 交互访问。

| 模块 | 核心端点 | 说明 |
|------|------|------|
| `Portfolio` | `/api/portfolio` | 获取虚拟持仓状态、交易记录流水等 |
| `Data` | `/api/data/ohlcv` | 获取实时与缓存的 OHLCV K 线数据 |
| `Predict` | `/api/predict` | 执行单/多时框的 Kronos 向前预测及融合信号获取 |
| `Backtest` | `/api/backtest` | 对所选区间数据全自动化地进行历史回测 |
| `Config` | `/api/config` | 加载或实时覆写风控、阈值及策略配置变量 |

---

## 📰 学术动态

- 🏆 **[2025.11.10]** Kronos 被 **AAAI 2026** 接收
- 📄 **[2025.08.17]** 发布微调脚本（支持自定义任务适配）
- 📝 **[2025.08.02]** 论文发布于 [arXiv:2508.02739](https://arxiv.org/abs/2508.02739)

---

## 📖 引用

如果本项目对你有帮助，欢迎引用原始论文：

```bibtex
@inproceedings{kronos2026,
  title     = {Kronos: A Foundation Model for the Language of Financial Markets},
  booktitle = {Proceedings of the AAAI Conference on Artificial Intelligence (AAAI 2026)},
  year      = {2026}
}
```

---

## ⚠️ 免责声明

本项目仅供**学术研究与技术学习**使用。加密货币市场具有高度不确定性，AI 预测模型不保证收益。**请勿将本系统用于真实资金交易。**

---

## 📄 许可证

本项目采用 [MIT License](./LICENSE)。上游 Kronos 模型版权归原作者所有。

---

<div align="center">
  <sub>🪐 Built with PyTorch · FastAPI · React · ccxt · yfinance</sub><br>
  <sub>Based on <a href="https://github.com/shiyu-coder/Kronos">Kronos (AAAI 2026)</a></sub>
</div>
