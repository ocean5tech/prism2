#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批处理任务数据模型
"""
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator

class JobType(str, Enum):
    """任务类型枚举"""
    WATCHLIST_WARM = "watchlist_warm"
    MARKET_SCAN = "market_scan"
    CACHE_CLEAN = "cache_clean"
    RAG_SYNC = "rag_sync"

class JobCategory(str, Enum):
    """任务分类枚举"""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    PRIORITY = "priority"

class JobStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class BatchJobCreate(BaseModel):
    """创建批处理任务请求模型"""
    job_name: str = Field(..., max_length=100, description="任务名称")
    job_type: JobType = Field(..., description="任务类型")
    job_category: JobCategory = Field(JobCategory.MANUAL, description="任务分类")
    stock_code: Optional[str] = Field(None, description="处理的股票代码")
    data_type: Optional[str] = Field(None, description="处理的数据类型")
    watchlist_id: Optional[int] = Field(None, description="关联的自选股列表")
    priority_level: int = Field(3, ge=1, le=5, description="任务优先级")
    scheduled_time: Optional[datetime] = Field(None, description="计划执行时间")
    max_retries: int = Field(3, ge=0, description="最大重试次数")

    @validator('stock_code')
    def validate_stock_code(cls, v):
        """验证股票代码格式"""
        if v and (len(v) != 6 or not v.isdigit()):
            raise ValueError(f"无效的股票代码: {v}")
        return v

class BatchJobUpdate(BaseModel):
    """更新批处理任务请求模型"""
    status: Optional[JobStatus] = None
    priority_level: Optional[int] = Field(None, ge=1, le=5)
    scheduled_time: Optional[datetime] = None
    error_message: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None

class BatchJobResponse(BaseModel):
    """批处理任务响应模型"""
    id: int
    job_name: str
    job_type: JobType
    job_category: JobCategory
    stock_code: Optional[str]
    data_type: Optional[str]
    watchlist_id: Optional[int]
    status: JobStatus
    priority_level: int
    scheduled_time: Optional[datetime]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    processed_count: int
    success_count: int
    failed_count: int
    error_message: Optional[str]
    result_summary: Optional[Dict[str, Any]]
    retry_count: int
    max_retries: int
    created_at: datetime

    class Config:
        from_attributes = True

class BatchJobStats(BaseModel):
    """批处理任务统计模型"""
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    success_jobs: int
    failed_jobs: int
    avg_duration: Optional[float]
    success_rate: float
    last_run_time: Optional[datetime]

class BatchJobTrigger(BaseModel):
    """手动触发批处理任务请求模型"""
    job_type: JobType
    target_data: Optional[Dict[str, Any]] = Field(None, description="目标数据配置")
    priority_level: int = Field(5, ge=1, le=5, description="紧急任务优先级")
    force_execute: bool = Field(False, description="是否强制执行")

class BatchScheduleConfig(BaseModel):
    """批处理调度配置模型"""
    enabled: bool = Field(True, description="是否启用调度")
    max_concurrent_jobs: int = Field(5, ge=1, le=20, description="最大并发任务数")
    job_timeout: int = Field(300, ge=60, description="任务超时时间(秒)")
    retry_delay: int = Field(60, ge=10, description="重试延迟时间(秒)")
    cleanup_days: int = Field(30, ge=1, description="清理历史任务天数")