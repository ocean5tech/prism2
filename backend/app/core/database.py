# -*- coding: utf-8 -*-
"""
Database configuration module
"""
import logging
from typing import Generator, Optional
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import redis
from redis import Redis

from .config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy配置
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis连接池
redis_client: Optional[Redis] = None


def get_redis() -> Redis:
    """获取Redis客户端实例"""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.redis_url,
            db=settings.redis_db_stock,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    return redis_client


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database() -> bool:
    """初始化数据库连接"""
    try:
        # 测试数据库连接
        with engine.connect() as conn:
            logger.info("Database connection successful")

        # 测试Redis连接
        redis_conn = get_redis()
        redis_conn.ping()
        logger.info("Redis connection successful")

        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def close_database():
    """关闭数据库连接"""
    global redis_client
    if redis_client:
        redis_client.close()
        redis_client = None
    engine.dispose()
    logger.info("Database connections closed")