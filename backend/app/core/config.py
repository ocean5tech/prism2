# -*- coding: utf-8 -*-
"""
Configuration management module
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application basic configuration
    app_name: str = "Prism2 Backend API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database configuration
    database_url: str = "postgresql://prism2:prism2_secure_password@localhost:5432/prism2"

    # Redis configuration
    redis_url: str = "redis://localhost:6379"
    redis_db_stock: int = 0
    redis_db_search: int = 1
    redis_db_system: int = 2

    # External services
    rag_service_url: str = "http://localhost:8001"

    # Cache TTL configuration (seconds)
    cache_ttl_stock_info: int = 86400
    cache_ttl_kline: int = 1800
    cache_ttl_news: int = 14400
    cache_ttl_analysis: int = 86400
    cache_ttl_search: int = 300

    # API configuration
    api_v1_prefix: str = "/api/v1"

    class Config:
        env_file = ".env"
        extra = "ignore"


# Global settings instance
settings = Settings()