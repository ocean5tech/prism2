from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime


class RAGSearchRequest(BaseModel):
    """RAG搜索请求模型"""
    query: str
    stock_code: Optional[str] = None
    search_type: str = "semantic"
    limit: int = 5
    similarity_threshold: float = 0.7
    filters: Optional[Dict[str, Any]] = None


class DocumentInput(BaseModel):
    """文档输入模型"""
    id: str
    content: str
    metadata: Dict[str, Any]


class DocumentEmbedRequest(BaseModel):
    """文档嵌入请求模型"""
    documents: List[DocumentInput]
    collection_name: Optional[str] = None


class BootstrapRequest(BaseModel):
    """系统初始化请求模型"""
    data_sources: List[str]
    time_range: Dict[str, str]
    batch_size: int = 100
    max_concurrent: int = 5
    enable_quality_filter: bool = True


class ContextEnhancementRequest(BaseModel):
    """上下文增强请求模型"""
    query: str
    stock_code: Optional[str] = None
    context_type: str = "investment"
    max_context_length: int = 2000


class SimilarityRequest(BaseModel):
    """相似度计算请求模型"""
    document_pairs: List[Tuple[str, str]]
    similarity_method: str = "cosine"