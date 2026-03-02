"""
Kronos FastAPI backend: portfolio, OHLCV data, prediction, backtest, config.
Run from project root: uvicorn backend.main:app --reload --port 8000
"""
import os
import sys

# Run from project root so crypto_simulator, trading, backtest resolve
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routers import portfolio, data, predict, config, backtest

app = FastAPI(
    title="Kronos API",
    description="Unified API for dashboard, prediction, backtest, config",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API under /api so SPA can be served from / in production
app.include_router(portfolio.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve frontend build in production: static assets + SPA fallback
FRONTEND_DIST = os.path.join(ROOT, "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
            
        # 优先判断是否是根目录下的真实静态文件 (如 doc.html, vite.svg)
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # 否则回退给 React Router 返回 index.html
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Frontend not built"}, status_code=404)
