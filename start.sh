#!/bin/bash
# ─────────────────────────────────────────────────────────
#  Kronos 项目启动脚本
#  主页面：crypto_dashboard.py（Streamlit 多功能交易看板）
#  用法：./start.sh           → 启动主页面（默认）
#        ./start.sh webui     → 启动 Flask K线预测界面
# ─────────────────────────────────────────────────────────

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv/bin"

# ── 检查虚拟环境 ──────────────────────────────────────────
if [ ! -f "$VENV/python3" ]; then
    echo "⚙️  虚拟环境不存在，正在创建..."
    python3 -m venv "$SCRIPT_DIR/.venv"
    echo "📦 安装依赖..."
    "$VENV/pip" install -r "$SCRIPT_DIR/requirements.txt" \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple
    echo "✅ 依赖安装完成"
fi

# ── 根据参数决定启动哪个页面 ──────────────────────────────
MODE="${1:-main}"

if [ "$MODE" = "webui" ]; then
    echo ""
    echo "🌐 启动 Flask K线预测界面..."
    echo "   访问地址：http://localhost:7070"
    echo "   按 Ctrl+C 停止"
    echo ""
    cd "$SCRIPT_DIR/webui"
    exec "$VENV/python3" app.py

else
    echo ""
    echo "🪐 启动 Kronos Crypto Dashboard（主页面）..."
    echo "   访问地址：http://localhost:8502"
    echo "   按 Ctrl+C 停止"
    echo ""
    cd "$SCRIPT_DIR"
    exec "$VENV/streamlit" run crypto_dashboard.py \
        --server.port 8502 \
        --server.headless true \
        --browser.gatherUsageStats false
fi
