import os
from typing import Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    # ChromaDB配置
    chromadb_host: str = os.getenv('CHROMADB_HOST', 'localhost')
    chromadb_port: int = int(os.getenv('CHROMADB_PORT', '8000'))
    chromadb_collection: str = os.getenv('CHROMADB_COLLECTION', 'financial_documents')

    # 向量模型配置
    embedding_model_path: str = os.getenv('EMBEDDING_MODEL_PATH', './data/models/bge-large-zh-v1.5')
    model_device: str = os.getenv('MODEL_DEVICE', 'cpu')
    model_max_length: int = int(os.getenv('MODEL_MAX_LENGTH', '512'))

    # 服务配置
    rag_service_port: int = int(os.getenv('RAG_SERVICE_PORT', '8001'))
    max_query_length: int = int(os.getenv('MAX_QUERY_LENGTH', '1000'))
    default_similarity_threshold: float = float(os.getenv('DEFAULT_SIMILARITY_THRESHOLD', '0.7'))
    context_max_length: int = int(os.getenv('CONTEXT_MAX_LENGTH', '2000'))

    # PostgreSQL数据库配置
    database_url: str = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/prism2')

    # 缓存配置
    redis_url: str = os.getenv('REDIS_URL', 'redis://localhost:6379/2')
    cache_ttl: int = int(os.getenv('CACHE_TTL', '1800'))

    # 日志配置
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = os.getenv('LOG_FILE', './logs/rag-service.log')

    class Config:
        env_file = ".env"


settings = Settings()