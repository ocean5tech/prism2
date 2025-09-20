"""
Prism2 Backend API 主应用
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_database
from app.api.v1 import health, stocks

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting Prism2 Backend API...")

    # 初始化数据库连接
    if init_database():
        logger.info("Database initialization successful")
    else:
        logger.error("Database initialization failed")
        raise RuntimeError("Database initialization failed")

    yield

    # 关闭时
    logger.info("Shutting down Prism2 Backend API...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Prism2股票分析平台后端API",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(
    health.router,
    prefix=settings.api_v1_prefix,
    tags=["健康检查"]
)

app.include_router(
    stocks.router,
    prefix=settings.api_v1_prefix,
    tags=["股票数据"]
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Prism2 Backend API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )