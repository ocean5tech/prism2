from fastapi import APIRouter, HTTPException
from datetime import datetime
import chromadb
import redis
import psycopg2

from app.core.config import settings
from app.models.responses import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """健康检查端点"""
    services = {}

    # 检查ChromaDB连接
    try:
        chroma_client = chromadb.HttpClient(
            host=settings.chromadb_host,
            port=settings.chromadb_port
        )
        chroma_client.heartbeat()
        services["chromadb"] = True
    except Exception as e:
        services["chromadb"] = False

    # 检查Redis连接
    try:
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        services["redis"] = True
    except Exception as e:
        services["redis"] = False

    # 检查PostgreSQL连接
    try:
        conn = psycopg2.connect(settings.database_url)
        conn.close()
        services["postgresql"] = True
    except Exception as e:
        services["postgresql"] = False

    # 确定整体状态
    overall_status = "healthy" if all(services.values()) else "unhealthy"

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        services=services
    )


@router.get("/ping")
async def ping():
    """简单ping检查"""
    return {"message": "pong", "timestamp": datetime.utcnow()}