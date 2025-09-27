from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from .config import settings

# 创建数据库引擎
engine = create_engine(settings.database_url, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class BootstrapTask(Base):
    """系统初始化任务表"""
    __tablename__ = "bootstrap_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    data_sources = Column(JSONB, nullable=False)
    time_range = Column(JSONB, nullable=False)
    status = Column(String(20), default='pending')
    progress_percentage = Column(Float, default=0)
    processed_documents = Column(Integer, default=0)
    total_documents = Column(Integer, default=0)
    current_stage = Column(String(50))
    stages_completed = Column(JSONB, default=list)
    error_count = Column(Integer, default=0)
    error_details = Column(JSONB)
    start_time = Column(DateTime, default=datetime.utcnow)
    estimated_completion = Column(DateTime)
    actual_completion = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class BatchProcessingLog(Base):
    """批量处理记录表"""
    __tablename__ = "batch_processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(UUID(as_uuid=True), nullable=False)
    batch_number = Column(Integer, nullable=False)
    data_source = Column(String(50), nullable=False)
    batch_size = Column(Integer, nullable=False)
    processing_status = Column(String(20), nullable=False)
    documents_processed = Column(Integer, default=0)
    documents_failed = Column(Integer, default=0)
    start_time = Column(DateTime, default=datetime.utcnow)
    completion_time = Column(DateTime)
    processing_time_seconds = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentQualityScore(Base):
    """文档质量评估表"""
    __tablename__ = "document_quality_scores"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(255), unique=True, nullable=False)
    data_source = Column(String(50), nullable=False)
    content_length = Column(Integer, nullable=False)
    readability_score = Column(Float)
    relevance_score = Column(Float)
    information_density = Column(Float)
    overall_quality = Column(Float, nullable=False)
    quality_tags = Column(JSONB)
    is_filtered = Column(Boolean, default=False)
    filter_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    """数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """创建数据库表"""
    Base.metadata.create_all(bind=engine)