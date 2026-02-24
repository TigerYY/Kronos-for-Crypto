# Kronos 精度优化实验说明

本文档说明如何运行 BTC/USDT-1h 与 ES=F-1h 的微调实验，以及如何用回测和看板评估新模型。

## 1. 配置文件一览

| 场景 | 保守版配置 | 激进版配置 |
|------|------------|------------|
| BTC/USDT 1h | `configs/config_btcusdt_1h_conservative.yaml` | `configs/config_btcusdt_1h_aggressive.yaml` |
| ES=F 1h | `configs/config_esf_1h_conservative.yaml` | `configs/config_esf_1h_aggressive.yaml` |

每个 YAML 中需要修改的路径（请改成你本机实际路径）：

- `data.data_path`：对应标的的 1h K 线 CSV（列：timestamps, open, high, low, close, volume, amount）
- `model_paths.pretrained_tokenizer` / `pretrained_predictor`：Kronos 预训练模型目录
- `model_paths.base_path`：微调结果保存根目录（如 `.../finetune_csv/finetuned`）

## 2. 运行微调

在项目根目录或 `finetune_csv` 目录下执行（需先安装依赖并准备好数据）：

```bash
cd finetune_csv

# BTC/USDT 1h
python train_sequential.py --config configs/config_btcusdt_1h_conservative.yaml
python train_sequential.py --config configs/config_btcusdt_1h_aggressive.yaml

# ES=F 1h
python train_sequential.py --config configs/config_esf_1h_conservative.yaml
python train_sequential.py --config configs/config_esf_1h_aggressive.yaml
```

多卡 DDP 示例：

```bash
DIST_BACKEND=nccl torchrun --standalone --nproc_per_node=8 train_sequential.py --config configs/config_btcusdt_1h_conservative.yaml
```

训练完成后，模型会保存在 `{base_path}/{exp_name}/` 下，例如：

- `.../finetuned/BTCUSDT_1h_conservative/tokenizer/best_model/`
- `.../finetuned/BTCUSDT_1h_conservative/basemodel/best_model/`

## 3. 使用微调模型

### 3.1 Streamlit 看板 / 模拟器（crypto_dashboard.py）

启动前设置环境变量，指向你要用的 tokenizer 与 basemodel 目录：

```bash
export KRONOS_MODEL_ID="/your/path/finetuned/BTCUSDT_1h_conservative/basemodel/best_model"
export KRONOS_TOKENIZER_ID="/your/path/finetuned/BTCUSDT_1h_conservative/tokenizer/best_model"

./start.sh
```

访问 http://localhost:8502，看板会使用上述本地模型做预测。

### 3.2 Flask WebUI（webui/app.py）

```bash
export KRONOS_CUSTOM_MODEL_DIR="/your/path/.../basemodel/best_model"
export KRONOS_CUSTOM_TOKENIZER_DIR="/your/path/.../tokenizer/best_model"

cd webui && python app.py
```

在界面或通过 API 选择/加载 `kronos-custom` 模型即可。

### 3.3 回测引擎（backtest/backtester.py）

用本地微调模型做历史回测时：

```bash
export KRONOS_BACKTEST_MODEL_ID="/your/path/.../basemodel/best_model"
export KRONOS_BACKTEST_TOKENIZER_ID="/your/path/.../tokenizer/best_model"

# 之后运行你的回测脚本或通过 crypto_dashboard 的回测入口（若已恢复该页）执行回测
```

未设置上述变量时，回测仍使用默认的 NeoQuasar/Kronos-small。

## 4. 回测对比建议

1. **基准**：不设置 `KRONOS_BACKTEST_*`，用默认模型对同一标的、同一时间区间、同一参数（lookback、pred_len、threshold 等）跑一次回测，记录总收益率、年化、夏普、最大回撤、胜率等。
2. **微调模型**：设置 `KRONOS_BACKTEST_MODEL_ID` / `KRONOS_BACKTEST_TOKENIZER_ID` 为某次实验的 `basemodel/best_model` 与 `tokenizer/best_model`，在相同条件下再跑一次回测。
3. **对比**：比较两次的 `BacktestResult.metrics` 与交易笔数、净值曲线，判断新模型是否在历史区间上带来改进；再在实时看板中观察一段时间，确认无异常后再长期使用。

## 5. 数据与超参建议

- **BTC/USDT 1h**：建议至少 1～2 年连续 1h K 线；保守版适合先验证流程，激进版可尝试更长 lookback 与略高学习率。
- **ES=F 1h**：期货指数波动与交易时段与加密货币不同，建议单独准备 ES=F 的 1h CSV，必要时可微调 `threshold`、`stop_loss_pct`、`take_profit_pct` 等策略参数再回测。

更多数据清洗与归一化选项（缺失值、异常值、归一化方式）见各 YAML 中的 `data` 段及 [README_CN.md](README_CN.md)。
