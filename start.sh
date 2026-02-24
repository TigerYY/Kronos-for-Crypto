#!/bin/bash
# ─────────────────────────────────────────────────────────
#  Kronos 项目启动脚本
#  用法：./start.sh           → 启动 Streamlit 主页面（传统入口）
#        ./start.sh webui     → 启动 Flask K线预测界面
#        ./start.sh api       → 仅启动 FastAPI 后端（端口 8000）
#        ./start.sh dev       → 启动 FastAPI + 前端 dev（API:8000，前端:5173）
#        ./start.sh prod      → 构建前端并启动 FastAPI（同端口提供 API + 前端）
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

# ── 根据参数决定启动哪个服务 ──────────────────────────────
MODE="${1:-main}"

if [ "$MODE" = "webui" ]; then
    echo ""
    echo "🌐 启动 Flask K线预测界面..."
    echo "   访问地址：http://localhost:7070"
    echo "   按 Ctrl+C 停止"
    echo ""
    cd "$SCRIPT_DIR/webui"
    exec "$VENV/python3" app.py

elif [ "$MODE" = "api" ]; then
    echo ""
    echo "🔌 启动 FastAPI 后端（仅 API）..."
    echo "   访问地址：http://localhost:8000"
    echo "   API 文档：http://localhost:8000/docs"
    echo "   按 Ctrl+C 停止"
    echo ""
    cd "$SCRIPT_DIR"
    exec "$VENV/python3" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

elif [ "$MODE" = "dev" ]; then
    echo ""
    echo "🔌 启动 FastAPI 后端（端口 8000）..."
    cd "$SCRIPT_DIR"
    "$VENV/python3" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
    UVID_PID=$!
    sleep 2
    echo "🌐 启动前端 dev server（端口 5173）..."
    (cd "$SCRIPT_DIR/frontend" && npm run dev) &
    FEPID=$!
    echo ""
    echo "   后端：http://localhost:8000  前端：http://localhost:5173"
    echo "   按 Ctrl+C 停止"
    trap "kill $UVID_PID $FEPID 2>/dev/null; exit" INT TERM
    wait

elif [ "$MODE" = "prod" ]; then
    echo ""
    echo "📦 构建前端..."
    (cd "$SCRIPT_DIR/frontend" && npm run build)
    echo ""
    echo "🔌 启动 FastAPI（API + 前端，端口 8000）..."
    echo "   访问地址：http://localhost:8000"
    echo "   按 Ctrl+C 停止"
    echo ""
    cd "$SCRIPT_DIR"
    exec "$VENV/python3" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

else
    echo ""
    echo "🪐 启动 Kronos Crypto Dashboard（Streamlit 传统入口）..."
    echo "   访问地址：http://localhost:8502"
    echo "   推荐新架构：./start.sh prod 或 ./start.sh dev"
    echo "   按 Ctrl+C 停止"
    echo ""
    cd "$SCRIPT_DIR"
    exec "$VENV/streamlit" run crypto_dashboard.py \
        --server.port 8502 \
        --server.headless true \
        --browser.gatherUsageStats false
fi
