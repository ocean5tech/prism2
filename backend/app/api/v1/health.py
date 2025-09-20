"""
e∑¿ÂAPI
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from redis import Redis

from app.core.config import settings
from app.core.database import get_db, get_redis_stock, get_redis_search, get_redis_system
from app.schemas.stock import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: Session = Depends(get_db),
    redis_stock: Redis = Depends(get_redis_stock),
    redis_search: Redis = Depends(get_redis_search),
    redis_system: Redis = Depends(get_redis_system)
):
    """
    e∑¿Â•„
    ¿ÂpnìRedisﬁ•∂
    """
    try:
        # ¿Âpnìﬁ•
        db.execute("SELECT 1")
        logger.info("Database health check passed")

        # ¿ÂRedisﬁ•
        redis_stock.ping()
        redis_search.ping()
        redis_system.ping()
        logger.info("Redis health check passed")

        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            version=settings.app_version
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/health/db")
async def database_health(db: Session = Depends(get_db)):
    """pnìe∑¿Â"""
    try:
        # K’pnìÂ‚
        result = db.execute("SELECT version();").fetchone()
        return {
            "status": "healthy",
            "database_version": result[0] if result else "unknown",
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/health/redis")
async def redis_health(
    redis_stock: Redis = Depends(get_redis_stock),
    redis_search: Redis = Depends(get_redis_search),
    redis_system: Redis = Depends(get_redis_system)
):
    """Redise∑¿Â"""
    try:
        # K’*Redispnì
        redis_status = {
            "stock_db": redis_stock.ping(),
            "search_db": redis_search.ping(),
            "system_db": redis_system.ping()
        }

        return {
            "status": "healthy",
            "redis_databases": redis_status,
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))