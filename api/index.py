"""
Vercel Serverless Function 入口
将 Flask WebUI 包装为 Vercel Python 函数

部署限制说明：
- Vercel 免费版无法加载 PyTorch（体积 >250MB 超限）
- 页面 UI 正常加载，K线数据浏览可用
- 模型预测功能在 Vercel 上不可用（需本地或 GPU 服务器运行）
"""
import sys
import os

# 将项目根目录和 webui 目录都加入路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBUI_DIR = os.path.join(ROOT_DIR, 'webui')

sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, WEBUI_DIR)

# 切换工作目录，使 Flask 能找到 templates/
os.chdir(WEBUI_DIR)

# 导入 Flask app（MODEL_AVAILABLE 会自动降级为 False）
from app import app

# Vercel 通过 handler 变量识别 WSGI 应用
handler = app
