from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.core.config import settings
from app.core.database import create_tables
from app.api.v1.rag import router as rag_router
from app.api.v1.health import router as health_router

# 创建日志目录
os.makedirs("logs", exist_ok=True)

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="RAG Service",
    description="检索增强生成服务 - 为股票分析平台提供智能文档检索和上下文增强",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    logger.info("RAG Service 正在启动...")

    # 创建数据库表
    create_tables()
    logger.info("数据库表初始化完成")

    logger.info(f"RAG Service 启动完成，运行在端口 {settings.rag_service_port}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    logger.info("RAG Service 正在关闭...")


# 注册路由
app.include_router(rag_router, prefix="/api/rag", tags=["RAG"])
app.include_router(health_router, prefix="/api", tags=["Health"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "RAG Service",
        "version": "1.0.0",
        "status": "running",
        "description": "检索增强生成服务 - 为股票分析平台提供智能文档检索和上下文增强"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.rag_service_port,
        reload=True,
        log_level=settings.log_level.lower()
    )