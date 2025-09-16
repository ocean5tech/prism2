# News Service - 内部设计文档

## 📋 基本信息

- **模块名称**: News Service (新闻监控服务)
- **技术栈**: FastAPI + Celery + RSS解析 + BeautifulSoup
- **部署端口**: 8005
- **依据**: 外部设计文档规范

---

## 📁 文件结构和权限

```
/home/wyatt/prism2/news-service/
├── app/                                  # 应用源代码 (755)
│   ├── __init__.py                       # (644)
│   ├── main.py                           # FastAPI应用入口 (644)
│   ├── core/                             # 核心配置 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── config.py                     # 环境配置 (644)
│   │   └── dependencies.py               # 依赖注入 (644)
│   ├── api/                              # API路由 (755)
│   │   ├── __init__.py                   # (644)
│   │   └── v1/                           # API版本1 (755)
│   │       ├── __init__.py               # (644)
│   │       ├── news.py                   # 新闻相关端点 (644)
│   │       ├── sources.py                # RSS源管理端点 (644)
│   │       ├── alerts.py                 # 推送管理端点 (644)
│   │       └── health.py                 # 健康检查端点 (644)
│   ├── services/                         # 业务服务层 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── rss_service.py                # RSS采集服务 (644)
│   │   ├── news_analyzer.py              # 新闻分析服务 (644)
│   │   ├── alert_service.py              # 推送服务 (644)
│   │   ├── keyword_service.py            # 关键词监控服务 (644)
│   │   └── translation_service.py        # 翻译服务 (644)
│   ├── crawlers/                         # 新闻爬虫模块 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── base_crawler.py               # 爬虫基类 (644)
│   │   ├── rss_crawler.py                # RSS爬虫 (644)
│   │   ├── sina_crawler.py               # 新浪财经爬虫 (644)
│   │   ├── eastmoney_crawler.py          # 东方财富爬虫 (644)
│   │   └── cninfo_crawler.py             # 巨潮资讯爬虫 (644)
│   ├── models/                           # 数据模型 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── requests.py                   # 请求模型 (644)
│   │   ├── responses.py                  # 响应模型 (644)
│   │   └── database.py                   # 数据库模型 (644)
│   ├── tasks/                            # Celery异步任务 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── rss_tasks.py                  # RSS采集任务 (644)
│   │   ├── analysis_tasks.py             # 分析任务 (644)
│   │   └── notification_tasks.py         # 通知任务 (644)
│   └── utils/                            # 工具函数 (755)
│       ├── __init__.py                   # (644)
│       ├── text_processor.py             # 文本处理工具 (644)
│       ├── sentiment_analyzer.py         # 情感分析工具 (644)
│       ├── stock_extractor.py            # 股票信息提取 (644)
│       └── notification_helper.py        # 通知工具 (644)
├── requirements.txt                      # Python依赖 (644)
├── Dockerfile                           # 容器化配置 (644)
└── .env                                 # 环境变量 (600)
```

---

## 🗄️ 数据库表结构 (PostgreSQL + TimescaleDB)

### RSS源配置表 (rss_sources)
```sql
CREATE TABLE rss_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,             -- RSS源名称
    url TEXT UNIQUE NOT NULL,               -- RSS URL
    source_type VARCHAR(50) DEFAULT 'rss',  -- 类型: rss/atom/json
    category VARCHAR(100),                  -- 分类: 财经/公告/研报等
    language VARCHAR(10) DEFAULT 'zh',      -- 语言: zh/en
    poll_interval INTEGER DEFAULT 300,     -- 轮询间隔(秒)
    enabled BOOLEAN DEFAULT true,          -- 是否启用
    last_poll_time TIMESTAMP,              -- 最后轮询时间
    last_success_time TIMESTAMP,           -- 最后成功时间
    success_count INTEGER DEFAULT 0,       -- 成功次数
    error_count INTEGER DEFAULT 0,         -- 错误次数
    error_message TEXT,                     -- 最后错误信息
    config JSONB DEFAULT '{}',              -- 扩展配置
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 索引
    INDEX idx_rss_sources_enabled (enabled),
    INDEX idx_rss_sources_poll_time (last_poll_time),
    INDEX idx_rss_sources_category (category)
);

-- 预设RSS源数据
INSERT INTO rss_sources (name, url, category, language) VALUES
('新浪财经', 'https://finance.sina.com.cn/rss/', '财经新闻', 'zh'),
('东方财富', 'http://feed.eastmoney.com/rss', '财经新闻', 'zh'),
('上交所公告', 'http://www.sse.com.cn/disclosure/listedinfo/announcement/rss.xml', '交易所公告', 'zh'),
('深交所公告', 'http://www.szse.cn/api/report/index/rss', '交易所公告', 'zh');
```

### 新闻数据表 (news_items) - TimescaleDB优化
```sql
CREATE TABLE news_items (
    id BIGSERIAL,
    source_id INTEGER REFERENCES rss_sources(id),
    title TEXT NOT NULL,                    -- 新闻标题
    summary TEXT,                           -- 新闻摘要
    content TEXT,                           -- 新闻正文
    url TEXT UNIQUE NOT NULL,               -- 原始URL
    source_name VARCHAR(200),               -- 来源名称
    author VARCHAR(200),                    -- 作者
    publish_time TIMESTAMP NOT NULL,        -- 发布时间
    language VARCHAR(10) DEFAULT 'zh',      -- 语言

    -- AI分析结果
    sentiment VARCHAR(20),                  -- 情感: positive/negative/neutral
    impact_score DECIMAL(3,2),              -- 影响评分 0-1
    affected_stocks TEXT[],                 -- 影响的股票代码数组
    keywords TEXT[],                        -- 提取的关键词
    category VARCHAR(100),                  -- 新闻分类

    -- 处理状态
    processed BOOLEAN DEFAULT false,        -- 是否已处理
    analysis_version INTEGER DEFAULT 1,    -- 分析版本

    -- 元数据
    raw_data JSONB,                        -- 原始数据
    metadata JSONB DEFAULT '{}',           -- 扩展元数据
    created_at TIMESTAMP DEFAULT NOW(),

    -- TimescaleDB分区键
    PRIMARY KEY (publish_time, id)
);

-- 创建TimescaleDB超表
SELECT create_hypertable('news_items', 'publish_time', chunk_time_interval => INTERVAL '1 day');

-- 索引优化
CREATE INDEX idx_news_items_source ON news_items(source_id, publish_time);
CREATE INDEX idx_news_items_stocks ON news_items USING GIN(affected_stocks);
CREATE INDEX idx_news_items_sentiment ON news_items(sentiment, publish_time);
CREATE INDEX idx_news_items_impact ON news_items(impact_score DESC, publish_time);
CREATE INDEX idx_news_items_url_hash ON news_items(md5(url));
```

### 用户关键词监控表 (user_keywords)
```sql
CREATE TABLE user_keywords (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,                 -- 用户ID
    keyword VARCHAR(100) NOT NULL,         -- 关键词
    keyword_type VARCHAR(50),              -- 类型: stock_code/company_name/concept
    stock_codes TEXT[],                    -- 关联股票代码
    alert_types VARCHAR(50)[] DEFAULT ARRAY['websocket'], -- 推送方式
    impact_threshold DECIMAL(3,2) DEFAULT 0.5, -- 影响阈值
    enabled BOOLEAN DEFAULT true,          -- 是否启用
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 约束和索引
    UNIQUE(user_id, keyword),
    INDEX idx_user_keywords_user_id (user_id),
    INDEX idx_user_keywords_keyword (keyword),
    INDEX idx_user_keywords_stocks (stock_codes)
);
```

### 推送记录表 (news_alerts)
```sql
CREATE TABLE news_alerts (
    id BIGSERIAL PRIMARY KEY,
    news_id BIGINT,                        -- 关联新闻ID
    user_id UUID NOT NULL,                 -- 用户ID
    alert_type VARCHAR(20) NOT NULL,       -- 推送类型: email/websocket/sms
    impact_level VARCHAR(20),              -- 影响级别: low/medium/high
    message TEXT,                          -- 推送消息内容
    metadata JSONB DEFAULT '{}',           -- 推送元数据

    -- 状态管理
    status VARCHAR(20) DEFAULT 'pending',  -- 状态: pending/sent/failed
    sent_at TIMESTAMP,                     -- 发送时间
    error_message TEXT,                    -- 错误信息
    retry_count INTEGER DEFAULT 0,        -- 重试次数

    created_at TIMESTAMP DEFAULT NOW(),

    -- 索引
    INDEX idx_news_alerts_user (user_id, created_at),
    INDEX idx_news_alerts_status (status),
    INDEX idx_news_alerts_type (alert_type)
);
```

### 新闻质量评估表 (news_quality_metrics)
```sql
CREATE TABLE news_quality_metrics (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES rss_sources(id),
    metric_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- 质量指标
    total_articles INTEGER DEFAULT 0,      -- 总文章数
    duplicate_articles INTEGER DEFAULT 0,  -- 重复文章数
    analysis_success_rate DECIMAL(5,2),    -- 分析成功率
    avg_impact_score DECIMAL(3,2),         -- 平均影响评分
    sentiment_distribution JSONB,          -- 情感分布统计

    -- 时效性指标
    avg_processing_time INTERVAL,          -- 平均处理时间
    delay_from_publish INTERVAL,           -- 发布延迟时间

    updated_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    UNIQUE(source_id, metric_date)
);
```

---

## 🔌 API接口定义 (严格按照外部设计)

### 基础配置
```python
# 服务配置
NEWS_SERVICE_PORT = int(os.getenv('NEWS_SERVICE_PORT', '8005'))
RSS_POLL_INTERVAL = int(os.getenv('RSS_POLL_INTERVAL', '300'))
MAX_CONCURRENT_CRAWLERS = int(os.getenv('MAX_CONCURRENT_CRAWLERS', '3'))
NEWS_RETENTION_DAYS = int(os.getenv('NEWS_RETENTION_DAYS', '30'))
```

### API1: RSS源管理 (对接外部设计接口)
- **URL**: `POST /api/news/sources`
- **输入参数**: 严格按照外部设计的RSS源配置请求
  ```python
  class RSSSourceCreateRequest(BaseModel):
      name: str                            # RSS源名称
      url: str                             # RSS URL
      type: str = "rss"                   # 类型: rss/atom/json
      poll_interval: int = 300            # 轮询间隔(秒)
      enabled: bool = True                # 是否启用
      category: Optional[str] = None      # 分类
      language: str = "zh"                # 语言
      config: Optional[Dict[str, Any]] = None  # 扩展配置
  ```
- **输出结果**: 外部设计的源创建响应
  ```python
  class RSSSourceResponse(BaseModel):
      source_id: int                      # 源ID
      name: str                           # 源名称
      url: str                            # RSS URL
      status: str                         # 状态: active/inactive/error
      last_poll_time: Optional[datetime]  # 最后轮询时间
      article_count: int                  # 文章总数
      success_rate: float                 # 成功率
  ```
- **资源**: rss_sources表、RSS验证服务
- **逻辑**: 验证RSS URL有效性，检查URL重复性，创建RSS源记录，启动轮询任务，返回源配置状态和统计信息

### API2: 用户关键词监控配置 (对接外部设计接口)
- **URL**: `POST /api/news/keywords`
- **输入参数**: 外部设计的关键词监控请求
  ```python
  class NewsMonitoringConfig(BaseModel):
      user_id: str                        # 用户ID
      keywords: List[str]                 # 关键词列表
      stock_codes: Optional[List[str]] = None  # 关联股票代码
      alert_types: List[str] = ["websocket"]   # 推送方式
      impact_threshold: float = 0.5       # 影响阈值
      language_filter: List[str] = ["zh"] # 语言过滤
  ```
- **输出结果**: 监控配置响应
  ```python
  class MonitoringConfigResponse(BaseModel):
      config_id: str                      # 配置ID
      active_keywords: List[str]          # 激活的关键词
      monitoring_status: str              # 监控状态
      estimated_alerts_per_day: int      # 预估每日推送数
  ```
- **资源**: user_keywords表、关键词匹配引擎
- **逻辑**: 验证用户权限，创建或更新关键词监控规则，配置推送偏好，启动实时监控，估算推送频率并返回配置状态

### API3: 新闻数据查询 (对接RAG Service)
- **URL**: `GET /api/news/search`
- **输入参数**: 新闻搜索请求
  ```python
  class NewsSearchRequest(BaseModel):
      query: Optional[str] = None         # 搜索关键词
      stock_codes: Optional[List[str]] = None  # 股票代码过滤
      sentiment: Optional[str] = None     # 情感过滤
      impact_min: Optional[float] = None  # 最小影响评分
      start_date: Optional[str] = None    # 开始日期
      end_date: Optional[str] = None      # 结束日期
      limit: int = 20                     # 返回数量
      offset: int = 0                     # 偏移量
  ```
- **输出结果**: 外部设计的NewsItem列表
  ```python
  class NewsItem(BaseModel):
      id: str
      title: str
      summary: str
      content: str
      source: str
      publish_time: datetime
      url: str
      impact_score: float                 # 0-1
      affected_stocks: List[str]
      sentiment: str                      # positive/negative/neutral

  class NewsSearchResponse(BaseModel):
      items: List[NewsItem]
      total: int
      has_more: bool
      search_time: float
  ```
- **资源**: news_items表、全文搜索引擎
- **逻辑**: 执行复合条件查询，应用时间和股票过滤，按影响评分排序，支持分页查询，返回结构化的新闻数据列表

### API4: 实时新闻推送 (WebSocket)
- **URL**: `WebSocket ws://localhost:8005/ws/news-alerts`
- **输入参数**: WebSocket连接和用户认证
  ```python
  class NewsSubscriptionRequest(BaseModel):
      user_id: str                        # 用户ID
      subscription_type: str = "keyword_alerts"  # 订阅类型
      filters: Optional[Dict[str, Any]] = None    # 过滤条件
  ```
- **输出结果**: 实时新闻推送
  ```python
  class NewsAlert(BaseModel):
      news_id: str
      user_id: str
      alert_type: str                     # email/push/websocket
      impact_level: str                   # low/medium/high
      message: str                        # 推送消息
      news_data: NewsItem                 # 完整新闻数据
      matched_keywords: List[str]         # 匹配的关键词
  ```
- **资源**: WebSocket连接池、Redis发布订阅
- **逻辑**: 建立WebSocket连接，验证用户身份，订阅用户关键词，监听新闻事件，实时推送匹配的新闻提醒到前端

### API5: 新闻影响分析 (对接AI Service)
- **URL**: `POST /api/news/analyze`
- **输入参数**: 新闻分析请求
  ```python
  class NewsAnalysisRequest(BaseModel):
      news_id: Optional[str] = None       # 新闻ID
      text_content: Optional[str] = None  # 文本内容
      analysis_types: List[str] = ["sentiment", "impact", "stocks"]  # 分析类型
  ```
- **输出结果**: 新闻分析结果
  ```python
  class NewsAnalysisResult(BaseModel):
      sentiment: str                      # 情感分析结果
      sentiment_confidence: float        # 情感置信度
      impact_score: float                 # 影响评分
      affected_stocks: List[str]          # 受影响股票
      key_entities: List[str]             # 关键实体
      classification: str                 # 新闻分类
      analysis_metadata: Dict[str, Any]   # 分析元数据
  ```
- **资源**: AI Service、NLP分析引擎
- **逻辑**: 调用AI Service进行文本分析，提取股票实体和关键词，计算情感和影响评分，更新新闻分析结果，返回结构化的分析数据

---

## 🔧 核心服务实现

### 1. RSSService (RSS采集服务)
- **文件**: `app/services/rss_service.py`
- **功能**: RSS源管理和内容采集
- **输入**: RSS源配置和轮询任务
- **输出**: 原始新闻数据
- **资源**: RSS解析器、HTTP客户端
- **逻辑**: 定时轮询RSS源，解析XML/JSON格式，提取新闻元数据，检测重复内容，存储原始数据到数据库，触发后续分析任务

### 2. NewsAnalyzer (新闻分析服务)
- **文件**: `app/services/news_analyzer.py`
- **功能**: 新闻内容智能分析
- **输入**: 原始新闻数据
- **输出**: 分析结果和评分
- **资源**: AI Service接口、NLP工具
- **逻辑**: 调用AI Service进行情感分析，使用NER技术提取股票实体，计算新闻影响评分，分类新闻类型，更新分析结果到数据库

### 3. AlertService (推送服务)
- **文件**: `app/services/alert_service.py`
- **功能**: 智能推送和通知管理
- **输入**: 新闻事件和用户订阅
- **输出**: 多渠道推送消息
- **资源**: WebSocket连接、邮件服务、短信服务
- **逻辑**: 匹配用户关键词订阅，评估推送优先级，选择合适的推送渠道，格式化推送消息，记录推送状态和用户反馈

### 4. KeywordService (关键词监控服务)
- **文件**: `app/services/keyword_service.py`
- **功能**: 用户关键词管理和匹配
- **输入**: 用户关键词配置和新闻内容
- **输出**: 关键词匹配结果
- **逻辑**: 维护用户关键词索引，实现高效的关键词匹配算法，支持模糊匹配和正则表达式，管理关键词优先级和权重

### 5. TranslationService (翻译服务)
- **文件**: `app/services/translation_service.py`
- **功能**: 多语言新闻自动翻译
- **输入**: 外文新闻内容
- **输出**: 中文翻译结果
- **逻辑**: 检测新闻语言类型，调用翻译API进行自动翻译，保持原文和译文的对应关系，提供翻译质量评估和人工校对接口

---

## 🕷️ 新闻爬虫架构

### 爬虫基类设计
```python
# app/crawlers/base_crawler.py
class BaseNewsCrawler:
    """新闻爬虫基类"""
    def __init__(self, source_config):
        self.source_config = source_config
        self.session = requests.Session()
        self.setup_headers()
        self.setup_retry_strategy()

    def crawl(self) -> List[NewsItem]:
        """抽象方法：执行爬取"""
        raise NotImplementedError

    def parse_article(self, raw_data) -> NewsItem:
        """解析单篇文章"""
        raise NotImplementedError
```

### RSS专用爬虫
```python
# app/crawlers/rss_crawler.py
class RSSCrawler(BaseNewsCrawler):
    """RSS源爬虫"""
    def crawl(self) -> List[NewsItem]:
        # 使用feedparser解析RSS
        # 提取title, link, description, pubDate
        # 去重检测和增量更新
        # 返回标准化的NewsItem列表
        pass
```

---

## 🌐 数据流设计

### 新闻采集流程
1. **定时触发** → Celery定时任务 → RSS源轮询 → 内容解析
2. **数据处理** → 重复检测 → 格式标准化 → 数据库存储
3. **智能分析** → AI分析任务 → 情感和影响评分 → 股票实体提取
4. **推送匹配** → 关键词匹配 → 用户筛选 → 多渠道推送

### 实时推送流程
1. **事件触发** → 新闻分析完成 → 发布Redis事件
2. **匹配检测** → 关键词匹配引擎 → 用户订阅筛选
3. **推送执行** → WebSocket推送 → 邮件/短信发送 → 状态记录
4. **反馈处理** → 用户反馈收集 → 推送效果评估 → 算法优化

---

## ⚡ 性能优化策略

### 采集性能优化
- **并发限制**: 每个RSS源独立线程，控制总并发数
- **增量更新**: 基于发布时间和URL的增量采集
- **缓存策略**: RSS内容缓存避免重复解析
- **故障恢复**: 自动重试机制和故障转移

### 分析性能优化
- **批量处理**: 新闻批量分析，提高AI调用效率
- **异步队列**: Celery异步任务队列处理分析任务
- **结果缓存**: 分析结果缓存避免重复计算
- **优先级队列**: 重要新闻优先分析和推送

---

## 🔒 环境配置

### 环境变量 (.env)
```bash
# 服务配置
NEWS_SERVICE_PORT=8005
MAX_CONCURRENT_CRAWLERS=3
NEWS_RETENTION_DAYS=30

# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost:5432/prism2
REDIS_URL=redis://localhost:6379/5

# Celery配置
CELERY_BROKER_URL=redis://localhost:6379/5
CELERY_RESULT_BACKEND=redis://localhost:6379/5
CELERY_WORKER_CONCURRENCY=2

# RSS配置
RSS_POLL_INTERVAL=300
RSS_REQUEST_TIMEOUT=30
RSS_MAX_RETRIES=3
USER_AGENT=Mozilla/5.0 Financial News Collector

# AI服务配置
AI_SERVICE_URL=http://localhost:11434
AI_SERVICE_TIMEOUT=30

# 推送服务配置
WEBSOCKET_MAX_CONNECTIONS=1000
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
SMS_API_KEY=your-sms-api-key

# 翻译服务配置
TRANSLATION_SERVICE=google  # google/baidu/tencent
TRANSLATION_API_KEY=your-translation-key

# 监控配置
LOG_LEVEL=INFO
METRICS_ENABLED=true
ALERT_WEBHOOK_URL=
```

### 依赖配置 (requirements.txt)
```txt
fastapi==0.104.1
uvicorn==0.24.0
celery==5.3.4
redis==5.0.1
psycopg2-binary==2.9.7
sqlalchemy==2.0.23
feedparser==6.0.10
beautifulsoup4==4.12.2
lxml==4.9.3
requests==2.31.0
pydantic==2.5.0
websockets==12.0
aiofiles==23.2.1
python-multipart==0.0.6
newspaper3k==0.2.8
textblob==0.17.1
langdetect==1.0.9
```

---

## 📊 监控和质量评估

### 关键性能指标
- **采集效率**: 每分钟成功采集的新闻数量
- **分析准确率**: AI分析结果的准确性评估
- **推送延迟**: 从新闻发布到用户收到推送的时间
- **用户满意度**: 推送内容的相关性和有用性评分

### 数据质量监控
```python
QUALITY_METRICS = {
    'duplicate_rate': '重复新闻比例',
    'analysis_success_rate': '分析成功率',
    'sentiment_accuracy': '情感分析准确率',
    'stock_extraction_accuracy': '股票实体提取准确率',
    'translation_quality': '翻译质量评分'
}
```

---

*文档更新时间: 2025-09-16*
*严格遵循外部设计规范，确保接口一致性*