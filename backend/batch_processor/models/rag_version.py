#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG版本管理数据模型
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid

class VectorStatus(str, Enum):
    """向量状态枚举"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    FAILED = "failed"

class DataType(str, Enum):
    """数据类型枚举"""
    FINANCIAL = "financial"
    ANNOUNCEMENTS = "announcements"
    SHAREHOLDERS = "shareholders"
    LONGHUBANG = "longhubang"

class RAGVersionCreate(BaseModel):
    """创建RAG版本请求模型"""
    stock_code: str = Field(..., description="股票代码")
    data_type: DataType = Field(..., description="数据类型")
    source_data: Dict[str, Any] = Field(..., description="原始结构化数据")
    embedding_model: str = Field("bge-large-zh-v1.5", description="嵌入模型")
    force_update: bool = Field(False, description="是否强制更新")

    @validator('stock_code')
    def validate_stock_code(cls, v):
        """验证股票代码格式"""
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError(f"无效的股票代码: {v}")
        return v

class RAGVersionUpdate(BaseModel):
    """更新RAG版本请求模型"""
    vector_status: Optional[VectorStatus] = None
    vector_metadata: Optional[Dict[str, Any]] = None
    chunk_count: Optional[int] = Field(None, ge=0)

class RAGVersionResponse(BaseModel):
    """RAG版本响应模型"""
    id: int
    stock_code: str
    data_type: DataType
    version_id: str
    data_hash: str
    vector_status: VectorStatus
    source_data: Dict[str, Any]
    vector_metadata: Optional[Dict[str, Any]]
    embedding_model: str
    chunk_count: int
    created_at: datetime
    activated_at: Optional[datetime]
    deprecated_at: Optional[datetime]

    class Config:
        from_attributes = True

class VectorMappingCreate(BaseModel):
    """创建向量映射请求模型"""
    version_id: str = Field(..., description="版本ID")
    vector_id: str = Field(..., description="ChromaDB向量ID")
    collection_name: str = Field(..., description="ChromaDB集合名")
    chunk_index: int = Field(..., ge=0, description="分块索引")
    chunk_text: str = Field(..., description="分块文本内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="向量元数据")

class VectorMappingResponse(BaseModel):
    """向量映射响应模型"""
    id: int
    version_id: str
    vector_id: str
    collection_name: str
    chunk_index: int
    chunk_text: str
    metadata: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

class RAGSyncRequest(BaseModel):
    """RAG同步请求模型"""
    stock_codes: List[str] = Field(..., description="股票代码列表")
    data_types: List[DataType] = Field(..., description="数据类型列表")
    force_refresh: bool = Field(False, description="是否强制刷新")
    batch_size: int = Field(10, ge=1, le=50, description="批处理大小")

    @validator('stock_codes')
    def validate_stock_codes(cls, v):
        """验证股票代码列表"""
        for code in v:
            if not code or len(code) != 6 or not code.isdigit():
                raise ValueError(f"无效的股票代码: {code}")
        return v

class RAGSyncResult(BaseModel):
    """RAG同步结果模型"""
    total_processed: int
    success_count: int
    failed_count: int
    skipped_count: int
    processing_time: float
    failed_items: List[Dict[str, str]]
    summary: Dict[str, Any]

class RAGQueryRequest(BaseModel):
    """RAG查询请求模型"""
    query_text: str = Field(..., description="查询文本")
    stock_codes: Optional[List[str]] = Field(None, description="限制股票代码")
    data_types: Optional[List[DataType]] = Field(None, description="限制数据类型")
    limit: int = Field(10, ge=1, le=100, description="返回结果数量")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="相似度阈值")

class RAGQueryResult(BaseModel):
    """RAG查询结果模型"""
    results: List[Dict[str, Any]]
    total_count: int
    processing_time: float
    query_metadata: Dict[str, Any]

class RAGVersionStats(BaseModel):
    """RAG版本统计模型"""
    total_versions: int
    active_versions: int
    deprecated_versions: int
    failed_versions: int
    total_chunks: int
    avg_chunks_per_version: float
    storage_size_mb: float
    last_sync_time: Optional[datetime]