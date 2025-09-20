#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自选股列表数据模型
"""
from typing import List, Optional
from datetime import datetime, time
from pydantic import BaseModel, Field, validator

class WatchlistCreate(BaseModel):
    """创建自选股列表请求模型"""
    user_id: str = Field(..., description="用户标识")
    watchlist_name: str = Field(..., max_length=100, description="自选股列表名称")
    description: Optional[str] = Field(None, description="列表描述")
    stock_codes: List[str] = Field(..., min_items=1, description="股票代码列表")
    priority_level: int = Field(3, ge=1, le=5, description="优先级 (1-5, 5最高)")
    data_types: List[str] = Field(
        default=["financial", "announcements", "shareholders"],
        description="需要预热的数据类型"
    )
    schedule_time: Optional[time] = Field(None, description="自定义调度时间")
    auto_batch: bool = Field(True, description="是否参与自动批处理")

    @validator('stock_codes')
    def validate_stock_codes(cls, v):
        """验证股票代码格式"""
        for code in v:
            if not code or len(code) != 6 or not code.isdigit():
                raise ValueError(f"无效的股票代码: {code}")
        return v

    @validator('data_types')
    def validate_data_types(cls, v):
        """验证数据类型"""
        valid_types = {"financial", "announcements", "shareholders", "longhubang"}
        for data_type in v:
            if data_type not in valid_types:
                raise ValueError(f"无效的数据类型: {data_type}")
        return v

class WatchlistUpdate(BaseModel):
    """更新自选股列表请求模型"""
    watchlist_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    stock_codes: Optional[List[str]] = None
    priority_level: Optional[int] = Field(None, ge=1, le=5)
    data_types: Optional[List[str]] = None
    schedule_time: Optional[time] = None
    auto_batch: Optional[bool] = None
    is_active: Optional[bool] = None

    @validator('stock_codes')
    def validate_stock_codes(cls, v):
        if v is not None:
            for code in v:
                if not code or len(code) != 6 or not code.isdigit():
                    raise ValueError(f"无效的股票代码: {code}")
        return v

class WatchlistResponse(BaseModel):
    """自选股列表响应模型"""
    id: int
    user_id: str
    watchlist_name: str
    description: Optional[str]
    stock_codes: List[str]
    priority_level: int
    data_types: List[str]
    schedule_time: Optional[time]
    auto_batch: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WatchlistStats(BaseModel):
    """自选股使用统计模型"""
    watchlist_id: int
    user_id: str
    access_count: int
    last_accessed: Optional[datetime]
    avg_response_time: Optional[float]
    cache_hit_rate: Optional[float]
    data_quality_score: Optional[float]
    date_recorded: datetime

    class Config:
        from_attributes = True

class WatchlistBatchConfig(BaseModel):
    """批处理配置模型"""
    priority_level: int = Field(ge=1, le=5)
    schedule_time: time
    data_types: List[str]
    auto_batch: bool = True

class WatchlistBatchTrigger(BaseModel):
    """手动触发批处理请求模型"""
    force_refresh: bool = Field(False, description="是否强制刷新缓存")
    data_types: Optional[List[str]] = Field(None, description="指定要处理的数据类型")
    priority_override: Optional[int] = Field(None, ge=1, le=5, description="优先级覆盖")