#!/usr/bin/env python3
"""
Shared database connection utilities for 4MCP architecture
"""

import asyncio
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Optional, Dict, Any, List
import json
from config import config
from logger import get_logger

logger = get_logger("Database")

class RedisConnection:
    """Redis connection manager"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None

    def get_sync_client(self) -> redis.Redis:
        """Get synchronous Redis client"""
        if self.redis_client is None:
            self.redis_client = redis.Redis(
                host=config.database.redis_host,
                port=config.database.redis_port,
                db=config.database.redis_db,
                password=config.database.redis_password,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
        return self.redis_client

    async def get_async_client(self) -> redis.Redis:
        """Get Redis client for async operations (using sync client in executor)"""
        return self.get_sync_client()

    async def get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data from Redis"""
        try:
            client = await self.get_async_client()
            loop = asyncio.get_event_loop()
            cached_data = await loop.run_in_executor(None, client.get, key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    async def set_cached_data(self, key: str, data: Dict[str, Any], ttl: int = 300) -> bool:
        """Set cached data in Redis with TTL"""
        try:
            client = await self.get_async_client()
            json_data = json.dumps(data, ensure_ascii=False)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, client.set, key, json_data, ttl)
            logger.info(f"Cached data for key {key} with TTL {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    async def delete_cached_data(self, key: str) -> bool:
        """Delete cached data from Redis"""
        try:
            client = await self.get_async_client()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, client.delete, key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

class PostgreSQLConnection:
    """PostgreSQL connection manager"""

    def __init__(self):
        self.sync_engine = None
        self.async_engine = None
        self.async_session_factory = None

    def get_sync_engine(self):
        """Get synchronous SQLAlchemy engine"""
        if self.sync_engine is None:
            connection_string = (
                f"postgresql://{config.database.postgresql_user}:"
                f"{config.database.postgresql_password}@"
                f"{config.database.postgresql_host}:"
                f"{config.database.postgresql_port}/"
                f"{config.database.postgresql_db}"
            )
            self.sync_engine = create_engine(
                connection_string,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800
            )
        return self.sync_engine

    def get_async_engine(self):
        """Get asynchronous SQLAlchemy engine"""
        if self.async_engine is None:
            connection_string = (
                f"postgresql+asyncpg://{config.database.postgresql_user}:"
                f"{config.database.postgresql_password}@"
                f"{config.database.postgresql_host}:"
                f"{config.database.postgresql_port}/"
                f"{config.database.postgresql_db}"
            )
            self.async_engine = create_async_engine(
                connection_string,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800
            )

            self.async_session_factory = sessionmaker(
                self.async_engine, class_=AsyncSession, expire_on_commit=False
            )
        return self.async_engine

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        try:
            engine = self.get_async_engine()
            async with self.async_session_factory() as session:
                result = await session.execute(text(query), params or {})
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]
        except Exception as e:
            logger.error(f"PostgreSQL query error: {e}")
            return []

    def get_sync_connection(self):
        """Get direct psycopg2 connection for simple queries"""
        try:
            conn = psycopg2.connect(
                host=config.database.postgresql_host,
                port=config.database.postgresql_port,
                database=config.database.postgresql_db,
                user=config.database.postgresql_user,
                password=config.database.postgresql_password,
                cursor_factory=RealDictCursor
            )
            return conn
        except Exception as e:
            logger.error(f"PostgreSQL connection error: {e}")
            return None

class DataManager:
    """Combined data manager for Redis and PostgreSQL"""

    def __init__(self):
        self.redis = RedisConnection()
        self.postgres = PostgreSQLConnection()

    async def get_stock_data(self, stock_code: str, data_type: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get stock data with caching strategy

        Priority:
        1. Redis cache (if not force_refresh)
        2. PostgreSQL database
        3. Return None if not found
        """
        cache_key = f"stock:{stock_code}:{data_type}"

        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_data = await self.redis.get_cached_data(cache_key)
            if cached_data:
                logger.info(f"Found cached data for {stock_code}:{data_type}")
                return cached_data

        # Query PostgreSQL
        try:
            if data_type == "basic":
                query = """
                    SELECT code, name, market, industry, listing_date
                    FROM stock_basic_info
                    WHERE code = :stock_code
                """
            elif data_type == "kline":
                query = """
                    SELECT * FROM stock_kline_data
                    WHERE code = :stock_code
                    ORDER BY trade_date DESC
                    LIMIT 100
                """
            elif data_type == "financial":
                query = """
                    SELECT * FROM stock_financial_data
                    WHERE code = :stock_code
                    ORDER BY report_date DESC
                    LIMIT 10
                """
            else:
                logger.warning(f"Unknown data type: {data_type}")
                return None

            results = await self.postgres.execute_query(
                query, {"stock_code": stock_code}
            )

            if results:
                data = {
                    "stock_code": stock_code,
                    "data_type": data_type,
                    "data": results,
                    "source": "postgresql",
                    "timestamp": asyncio.get_event_loop().time()
                }

                # Cache the result
                ttl = 300 if data_type == "kline" else 3600  # 5min for kline, 1hr for others
                await self.redis.set_cached_data(cache_key, data, ttl)

                logger.info(f"Retrieved {len(results)} records for {stock_code}:{data_type} from PostgreSQL")
                return data
            else:
                logger.warning(f"No data found in PostgreSQL for {stock_code}:{data_type}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving stock data for {stock_code}:{data_type}: {e}")
            return None

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all database connections"""
        health = {}

        # Check Redis
        try:
            redis_client = await self.redis.get_async_client()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, redis_client.ping)
            health["redis"] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            health["redis"] = False

        # Check PostgreSQL
        try:
            results = await self.postgres.execute_query("SELECT 1 as test")
            health["postgresql"] = len(results) == 1
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            health["postgresql"] = False

        return health

# Global instances
redis_conn = RedisConnection()
postgres_conn = PostgreSQLConnection()
data_manager = DataManager()