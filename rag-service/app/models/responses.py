from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime


class DocumentMatch(BaseModel):
    """文档匹配结果"""
    document_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]


class RAGSearchResponse(BaseModel):
    """RAG搜索响应模型"""
    results: List[DocumentMatch]
    query_embedding: List[float]
    search_time: float
    total_documents: int


class EmbedResponse(BaseModel):
    """文档嵌入响应模型"""
    success: bool
    processed_count: int
    failed_documents: List[str]
    processing_time: float


class BootstrapResponse(BaseModel):
    """系统初始化响应模型"""
    task_id: str
    estimated_documents: int
    estimated_time_hours: float
    status: str
    progress_url: str


class BootstrapProgress(BaseModel):
    """系统初始化进度响应"""
    task_id: str
    status: str
    progress_percentage: float
    processed_documents: int
    total_documents: int
    current_stage: str
    stages_completed: List[str]
    estimated_remaining_time: float
    error_count: int
    last_update_time: datetime


class RAGContextResponse(BaseModel):
    """RAG上下文增强响应"""
    context: str
    sources: List[str]
    relevance_score: float
    token_count: int


class SimilarityResponse(BaseModel):
    """相似度计算响应"""
    similarities: List[float]
    computation_time: float


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, bool]