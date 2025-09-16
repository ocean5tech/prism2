# Prism2 股票分析平台外部设计文档

## 📋 文档信息

- **文档版本**: v1.0
- **创建日期**: 2025-09-16
- **最后更新**: 2025-09-16
- **文档状态**: 详细设计完成
- **负责人**: 架构团队

---

## 🎯 设计目标

本文档基于商业需求、基础设施和架构设计，将Prism2系统分解为可独立开发、独立测试、独立部署的功能模块，明确定义模块间的接口契约和依赖关系。

### 设计原则
- **高内聚低耦合**: 模块内部功能紧密相关，模块间依赖最小化
- **接口标准化**: 统一的REST API接口设计
- **独立可测**: 每个模块可独立进行单元测试和集成测试
- **水平扩展**: 支持模块独立扩容和部署
- **故障隔离**: 单模块故障不影响其他模块运行

---

## 🏗️ 系统架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (Nginx)                      │
│                        Port: 80/443                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┼─────────────┐
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Frontend  │ │Stock Service│ │ RAG Service │ │  Open WebUI │
│  Module     │ │    8000     │ │    8001     │ │  (AI Mgmt)  │
│   3000      │ └─────────────┘ └─────────────┘ │    3001     │
└─────────────┘        │             │         └─────────────┘
        ┌──────────────┼─────────────┼──────────────┼──────────────┐
        │              │             │              │              │
        ▼              ▼             ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│Data Service │ │Auth Service │ │News Service │ │AI Service   │ │   (Connected │
│    8003     │ │    8004     │ │    8005     │ │   11434     │ │  to Ollama) │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
        │              │             │              │
        └──────────────┼─────────────┼──────────────┘
                       │             │
        ┌──────────────┼─────────────┼──────────────┐
        │              │             │              │
        ▼              ▼             ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ PostgreSQL  │ │    Redis    │ │  ChromaDB   │ │File Storage │
│    5432     │ │    6379     │ │    8000     │ │   MinIO     │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

---

## 📦 核心模块设计

### 1. Frontend Module - 前端展示模块

#### 模块概述
**功能**: 提供用户交互界面，包括PWA、聊天机器人、仪表板等
**技术栈**: React 18 + TypeScript + Vite + Tailwind CSS
**部署端口**: 3000 (开发) / 80,443 (生产)

#### 输入接口
```typescript
// === 股票实时行情数据 ===
interface StockRealtimeData {
  basic_info: {
    code: string;
    name: string;
    market: string; // 'SH' | 'SZ' | 'HK' | 'US'
    industry: string;
    market_cap: number;
    total_shares: number;
    float_shares: number;
  };

  price_data: {
    current_price: number;
    open_price: number;
    high_price: number;
    low_price: number;
    pre_close: number;
    change_amount: number;
    change_percent: number;
    volume: number;
    turnover: number;
    turnover_rate: number;
    timestamp: string;
  };

  market_depth: {
    bid_prices: number[]; // 买1-5价格
    bid_volumes: number[]; // 买1-5量
    ask_prices: number[]; // 卖1-5价格
    ask_volumes: number[]; // 卖1-5量
  };

  technical_indicators: {
    ma5: number;
    ma10: number;
    ma20: number;
    ma60: number;
    macd: { diff: number; dea: number; macd: number };
    rsi: number;
    kdj: { k: number; d: number; j: number };
    boll: { upper: number; middle: number; lower: number };
  };
}

// === K线图表数据 ===
interface KLineData {
  stock_code: string;
  period: '1m' | '5m' | '15m' | '30m' | '1h' | '1d' | '1w' | '1M';
  data: Array<{
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    turnover: number;
  }>;
  indicators?: {
    [key: string]: Array<number | null>; // MA, MACD等指标数据
  };
}

// === 公司基本信息 ===
interface CompanyInfo {
  basic: {
    full_name: string;
    english_name: string;
    establishment_date: string;
    listing_date: string;
    legal_representative: string;
    registered_capital: number;
    employees_count: number;
    main_business: string;
    business_scope: string;
  };

  industry_info: {
    industry_classification: string;
    industry_ranking: number;
    market_share: number;
    competitors: string[];
  };

  concept_tags: Array<{
    tag_name: string;
    tag_type: 'hot' | 'concept' | 'theme';
    relevance_score: number;
  }>;

  shareholder_structure: {
    top_shareholders: Array<{
      name: string;
      shares: number;
      percentage: number;
      nature: 'individual' | 'institution' | 'state' | 'foreign';
    }>;
    institutional_holdings: {
      total_percentage: number;
      major_institutions: string[];
    };
  };
}

// === 财务数据 ===
interface FinancialData {
  reports: Array<{
    period: string; // '2024Q3', '2024Q2'
    report_type: 'quarterly' | 'annual';
    revenue: number;
    net_profit: number;
    gross_profit_margin: number;
    net_profit_margin: number;
    roe: number; // 净资产收益率
    roa: number; // 总资产收益率
    debt_ratio: number;
    current_ratio: number;
    eps: number; // 每股收益
    bps: number; // 每股净资产
    operating_cash_flow: number;
  }>;

  valuation_metrics: {
    pe_ratio: number;
    pb_ratio: number;
    peg_ratio: number;
    ps_ratio: number;
    price_to_cash_flow: number;
  };

  industry_comparison: {
    industry_average_pe: number;
    industry_average_pb: number;
    relative_valuation: 'undervalued' | 'fairly_valued' | 'overvalued';
  };
}

// === 公告和新闻信息 ===
interface AnnouncementInfo {
  company_announcements: Array<{
    id: string;
    title: string;
    type: 'earnings' | 'dividend' | 'restructuring' | 'governance' | 'other';
    publish_date: string;
    summary: string;
    importance: 'high' | 'medium' | 'low';
    url: string;
  }>;

  regulatory_announcements: Array<{
    id: string;
    title: string;
    source: 'sse' | 'szse' | 'csrc' | 'mofcom'; // 上交所、深交所、证监会、商务部
    publish_date: string;
    summary: string;
    affected_stocks: string[];
  }>;

  dragon_tiger_list: Array<{
    date: string;
    reason: string;
    buy_seats: Array<{
      seat_name: string;
      buy_amount: number;
    }>;
    sell_seats: Array<{
      seat_name: string;
      sell_amount: number;
    }>;
  }>;
}

// === AI综合分析结果 ===
interface AIComprehensiveAnalysis {
  six_dimension_scores: {
    technical_score: number; // 0-100
    fundamental_score: number;
    news_sentiment_score: number;
    concept_heat_score: number;
    market_trend_score: number;
    capital_attention_score: number;
  };

  detailed_analysis: {
    technical_analysis: {
      trend_direction: 'bullish' | 'bearish' | 'sideways';
      support_levels: number[];
      resistance_levels: number[];
      key_indicators_summary: string;
      technical_rating: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';
      reasoning: string[];
    };

    fundamental_analysis: {
      financial_health: 'excellent' | 'good' | 'average' | 'poor';
      growth_potential: 'high' | 'medium' | 'low';
      valuation_assessment: 'undervalued' | 'fairly_valued' | 'overvalued';
      key_financial_highlights: string[];
      fundamental_rating: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';
      reasoning: string[];
    };

    news_sentiment_analysis: {
      overall_sentiment: 'very_positive' | 'positive' | 'neutral' | 'negative' | 'very_negative';
      key_news_impacts: Array<{
        news_title: string;
        impact_type: 'positive' | 'negative' | 'neutral';
        impact_magnitude: 'high' | 'medium' | 'low';
        reasoning: string;
      }>;
      sentiment_trend: 'improving' | 'stable' | 'deteriorating';
    };
  };

  investment_recommendation: {
    overall_rating: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';
    confidence_level: number; // 0-1
    target_price_range: {
      optimistic: number;
      base_case: number;
      pessimistic: number;
    };
    investment_horizon: 'short_term' | 'medium_term' | 'long_term';
    key_reasons: string[];
    risk_factors: string[];
    catalysts: string[];
  };

  reasoning_chain: Array<{
    step: number;
    description: string;
    evidence: string[];
    weight: number; // 该步骤在整体分析中的权重
  }>;
}

// === 实时新闻数据 ===
interface NewsData {
  news_items: Array<{
    id: string;
    title: string;
    summary: string;
    content: string;
    source: string;
    author: string;
    publish_time: string;
    url: string;
    related_stocks: string[];
    impact_assessment: {
      overall_impact: 'very_positive' | 'positive' | 'neutral' | 'negative' | 'very_negative';
      affected_stocks: Array<{
        stock_code: string;
        impact_level: 'high' | 'medium' | 'low';
        impact_reasoning: string;
      }>;
    };
    keywords: string[];
    category: 'market' | 'policy' | 'company' | 'industry' | 'macro' | 'international';
  }>;

  market_sentiment: {
    overall_sentiment_score: number; // -1 to 1
    sentiment_trend: 'improving' | 'stable' | 'deteriorating';
    key_themes: string[];
  };
}

// === 用户搜索建议 ===
interface SearchSuggestions {
  stocks: Array<{
    code: string;
    name: string;
    market: string;
    current_price: number;
    change_percent: number;
  }>;

  hot_stocks: Array<{
    code: string;
    name: string;
    reason: string; // 热门原因
    heat_score: number;
  }>;

  concepts: Array<{
    concept_name: string;
    related_stocks_count: number;
    recent_performance: number;
  }>;
}
```

#### 输出接口
```typescript
// === 股票搜索请求 ===
interface StockSearchRequest {
  query: string;
  query_type: 'code' | 'name' | 'pinyin' | 'concept' | 'industry';
  market_filter?: 'SH' | 'SZ' | 'HK' | 'US' | 'all';
  limit?: number;
  user_id?: string;
  session_id?: string;
}

// === Dashboard数据请求 ===
interface DashboardDataRequest {
  stock_code: string;
  data_types: Array<'realtime' | 'kline' | 'company_info' | 'financial' | 'announcements' | 'ai_analysis'>;
  kline_period?: '1d' | '1w' | '1M';
  kline_limit?: number;
  user_id?: string;
}

// === AI聊天请求 ===
interface AIAssistantRequest {
  message: string;
  session_id: string;
  context?: {
    current_stock?: string;
    conversation_history?: Array<{
      role: 'user' | 'assistant';
      content: string;
      timestamp: string;
    }>;
    user_preferences?: {
      risk_tolerance: 'conservative' | 'moderate' | 'aggressive';
      investment_horizon: 'short' | 'medium' | 'long';
      focus_areas: string[];
    };
  };
  analysis_preferences?: {
    include_technical: boolean;
    include_fundamental: boolean;
    include_news: boolean;
    detail_level: 'brief' | 'detailed' | 'comprehensive';
  };
  user_id?: string;
}

// === 用户设置和偏好 ===
interface UserPreferencesUpdate {
  user_id: string;
  preferences: {
    watchlist: string[]; // 自选股列表
    default_market: string;
    refresh_interval: number; // 秒
    chart_preferences: {
      default_period: string;
      default_indicators: string[];
      color_scheme: 'light' | 'dark' | 'auto';
    };
    notification_settings: {
      price_alerts: boolean;
      news_alerts: boolean;
      ai_insights: boolean;
      email_notifications: boolean;
    };
    ai_assistant_settings: {
      response_style: 'concise' | 'detailed' | 'educational';
      include_reasoning: boolean;
      focus_areas: string[];
    };
  };
}

// === 新闻监控配置 ===
interface NewsMonitoringConfig {
  user_id: string;
  monitoring_rules: Array<{
    rule_id?: string;
    rule_name: string;
    keywords: string[];
    stock_codes: string[];
    sources: string[];
    alert_level: 'all' | 'important' | 'critical';
    notification_methods: Array<'websocket' | 'email' | 'push'>;
    enabled: boolean;
  }>;
}

// === 实时订阅请求 ===
interface RealtimeSubscriptionRequest {
  subscription_type: 'stock_price' | 'news' | 'ai_insights' | 'market_alerts';
  targets: {
    stock_codes?: string[];
    news_keywords?: string[];
    alert_types?: string[];
  };
  user_id: string;
  session_id: string;
}

// === 历史数据查询 ===
interface HistoricalDataRequest {
  stock_code: string;
  data_type: 'price' | 'volume' | 'financial' | 'news' | 'announcements';
  start_date: string;
  end_date: string;
  granularity?: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  indicators?: string[]; // 技术指标
}

// === AI分析定制请求 ===
interface CustomAnalysisRequest {
  stock_codes: string[];
  analysis_type: 'comparative' | 'portfolio' | 'sector' | 'custom';
  focus_areas: Array<'technical' | 'fundamental' | 'news' | 'risk' | 'opportunity'>;
  time_horizon: 'short_term' | 'medium_term' | 'long_term';
  custom_prompt?: string;
  user_context?: {
    investment_goals: string;
    risk_tolerance: string;
    current_holdings: Array<{
      stock_code: string;
      shares: number;
      cost_basis: number;
    }>;
  };
  user_id: string;
}

// === 用户反馈和交互 ===
interface UserFeedback {
  feedback_type: 'ai_analysis_rating' | 'feature_request' | 'bug_report' | 'general';
  content: {
    rating?: number; // 1-5
    comments?: string;
    reference_id?: string; // 相关的分析ID或会话ID
    suggestions?: string;
  };
  user_id: string;
  timestamp: string;
}

// === 数据导出请求 ===
interface DataExportRequest {
  export_type: 'watchlist' | 'analysis_history' | 'portfolio' | 'custom';
  data_range: {
    start_date: string;
    end_date: string;
    stock_codes?: string[];
  };
  format: 'json' | 'csv' | 'excel' | 'pdf';
  include_charts?: boolean;
  user_id: string;
}
```

#### 功能需求
- ✅ **主页搜索**: Google式极简股票搜索界面
- ✅ **Dashboard**: 实时股票数据展示和K线图表
- ✅ **AI Chat**: 类ChatGPT的投资助手对话界面
- ✅ **监控中心**: 新闻源配置和市场监控设置
- ✅ **PWA支持**: 移动端离线使用和桌面安装

#### 资源需求
- **CPU**: 1核心
- **内存**: 512MB
- **磁盘**: 200MB (构建产物)
- **依赖**: Nginx (生产环境)

#### 测试策略
- **单元测试**: Jest + React Testing Library
- **E2E测试**: Playwright
- **性能测试**: Lighthouse CI
- **兼容性测试**: 多浏览器和移动设备测试

---

### 2. Stock Analysis Service - 股票分析服务

#### 模块概述
**功能**: 股票数据处理、技术分析、基本面分析的核心业务逻辑
**技术栈**: FastAPI + Python 3.12
**部署端口**: 8000

#### 输入接口
```python
# REST API 端点
POST /api/stock/search
{
    "query": "000001",
    "query_type": "code"
}

POST /api/stock/analysis
{
    "stock_code": "000001",
    "analysis_types": ["technical", "fundamental", "news"],
    "timeframe": "1d"
}

GET /api/stock/{stock_code}/realtime
```

#### 输出接口
```python
# 股票搜索结果
class StockSearchResponse(BaseModel):
    results: List[StockInfo]
    total: int
    query_time: float

class StockInfo(BaseModel):
    code: str
    name: str
    market: str
    industry: str
    current_price: float
    change_percent: float

# 分析结果
class AnalysisResponse(BaseModel):
    stock_code: str
    analysis_data: Dict[str, Any]
    ai_insights: List[str]
    risk_assessment: RiskAssessment
    timestamp: datetime
```

#### 功能需求
- ✅ **股票搜索**: 支持代码、名称、拼音等多种查询方式
- ✅ **实时数据**: 提供股价、成交量等实时行情数据
- ✅ **技术分析**: MA、MACD、RSI等技术指标计算
- ✅ **基本面分析**: 财报数据解读和估值计算
- ✅ **综合评分**: AI驱动的六维度评价体系

#### 资源需求
- **CPU**: 2核心
- **内存**: 2GB
- **磁盘**: 1GB
- **依赖**: PostgreSQL, Redis, AI Service

#### 外部依赖
```yaml
dependencies:
  - data_service: "获取原始股票数据"
  - ai_service: "AI分析和推理"
  - auth_service: "用户认证和权限"
  - postgresql: "股票数据存储"
  - redis: "缓存和会话"
```

#### 测试策略
- **单元测试**: pytest + mock外部API
- **集成测试**: testcontainers + 真实数据库
- **性能测试**: 并发请求压力测试
- **API测试**: OpenAPI自动化测试

---

### 3. RAG Service - 检索增强生成服务

#### 模块概述
**功能**: 向量检索、语义搜索、上下文增强的RAG核心服务
**技术栈**: FastAPI + LangChain + ChromaDB
**部署端口**: 8001

#### 输入接口
```python
POST /api/rag/search
{
    "query": "平安银行最新财报分析",
    "stock_code": "000001",
    "search_type": "semantic",
    "limit": 5
}

POST /api/rag/embed
{
    "documents": [
        {
            "id": "doc_001",
            "content": "文档内容",
            "metadata": {"stock_code": "000001", "doc_type": "report"}
        }
    ]
}
```

#### 输出接口
```python
class RAGSearchResponse(BaseModel):
    results: List[DocumentMatch]
    query_embedding: List[float]
    search_time: float

class DocumentMatch(BaseModel):
    document_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]

class RAGContextResponse(BaseModel):
    context: str
    sources: List[str]
    relevance_score: float
```

#### 功能需求
- ✅ **语义搜索**: 基于bge-large-zh-v1.5的中文向量检索
- ✅ **文档嵌入**: 研报、新闻、公告的向量化存储
- ✅ **上下文增强**: 为AI模型提供相关背景信息
- ✅ **相似度计算**: 文档间语义相似度分析

#### 资源需求
- **CPU**: 2核心
- **内存**: 3GB (向量模型需求)
- **磁盘**: 2GB (模型文件 + 向量数据)
- **依赖**: ChromaDB, 向量模型文件

#### 外部依赖
```yaml
dependencies:
  - chromadb: "向量数据存储"
  - news_service: "文档数据来源"
  - ai_service: "向量模型推理"
```

#### 测试策略
- **单元测试**: 向量计算和检索逻辑测试
- **集成测试**: ChromaDB连接和数据一致性
- **性能测试**: 向量检索速度和准确率
- **质量测试**: 语义搜索结果相关性评估

---

### 4. Data Service - 数据采集服务

#### 模块概述
**功能**: 外部数据源集成、数据清洗、实时数据推送
**技术栈**: FastAPI + Scrapy + APScheduler
**部署端口**: 8003

#### 输入接口
```python
POST /api/data/configure
{
    "source_type": "rss",
    "source_url": "https://finance.sina.com.cn/rss/",
    "poll_interval": 300,
    "keywords": ["平安银行", "000001"]
}

GET /api/data/stocks/{stock_code}/ohlcv?period=1d&limit=100
```

#### 输出接口
```python
class OHLCVData(BaseModel):
    stock_code: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: float

class NewsData(BaseModel):
    id: str
    title: str
    content: str
    source: str
    publish_time: datetime
    stock_codes: List[str]
    sentiment: str  # positive/negative/neutral
```

#### 功能需求
- ✅ **实时数据获取**: 股价、成交量等市场数据
- ✅ **新闻爬取**: 多源新闻、公告、研报采集
- ✅ **数据清洗**: 格式标准化和质量验证
- ✅ **定时任务**: 基于APScheduler的定时数据更新
- ✅ **数据推送**: WebSocket实时数据推送

#### 资源需求
- **CPU**: 2核心
- **内存**: 1.5GB
- **磁盘**: 1GB
- **网络**: 重要 (大量外部API调用)

#### 外部依赖
```yaml
dependencies:
  - postgresql: "原始数据存储"
  - redis: "缓存和队列"
  - external_apis: "第三方数据源"
```

#### 测试策略
- **单元测试**: 数据解析和清洗逻辑
- **集成测试**: 外部API连接稳定性
- **负载测试**: 大量数据处理性能
- **数据质量测试**: 数据准确性和完整性验证

---

### 5. Authentication Service - 认证授权服务

#### 模块概述
**功能**: 用户认证、权限管理、会话控制
**技术栈**: FastAPI + JWT + Redis
**部署端口**: 8004

#### 输入接口
```python
POST /api/auth/login
{
    "username": "user@example.com",
    "password": "hashed_password"
}

POST /api/auth/register
{
    "email": "user@example.com",
    "password": "password",
    "plan": "standard"
}

GET /api/auth/profile
Headers: Authorization: Bearer <jwt_token>
```

#### 输出接口
```python
class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: UserInfo

class UserInfo(BaseModel):
    user_id: str
    email: str
    plan: str  # free/standard/professional/enterprise
    permissions: List[str]
    created_at: datetime
```

#### 功能需求
- ✅ **用户注册/登录**: 邮箱/密码认证
- ✅ **JWT令牌管理**: 访问令牌和刷新令牌
- ✅ **权限控制**: 基于用户套餐的功能权限
- ✅ **会话管理**: 用户会话状态和超时控制
- ✅ **安全防护**: 限流、防暴力破解

#### 资源需求
- **CPU**: 1核心
- **内存**: 1GB
- **磁盘**: 500MB
- **依赖**: Redis, PostgreSQL

#### 测试策略
- **单元测试**: JWT生成和验证逻辑
- **安全测试**: 密码加密和权限验证
- **性能测试**: 高并发认证请求
- **渗透测试**: 常见安全漏洞检测

---

### 6. News Monitoring Service - 新闻监控服务

#### 模块概述
**功能**: RSS源管理、新闻分析、实时推送
**技术栈**: FastAPI + Celery + RSS解析
**部署端口**: 8005

#### 输入接口
```python
POST /api/news/sources
{
    "name": "新浪财经",
    "url": "https://finance.sina.com.cn/rss/",
    "type": "rss",
    "poll_interval": 300,
    "enabled": true
}

POST /api/news/keywords
{
    "user_id": "user_123",
    "keywords": ["平安银行", "金融科技"],
    "stock_codes": ["000001"]
}
```

#### 输出接口
```python
class NewsItem(BaseModel):
    id: str
    title: str
    summary: str
    content: str
    source: str
    publish_time: datetime
    url: str
    impact_score: float  # 0-1
    affected_stocks: List[str]
    sentiment: str

class NewsAlert(BaseModel):
    news_id: str
    user_id: str
    alert_type: str  # email/push/websocket
    impact_level: str  # low/medium/high
    message: str
```

#### 功能需求
- ✅ **RSS源管理**: 添加、删除、测试RSS源
- ✅ **智能分析**: AI判断新闻对股票的影响
- ✅ **关键词监控**: 用户自定义关键词跟踪
- ✅ **实时推送**: WebSocket/邮件/短信推送
- ✅ **多语言处理**: 外文新闻自动翻译

#### 资源需求
- **CPU**: 2核心
- **内存**: 2GB
- **磁盘**: 2GB
- **依赖**: Redis, AI Service

#### 测试策略
- **单元测试**: RSS解析和新闻分析逻辑
- **集成测试**: 多个RSS源同时监控
- **性能测试**: 大量新闻处理能力
- **准确性测试**: 新闻影响判断准确率

---

### 7. Open WebUI - AI模型管理界面

#### 模块概述
**功能**: AI模型管理界面，支持多模型切换、Prompt工程、对话测试
**技术栈**: Open WebUI + Docker + Ollama集成
**部署端口**: 3001

#### 输入接口
```python
# Web界面操作 (通过浏览器访问)
# http://localhost:3001

# 模型管理
- 模型列表查看: GET /api/models
- 模型切换: POST /api/models/switch
- 对话创建: POST /api/chats
- Prompt测试: POST /api/generate

# 用户管理
- 用户登录: POST /auth/signin
- 设置管理: POST /api/settings
```

#### 输出接口
```python
# 与Ollama后端通信
class ModelSwitchRequest(BaseModel):
    model_name: str  # "qwen2.5:7b" | "deepseek-coder:1.3b"

class ChatRequest(BaseModel):
    message: str
    model: str
    system_prompt: str
    temperature: float
    max_tokens: int

class ModelInfo(BaseModel):
    name: str
    size: str
    modified_at: datetime
    digest: str
    status: str  # "loaded" | "unloaded"
```

#### 功能需求
- ✅ **模型管理**: 查看、加载、卸载AI模型
- ✅ **多模型切换**: 在Qwen2.5-7B和DeepSeek-Coder之间切换
- ✅ **对话测试**: 直接测试AI模型的对话能力
- ✅ **Prompt工程**: 系统提示词设计和测试
- ✅ **对话历史**: 保存和管理对话记录
- ✅ **用户管理**: 支持多用户访问和权限控制

#### 资源需求
- **CPU**: 1核心
- **内存**: 200MB
- **磁盘**: 100MB
- **依赖**: Ollama (11434端口)

#### 外部依赖
```yaml
dependencies:
  - ollama: "AI模型后端服务"
  - models: "qwen2.5:7b, deepseek-coder:1.3b"
```

#### 测试策略
- **功能测试**: 模型切换和对话功能
- **界面测试**: Web UI响应性和兼容性
- **集成测试**: 与Ollama服务的连接稳定性
- **用户测试**: 多用户并发访问测试

---

### 8. AI Service - AI模型服务

#### 模块概述
**功能**: 大语言模型推理、文本生成、智能分析
**技术栈**: Ollama + Qwen2.5-7B + API封装
**部署端口**: 11434

#### 输入接口
```python
POST /api/ai/generate
{
    "prompt": "分析平安银行的投资价值",
    "context": "相关背景信息",
    "model": "qwen2.5:7b",
    "max_tokens": 1000,
    "temperature": 0.7
}

POST /api/ai/embed
{
    "text": "需要向量化的文本",
    "model": "bge-large-zh-v1.5"
}
```

#### 输出接口
```python
class AIGenerateResponse(BaseModel):
    generated_text: str
    model_used: str
    tokens_used: int
    generation_time: float
    confidence_score: float

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    model_used: str
    text_length: int
    embedding_time: float
```

#### 功能需求
- ✅ **文本生成**: 投资分析报告生成
- ✅ **多模型支持**: Qwen2.5-7B, DeepSeek-Coder等
- ✅ **向量化服务**: 中文文本向量嵌入
- ✅ **模型管理**: 动态加载/卸载模型
- ✅ **推理优化**: 批处理和缓存策略

#### 资源需求
- **CPU**: 4核心
- **内存**: 8GB (大模型需求)
- **磁盘**: 6GB (模型文件)
- **GPU**: 可选 (推理加速)

#### 测试策略
- **单元测试**: API接口和参数验证
- **性能测试**: 推理速度和并发能力
- **质量测试**: 生成文本质量和相关性
- **压力测试**: 长时间连续推理稳定性

---

## 🔌 接口设计规范

### REST API 统一规范

#### 请求格式
```http
POST /api/{service}/{resource}
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
    "data": "请求数据",
    "timestamp": "2025-09-16T10:00:00Z",
    "request_id": "uuid"
}
```

#### 响应格式
```json
{
    "success": true,
    "data": {},
    "message": "Success",
    "timestamp": "2025-09-16T10:00:01Z",
    "request_id": "uuid",
    "execution_time": 0.123
}
```

#### 错误响应
```json
{
    "success": false,
    "error": {
        "code": "STOCK_NOT_FOUND",
        "message": "Stock code 000001 not found",
        "details": "Additional error details"
    },
    "timestamp": "2025-09-16T10:00:01Z",
    "request_id": "uuid"
}
```

### WebSocket 实时通信

#### 连接格式
```javascript
// 前端连接
const ws = new WebSocket('ws://localhost:8000/ws/stock-data');

// 认证消息
ws.send(JSON.stringify({
    type: 'auth',
    token: 'jwt_token'
}));

// 订阅股票数据
ws.send(JSON.stringify({
    type: 'subscribe',
    data: {
        stock_codes: ['000001', '000002'],
        data_types: ['price', 'volume']
    }
}));
```

#### 推送格式
```json
{
    "type": "stock_update",
    "data": {
        "stock_code": "000001",
        "price": 12.34,
        "change": 0.05,
        "volume": 1000000,
        "timestamp": "2025-09-16T10:00:00Z"
    }
}
```

---

## 🔄 模块间依赖关系

### 依赖图
```mermaid
graph TD
    A[Frontend Module] --> B[Stock Service]
    A --> C[Auth Service]
    A --> F[News Service]

    B --> D[Data Service]
    B --> E[RAG Service]
    B --> G[AI Service]
    B --> C

    E --> H[ChromaDB]
    E --> G

    D --> I[PostgreSQL]
    D --> J[Redis]

    F --> G
    F --> J

    C --> I
    C --> J

    G --> K[Ollama]
    L[Open WebUI] --> K[Ollama]
```

### 启动顺序
1. **基础设施层**: PostgreSQL, Redis, ChromaDB, Ollama
2. **核心服务层**: Auth Service, AI Service
3. **业务服务层**: Data Service, RAG Service, News Service
4. **聚合服务层**: Stock Service
5. **展示层**: Frontend Module, Open WebUI
6. **网关层**: Nginx

---

## 📊 性能指标要求

### 响应时间要求
| 模块 | 接口类型 | 目标响应时间 | 最大响应时间 |
|------|----------|--------------|--------------|
| Stock Service | 股票查询 | < 500ms | < 2s |
| AI Service | 文本生成 | < 2s | < 10s |
| RAG Service | 语义搜索 | < 1s | < 3s |
| Data Service | 实时数据 | < 200ms | < 1s |
| Auth Service | 登录验证 | < 100ms | < 500ms |

### 并发能力要求
| 模块 | 并发用户 | QPS | 内存使用 |
|------|----------|-----|----------|
| Frontend | 10,000+ | N/A | 512MB |
| Stock Service | 1,000+ | 500+ | 2GB |
| AI Service | 100+ | 50+ | 8GB |
| RAG Service | 500+ | 200+ | 3GB |
| Data Service | 200+ | 100+ | 1.5GB |
| Open WebUI | 50+ | N/A | 200MB |

---

## 🧪 测试策略

### 单元测试覆盖率要求
- **代码覆盖率**: ≥ 80%
- **分支覆盖率**: ≥ 70%
- **关键模块**: ≥ 90% (Auth, Stock Analysis, AI)

### 集成测试策略
```yaml
integration_tests:
  - name: "Stock Data Flow"
    modules: [Data Service, Stock Service, Frontend]
    scenario: "完整的股票查询和展示流程"

  - name: "AI Analysis Pipeline"
    modules: [RAG Service, AI Service, Stock Service]
    scenario: "RAG增强的AI分析生成"

  - name: "Real-time Updates"
    modules: [Data Service, Stock Service, Frontend]
    scenario: "实时数据推送和前端更新"
```

### 性能测试计划
```yaml
performance_tests:
  - name: "Load Testing"
    tool: "K6"
    duration: "10min"
    users: "1000"
    ramp_up: "2min"

  - name: "Stress Testing"
    tool: "JMeter"
    max_users: "5000"
    duration: "30min"

  - name: "AI Model Performance"
    metrics: ["tokens/second", "memory_usage", "gpu_utilization"]
    models: ["qwen2.5:7b", "deepseek-coder:1.3b"]
```

---

## 📦 部署配置

### Docker Compose 模块配置
```yaml
version: '3.8'

services:
  # Frontend Module
  frontend:
    image: prism2/frontend:latest
    ports: ["3000:3000"]
    environment:
      - API_BASE_URL=http://nginx
    depends_on: [nginx]

  # Open WebUI (AI Management)
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports: ["3001:8080"]
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on: [ollama]
    volumes:
      - ./open-webui:/app/backend/data

  # Stock Service
  stock-service:
    image: prism2/stock-service:latest
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/prism2
      - REDIS_URL=redis://redis:6379/0
      - AI_SERVICE_URL=http://ollama:11434
    depends_on: [postgres, redis, ollama]

  # RAG Service
  rag-service:
    image: prism2/rag-service:latest
    ports: ["8001:8001"]
    environment:
      - CHROMADB_URL=http://chromadb:8000
      - AI_SERVICE_URL=http://ollama:11434
    depends_on: [chromadb, ollama]
    volumes:
      - ./models:/app/models
```

### 环境配置模板
```bash
# .env.production
DATABASE_URL=postgresql://user:pass@postgres:5432/prism2
REDIS_URL=redis://redis:6379/0
CHROMADB_URL=http://chromadb:8000
AI_SERVICE_URL=http://ollama:11434

# JWT配置
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# 外部API配置
STOCK_API_KEY=your-api-key
NEWS_API_KEY=your-api-key

# 性能配置
MAX_WORKERS=4
CACHE_TTL=300
AI_MAX_TOKENS=2000
```

---

## 🔧 开发工具链

### 代码质量工具
```yaml
linting:
  python: ["black", "isort", "flake8", "mypy"]
  typescript: ["eslint", "prettier", "tsc"]

testing:
  python: ["pytest", "pytest-cov", "pytest-asyncio"]
  typescript: ["jest", "testing-library", "playwright"]

documentation:
  api: ["fastapi-docs", "redoc"]
  code: ["sphinx", "typedoc"]
```

### CI/CD Pipeline
```yaml
pipeline:
  stages:
    - lint: "代码质量检查"
    - test: "单元测试和集成测试"
    - build: "Docker镜像构建"
    - security: "安全扫描"
    - deploy: "分环境部署"

  quality_gates:
    - test_coverage: ">= 80%"
    - security_scan: "no_high_vulnerabilities"
    - performance: "response_time < 2s"
```

---

## 📝 附录

### 相关文档
- [商业需求文档](./business_requirements.md)
- [技术架构设计](./architecture-design.md)
- [基础设施清单](./基础设施.md)
- [经验教训文档](./LessonsLearned.md)

### API接口清单
```
Stock Service APIs (Port 8000):
├── GET    /api/stock/search
├── GET    /api/stock/{code}/realtime
├── POST   /api/stock/analysis
├── GET    /api/stock/{code}/history
└── WS     /ws/stock-data

RAG Service APIs (Port 8001):
├── POST   /api/rag/search
├── POST   /api/rag/embed
├── GET    /api/rag/documents
└── DELETE /api/rag/documents/{id}

Auth Service APIs (Port 8004):
├── POST   /api/auth/login
├── POST   /api/auth/register
├── POST   /api/auth/refresh
├── GET    /api/auth/profile
└── POST   /api/auth/logout

Data Service APIs (Port 8003):
├── GET    /api/data/stocks/{code}/ohlcv
├── POST   /api/data/sources
├── GET    /api/data/news
└── WS     /ws/realtime-data

News Service APIs (Port 8005):
├── POST   /api/news/sources
├── GET    /api/news/feed
├── POST   /api/news/keywords
└── WS     /ws/news-alerts

AI Service APIs (Port 11434):
├── POST   /api/generate
├── POST   /api/embeddings
├── GET    /api/tags
└── POST   /api/pull

Open WebUI (Port 3001):
├── GET    /api/models
├── POST   /api/chats
├── POST   /auth/signin
└── POST   /api/settings
```

### 变更记录
| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| v1.0 | 2025-09-16 | 初始外部设计文档创建 | 架构团队 |

---

*本文档为Prism2项目的详细外部设计规范，为各模块独立开发提供标准化接口定义和依赖关系说明。*