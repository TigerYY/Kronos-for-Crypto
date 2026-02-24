"""
Vercel Serverless Function 入口
将 FastAPI 后端包装为 Vercel Python 函数

部署限制说明：
- Vercel 免费版无法加载 PyTorch（体积 >250MB 超限）
- 建议在本地或自己搭载 GPU 的服务器上获取完整的 Kronos 模型预测能力
"""
import sys
import os

# 将项目根目录加入路径以解析 backend 等包
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

# 导入 FastAPI app
from backend.main import app

# Vercel 会通过 app 变量识别 ASGI 服务
