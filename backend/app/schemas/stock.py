"""
�hpn�Pydantic Schema
��01-�����.md�I�API͔<
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel


# === �@�h�o ===
class StockBase(BaseModel):
    code: str
    name: str
    market: str
    industry: Optional[str] = None


class StockInfo(StockBase):
    """�h�@�o"""
    market_cap: Optional[int] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None


# === ���<pn ===
class RealtimeData(BaseModel):
    """���<pn"""
    current_price: float
    change_amount: float
    change_percent: float
    volume: int
    turnover: float
    high: float
    low: float
    open: float
    timestamp: datetime


# === K�pn ===
class KLineItem(BaseModel):
    """UaK�pn"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class KLineData(BaseModel):
    """K�pn�"""
    period: str
    data: List[KLineItem]


# === "�pn ===
class FinancialData(BaseModel):
    """"�pn"""
    latest_quarter: str
    revenue: Optional[int] = None
    net_profit: Optional[int] = None
    roe: Optional[float] = None
    gross_margin: Optional[float] = None
    debt_ratio: Optional[float] = None


# === ��pn ===
class NewsItem(BaseModel):
    """��a�"""
    title: str
    summary: Optional[str] = None
    publish_time: datetime
    sentiment_score: Optional[float] = None
    source: Optional[str] = None
    url: Optional[str] = None


# === lJpn ===
class AnnouncementItem(BaseModel):
    """lJa�"""
    title: str
    type: Optional[str] = None
    publish_date: date
    url: Optional[str] = None


# === �N�pn ===
class LongHuBangData(BaseModel):
    """�N�pn"""
    trade_date: date
    rank_reason: Optional[str] = None
    buy_amount: Optional[int] = None
    sell_amount: Optional[int] = None
    net_amount: Optional[int] = None


# === AI�pn ===
class SixDimensionScores(BaseModel):
    """m���"""
    growth: float
    profitability: float
    risk: float
    valuation: float
    technical: float
    market_sentiment: float


class AIAnalysis(BaseModel):
    """AI�Ӝ"""
    analysis_type: str
    six_dimension_scores: SixDimensionScores
    investment_recommendation: str
    confidence_level: float
    summary: str


# === Dashboard�B/͔ ===
class DashboardRequest(BaseModel):
    """Dashboardpn�B"""
    stock_code: str
    data_types: List[str]  # ["basic_info", "realtime", "kline", "financial", "news", "announcements", "longhubang", "ai_analysis"]


class DashboardData(BaseModel):
    """Dashboard�tpn"""
    basic_info: Optional[StockInfo] = None
    realtime: Optional[RealtimeData] = None
    kline: Optional[KLineData] = None
    financial: Optional[FinancialData] = None
    news: Optional[List[NewsItem]] = None
    announcements: Optional[List[AnnouncementItem]] = None
    longhubang: Optional[LongHuBangData] = None
    ai_analysis: Optional[AIAnalysis] = None


class DashboardResponse(BaseModel):
    """Dashboard API͔"""
    success: bool
    stock_code: str
    timestamp: datetime
    data: DashboardData


# === "�B/͔ ===
class StockSearchRequest(BaseModel):
    """�h"�B"""
    query: str
    limit: Optional[int] = 10


class StockSearchItem(BaseModel):
    """"Ӝa�"""
    code: str
    name: str
    market: str
    industry: Optional[str] = None


class StockSearchResponse(BaseModel):
    """�h"͔"""
    success: bool
    query: str
    results: List[StockSearchItem]
    total: int


# === (͔ ===
class HealthResponse(BaseModel):
    """e���͔"""
    status: str
    timestamp: datetime
    version: str


class ErrorResponse(BaseModel):
    """�͔"""
    success: bool = False
    error_code: str
    error_message: str
    timestamp: datetime