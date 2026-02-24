<div align="center">
  <img src="./figures/logo.png" width="80" alt="Kronos Logo">
  <h1>Kronos</h1>
  <p><b>金融 K 线基础模型 · AI 加密货币交易系统</b></p>
  <p>A Foundation Model for Financial Markets + Full-Stack Crypto Trading Platform</p>
</div>

<div align="center">

[![Hugging Face](https://img.shields.io/badge/🤗-Hugging_Face-yellow)](https://huggingface.co/NeoQuasar)
[![Live Demo](https://img.shields.io/badge/🚀-Live_Demo-brightgreen)](https://shiyu-coder.github.io/Kronos-demo/)
[![Last Commit](https://img.shields.io/github/last-commit/shiyu-coder/Kronos?color=blue)](https://github.com/shiyu-coder/Kronos/graphs/commit-activity)
[![Stars](https://img.shields.io/github/stars/shiyu-coder/Kronos?color=lightblue)](https://github.com/shiyu-coder/Kronos/stargazers)
[![License](https://img.shields.io/github/license/shiyu-coder/Kronos?color=green)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-red?logo=pytorch)](https://pytorch.org/)

</div>

---

## ✨ 项目概览

Kronos 是首个面向金融 K 线（OHLCV）数据的**开源基础模型**，在来自全球 45+ 家交易所的数据上预训练，具备强大的 K 线序列理解与预测能力。

在原始学术模型基础上，本仓库**扩展了一套完整的加密货币量化交易系统**，包含：

| 模块 | 功能 |
|------|------|
| 🪐 **Crypto Dashboard** | Streamlit 多页面交易看板（实时监控 / 回测 / 策略配置）|
| � **WebUI** | Flask K 线预测界面（深色主题，交互图表）|
| 🤖 **交易模拟器** | 基于 Kronos 预测的自动信号生成与持仓管理 |
| � **回测引擎** | 历史数据回测 + 绩效指标（夏普、最大回撤、胜率）|
| � **数据获取** | ccxt（Binance 等）+ yfinance（ES=F 期货）多源数据 |

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/shiyu-coder/Kronos.git
cd Kronos
```

### 2. 一键启动（推荐）

```bash
# 授予执行权限（首次）
chmod +x start.sh

# 启动主页面（Kronos Crypto Dashboard）
./start.sh
```

> 首次运行会自动创建虚拟环境并安装所有依赖，约需 3-5 分钟（含 PyTorch 下载）

| 界面 | 地址 | 说明 |
|------|------|------|
| 🪐 主页面 | <http://localhost:8502> | Streamlit 交易看板 |
| 🔮 WebUI | <http://localhost:7070> | Flask K 线预测界面 |

```bash
# 启动 Flask WebUI（可选）
./start.sh webui
```

### 3. 手动安装（可选）

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖（PyTorch CPU 版）
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 启动主页面
streamlit run crypto_dashboard.py --server.port 8502
```

---

## 🖥️ 界面预览

### 主页面 — Kronos Crypto Dashboard

```
┌─────────────────────────────────────────────────────────┐
│  🪐 Kronos Trading    │  📊 实时监控                    │
│  ─────────────────    │  ─────────────────────────────  │
│  ○ 📊 实时监控        │  交易对: BTC/USDT  周期: 1h     │
│  ○ 🔬 回测分析        │                                 │
│  ○ ⚙️ 策略配置        │  ┌──────────────────────────┐  │
│                       │  │   K线图 + Kronos预测线    │  │
│  💼 组合概览          │  │   成交量柱状图             │  │
│  余额: $10,000.00     │  └──────────────────────────┘  │
│                       │                                 │
│                       │  ▲ BUY  📈 多时框信号详情      │
└─────────────────────────────────────────────────────────┘
```

---

## 🏗️ 项目结构

```
Kronos/
├── 📄 start.sh                 # ⭐ 一键启动脚本（主入口）
├── 📄 crypto_dashboard.py      # ⭐ 主页面（Streamlit 交易看板）
├── 📄 crypto_simulator.py      # 交易模拟器（信号生成 + 持仓管理）
├── 📄 requirements.txt         # 依赖清单
│
├── 📁 trading/                 # 交易系统核心模块
│   ├── data_fetcher.py         # 多源数据获取（ccxt + yfinance）
│   ├── strategy.py             # 多时框信号策略
│   └── risk_manager.py         # 风险管理（止损 / 止盈 / 仓位控制）
│
├── 📁 backtest/                # 回测引擎
│   ├── backtester.py           # 历史回测主逻辑
│   └── metrics.py              # 绩效指标计算（夏普、回撤、胜率等）
│
├── 📁 webui/                   # Flask K线预测界面（辅助）
│   ├── app.py                  # Flask 后端
│   └── templates/index.html    # 深色主题前端
│
├── 📁 model/                   # Kronos 模型定义
├── 📁 data/                    # K线数据文件（.csv / .feather）
├── 📁 finetune/                # 微调脚本
└── 📁 examples/                # 使用示例
```

---

## 🤖 Kronos 模型

Kronos 将 K 线数据视为「金融语言」，通过 Transformer 架构进行自回归预测。

### 可用模型

| 模型 | 参数量 | 上下文长度 | 适用场景 |
|------|--------|------------|----------|
| `Kronos-mini` | 4.1M | 2048 | 快速推断 |
| `Kronos-small` | 24.7M | 512 | 平衡性能 |
| `Kronos-base` | 102.3M | 512 | 最佳精度 |

模型托管于 [HuggingFace NeoQuasar](https://huggingface.co/NeoQuasar)，首次运行自动下载。

### 预测流程

```
原始 OHLCV 数据
    ↓
KronosTokenizer（归一化 + Token化）
    ↓
Kronos Transformer（自回归推断）
    ↓
预测 K 线序列（open/high/low/close）
    ↓
交易信号生成（多时框加权投票）
```

---

## � 交易系统功能

### 实时监控

- **多时框预测**：同时对 5m / 15m / 1h / 4h / 1d 执行 Kronos 预测
- **信号生成**：基于预测涨跌幅加权投票，输出 BUY / SELL / HOLD
- **K 线图表**：Plotly 交互式 K 线 + 预测线 + 成交量
- **交易标记**：历史买入 / 卖出点叠加展示

### 回测分析

- 支持自定义时间段、交易对、时间周期
- 绩效指标：总收益率、年化收益率、夏普比率、最大回撤、胜率
- 净值曲线可视化

### 策略配置

- 信号阈值 / 强信号阈值
- 多时框权重（5m / 15m / 1h）
- 风险参数：买入比例、最大仓位、止损比例、止盈比例
- 配置持久化（`strategy_config.json`）

---

## � 学术动态

- 🏆 **[2025.11.10]** Kronos 被 AAAI 2026 接收
- 📄 **[2025.08.17]** 发布微调脚本
- 📝 **[2025.08.02]** 论文发布于 [arXiv](https://arxiv.org/abs/2508.02739)

---

## 📖 引用

```bibtex
@inproceedings{kronos2026,
  title     = {Kronos: A Foundation Model for the Language of Financial Markets},
  booktitle = {AAAI 2026},
  year      = {2026}
}
```

---

## � 许可证

本项目采用 [MIT License](./LICENSE)。

---

<div align="center">
  <sub>Built with ❤️ on top of the Kronos foundation model</sub>
</div>
