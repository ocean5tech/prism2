# Data Service - 内部设计文档

## 📋 基本信息

- **模块名称**: Data Service (数据采集服务)
- **技术栈**: FastAPI + Scrapy + APScheduler + Celery
- **部署端口**: 8003
- **依据**: 外部设计文档规范

---

## 📁 文件结构和权限

```
/home/wyatt/prism2/data-service/
├── app/                                  # 应用源代码 (755)
│   ├── __init__.py                       # (644)
│   ├── main.py                           # FastAPI应用入口 (644)
│   ├── core/                             # 核心配置 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── config.py                     # 环境配置 (644)
│   │   ├── dependencies.py               # 依赖注入 (644)
│   │   └── security.py                   # 安全配置 (644)
│   ├── api/                              # API路由 (755)
│   │   ├── __init__.py                   # (644)
│   │   └── v1/                           # API版本1 (755)
│   │       ├── __init__.py               # (644)
│   │       ├── data.py                   # 数据相关端点 (644)
│   │       ├── sources.py                # 数据源管理端点 (644)
│   │       └── health.py                 # 健康检查端点 (644)
│   ├── services/                         # 业务服务层 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── data_collector.py             # 数据采集服务 (644)
│   │   ├── data_cleaner.py               # 数据清洗服务 (644)
│   │   ├── source_manager.py             # 数据源管理服务 (644)
│   │   └── scheduler_service.py          # 定时任务服务 (644)
│   ├── crawlers/                         # 爬虫模块 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── base_crawler.py               # 爬虫基类 (644)
│   │   ├── stock_crawler.py              # 股票数据爬虫 (644)
│   │   ├── news_crawler.py               # 新闻数据爬虫 (644)
│   │   └── announcement_crawler.py       # 公告数据爬虫 (644)
│   ├── models/                           # 数据模型 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── requests.py                   # 请求模型 (644)
│   │   ├── responses.py                  # 响应模型 (644)
│   │   └── database.py                   # 数据库模型 (644)
│   ├── tasks/                            # Celery任务 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── data_tasks.py                 # 数据采集任务 (644)
│   │   └── cleanup_tasks.py              # 数据清理任务 (644)
│   └── utils/                            # 工具函数 (755)
│       ├── __init__.py                   # (644)
│       ├── data_parser.py                # 数据解析工具 (644)
│       ├── data_validator.py             # 数据验证工具 (644)
│       └── retry_helper.py               # 重试机制工具 (644)
├── scrapy_project/                       # Scrapy项目 (755)
│   ├── scrapy.cfg                        # Scrapy配置 (644)
│   ├── spiders/                          # 爬虫脚本 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── sina_spider.py                # 新浪财经爬虫 (644)
│   │   ├── eastmoney_spider.py           # 东方财富爬虫 (644)
│   │   └── cninfo_spider.py              # 巨潮资讯爬虫 (644)
│   ├── items.py                          # 数据项定义 (644)
│   ├── pipelines.py                      # 数据管道 (644)
│   └── settings.py                       # Scrapy设置 (644)
├── requirements.txt                      # Python依赖 (644)
├── Dockerfile                           # 容器化配置 (644)
└── .env                                 # 环境变量 (600)
```

---

## 🗄️ 数据库表结构 (PostgreSQL + TimescaleDB)

### 数据源配置表 (data_sources)
```sql
CREATE TABLE data_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,              -- 数据源名称
    source_type VARCHAR(50) NOT NULL,        -- 类型: rss/api/scraper
    source_url TEXT NOT NULL,                -- 数据源URL
    poll_interval INTEGER DEFAULT 300,       -- 轮询间隔(秒)
    enabled BOOLEAN DEFAULT true,            -- 是否启用
    config JSONB,                           -- 配置参数
    last_poll_time TIMESTAMP,               -- 最后轮询时间
    success_count INTEGER DEFAULT 0,        -- 成功次数
    error_count INTEGER DEFAULT 0,          -- 错误次数
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_data_sources_type ON data_sources(source_type);
CREATE INDEX idx_data_sources_enabled ON data_sources(enabled);
```

### 原始数据表 (raw_data) - TimescaleDB优化
```sql
CREATE TABLE raw_data (
    id BIGSERIAL,
    source_id INTEGER REFERENCES data_sources(id),
    data_type VARCHAR(50) NOT NULL,          -- 数据类型: stock/news/announcement
    content JSONB NOT NULL,                  -- 原始数据内容
    checksum VARCHAR(64),                    -- 数据校验和(去重用)
    status VARCHAR(20) DEFAULT 'pending',    -- 状态: pending/processed/failed
    collected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP,

    -- TimescaleDB分区键
    PRIMARY KEY (collected_at, id)
);

-- 创建TimescaleDB超表
SELECT create_hypertable('raw_data', 'collected_at', chunk_time_interval => INTERVAL '1 day');

-- 索引优化
CREATE INDEX idx_raw_data_type ON raw_data(data_type, collected_at);
CREATE INDEX idx_raw_data_status ON raw_data(status);
CREATE INDEX idx_raw_data_checksum ON raw_data(checksum);
```

### 处理任务表 (processing_tasks)
```sql
CREATE TABLE processing_tasks (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,          -- 任务类型
    task_config JSONB,                       -- 任务配置
    status VARCHAR(20) DEFAULT 'pending',    -- pending/running/completed/failed
    priority INTEGER DEFAULT 5,             -- 优先级 1-10
    retry_count INTEGER DEFAULT 0,          -- 重试次数
    max_retries INTEGER DEFAULT 3,          -- 最大重试次数
    error_message TEXT,                      -- 错误信息
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- 索引
    INDEX idx_tasks_status (status),
    INDEX idx_tasks_priority (priority, created_at)
);
```

### 数据质量监控表 (data_quality_metrics)
```sql
CREATE TABLE data_quality_metrics (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES data_sources(id),
    metric_name VARCHAR(100),                -- 指标名称
    metric_value DECIMAL(10,4),              -- 指标值
    metric_unit VARCHAR(20),                 -- 单位
    threshold_min DECIMAL(10,4),             -- 最小阈值
    threshold_max DECIMAL(10,4),             -- 最大阈值
    is_within_threshold BOOLEAN,             -- 是否在阈值内
    measured_at TIMESTAMP DEFAULT NOW(),

    -- TimescaleDB分区
    PRIMARY KEY (measured_at, id)
);

SELECT create_hypertable('data_quality_metrics', 'measured_at', chunk_time_interval => INTERVAL '1 hour');
```

---

## 🔌 API接口定义 (严格按照外部设计)

### 基础配置
```python
# 服务配置
DATA_SERVICE_PORT = int(os.getenv('DATA_SERVICE_PORT', '8003'))
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/3')
SCRAPY_PROJECT_PATH = os.getenv('SCRAPY_PROJECT_PATH', './scrapy_project')
MAX_CONCURRENT_CRAWLERS = int(os.getenv('MAX_CONCURRENT_CRAWLERS', '5'))
```

### API1: 数据源配置管理 (对接外部设计接口)
- **URL**: `POST /api/data/configure`
- **输入参数**: 严格按照外部设计的数据源配置请求
  ```python
  class DataSourceConfigRequest(BaseModel):
      source_type: str                      # rss/api/scraper/manual
      source_url: str                       # 数据源URL
      poll_interval: int = 300              # 轮询间隔(秒)
      keywords: Optional[List[str]] = None  # 关键词过滤
      config: Optional[Dict[str, Any]] = None  # 扩展配置
      enabled: bool = True                  # 是否启用
  ```
- **输出结果**: 外部设计的配置响应
  ```python
  class DataSourceConfigResponse(BaseModel):
      source_id: str                        # 数据源唯一ID
      status: str                          # success/failed
      message: str                         # 状态描述
      next_poll_time: datetime             # 下次轮询时间
  ```
- **资源**: data_sources表、Celery任务队列
- **逻辑**: 接收数据源配置请求，验证URL可访问性，创建数据源记录，启动定时采集任务，返回配置状态和下次执行时间

### API2: OHLCV历史数据获取 (对接Stock Service)
- **URL**: `GET /api/data/stocks/{stock_code}/ohlcv`
- **输入参数**: 外部设计的OHLCV数据请求
  ```python
  class OHLCVRequest(BaseModel):
      stock_code: str                       # 股票代码
      period: str = "1d"                   # 周期: 1m/5m/15m/30m/1h/1d/1w/1M
      limit: int = 100                     # 返回条数
      start_date: Optional[str] = None     # 开始日期
      end_date: Optional[str] = None       # 结束日期
  ```
- **输出结果**: 外部设计的OHLCV数据响应
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

  class OHLCVResponse(BaseModel):
      data: List[OHLCVData]
      total_count: int
      period: str
      data_quality: float                  # 数据质量评分 0-1
  ```
- **资源**: TimescaleDB OHLCV表、数据质量监控
- **逻辑**: 根据股票代码和时间范围查询OHLCV历史数据，支持多种时间周期聚合，检查数据完整性和质量，返回带质量评分的数据列表

### API3: 新闻数据采集状态查询
- **URL**: `GET /api/data/news/status`
- **输入参数**: 新闻采集状态查询
  ```python
  class NewsCollectionStatusRequest(BaseModel):
      source_ids: Optional[List[str]] = None  # 指定数据源ID
      date_range: Optional[Dict[str, str]] = None  # 时间范围
      status_filter: Optional[str] = None   # 状态过滤
  ```
- **输出结果**: 新闻采集状态报告
  ```python
  class NewsData(BaseModel):
      id: str
      title: str
      content: str
      source: str
      publish_time: datetime
      stock_codes: List[str]
      sentiment: str                        # positive/negative/neutral

  class NewsCollectionStatusResponse(BaseModel):
      total_collected: int                  # 总采集数量
      successful: int                       # 成功处理数量
      failed: int                          # 失败数量
      latest_items: List[NewsData]         # 最新采集的数据
      collection_rate: float               # 采集效率
  ```
- **资源**: raw_data表、processing_tasks表
- **逻辑**: 统计指定时间范围内的新闻采集情况，计算采集成功率和处理效率，返回最新采集的新闻样本和整体状态指标

### API4: 数据清洗和质量检查
- **URL**: `POST /api/data/quality/check`
- **输入参数**: 数据质量检查请求
  ```python
  class DataQualityCheckRequest(BaseModel):
      data_type: str                        # 检查的数据类型
      batch_id: Optional[str] = None       # 批次ID
      quality_rules: List[str]             # 质量规则列表
      auto_fix: bool = False               # 是否自动修复
  ```
- **输出结果**: 数据质量检查报告
  ```python
  class QualityIssue(BaseModel):
      issue_type: str                       # 问题类型
      severity: str                        # 严重程度
      affected_records: int                # 受影响记录数
      description: str                     # 问题描述

  class DataQualityResponse(BaseModel):
      total_records: int                    # 总记录数
      valid_records: int                   # 有效记录数
      quality_score: float                 # 质量评分 0-1
      issues: List[QualityIssue]           # 质量问题列表
      recommendations: List[str]           # 改进建议
  ```
- **资源**: 数据验证引擎、数据质量规则库
- **逻辑**: 对指定批次的数据执行质量检查规则，识别数据完整性、准确性、一致性问题，生成质量评分和详细问题报告，提供数据改进建议

---

## 🔧 核心服务实现

### 1. DataCollector (数据采集服务)
- **文件**: `app/services/data_collector.py`
- **功能**: 统一的数据采集服务接口
- **输入**: 数据源配置和采集参数
- **输出**: 原始数据存储和采集状态
- **资源**: Scrapy爬虫引擎、Celery任务队列
- **逻辑**: 根据数据源类型选择合适的采集器，管理并发采集任务，监控采集进度和错误率，实现增量采集和重复数据检测

### 2. DataCleaner (数据清洗服务)
- **文件**: `app/services/data_cleaner.py`
- **功能**: 原始数据标准化和质量提升
- **输入**: 原始数据记录
- **输出**: 清洗后的结构化数据
- **资源**: 数据验证规则、清洗算法库
- **逻辑**: 执行数据格式标准化、异常值检测和修复、缺失值填充、数据类型转换，确保数据质量满足下游服务需求

### 3. SourceManager (数据源管理服务)
- **文件**: `app/services/source_manager.py`
- **功能**: 数据源生命周期管理
- **输入**: 数据源配置和状态更新
- **输出**: 数据源健康状态和性能指标
- **逻辑**: 管理数据源的添加、更新、删除操作，监控数据源可用性和响应时间，实现自动故障检测和恢复，维护数据源配置历史

### 4. SchedulerService (定时任务服务)
- **文件**: `app/services/scheduler_service.py`
- **功能**: 基于APScheduler的智能任务调度
- **输入**: 任务配置和调度规则
- **输出**: 任务执行状态和调度日志
- **逻辑**: 根据数据源配置创建定时采集任务，实现任务优先级管理和负载均衡，支持任务失败重试和依赖关系处理

---

## 🕷️ Scrapy爬虫架构

### 爬虫项目结构
```python
# scrapy_project/spiders/base_spider.py
class BaseFinancialSpider(scrapy.Spider):
    """金融数据爬虫基类"""
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS': 8,
        'USER_AGENT': 'Mozilla/5.0 Financial Data Collector'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_proxy_middleware()
        self.setup_retry_middleware()
```

### 数据管道配置
```python
# scrapy_project/pipelines.py
class DataValidationPipeline:
    """数据验证管道"""
    def process_item(self, item, spider):
        # 数据格式验证
        # 重复数据检测
        # 数据质量评分
        return item

class DatabasePipeline:
    """数据库存储管道"""
    def process_item(self, item, spider):
        # 存储到raw_data表
        # 触发后续处理任务
        return item
```

---

## 🌐 数据流设计

### 实时数据采集流程
1. **任务调度** → APScheduler触发采集任务 → Celery执行器接收
2. **数据获取** → Scrapy爬虫启动 → 外部API调用 → 原始数据获取
3. **初步处理** → 格式验证 → 重复检测 → raw_data表存储
4. **后续处理** → 数据清洗 → 质量检查 → 推送到下游服务

### 批量数据处理流程
1. **批次创建** → 定义处理批次 → 设置处理规则 → 任务分发
2. **并行处理** → 多Worker处理 → 进度监控 → 错误处理
3. **质量控制** → 数据验证 → 异常标记 → 质量报告生成
4. **结果输出** → 清洗数据存储 → 状态更新 → 下游通知

---

## ⚡ 性能优化策略

### 采集性能优化
- **并发控制**: 基于目标网站负载能力动态调整并发数
- **智能重试**: 指数退避重试策略，避免过度请求
- **缓存机制**: 重复URL检测，避免重复采集
- **负载均衡**: 多实例部署，任务智能分发

### 数据处理优化
- **流式处理**: 大数据集采用流式处理，减少内存占用
- **批量操作**: 数据库批量插入，提高写入效率
- **索引优化**: TimescaleDB时间分区和索引优化
- **异步处理**: Celery异步任务处理，提高响应速度

---

## 🔒 环境配置

### 环境变量 (.env)
```bash
# 服务配置
DATA_SERVICE_PORT=8003
MAX_CONCURRENT_CRAWLERS=5
DATA_RETENTION_DAYS=90

# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost:5432/prism2
TIMESCALEDB_ENABLED=true

# Celery配置
CELERY_BROKER_URL=redis://localhost:6379/3
CELERY_RESULT_BACKEND=redis://localhost:6379/3
CELERY_WORKER_CONCURRENCY=4

# Scrapy配置
SCRAPY_PROJECT_PATH=./scrapy_project
USER_AGENT=Mozilla/5.0 Financial Data Collector
DOWNLOAD_DELAY=1
CONCURRENT_REQUESTS=8

# 代理配置 (可选)
PROXY_ENABLED=false
PROXY_LIST=[]

# 监控配置
SENTRY_DSN=
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

### 依赖配置 (requirements.txt)
```txt
fastapi==0.104.1
uvicorn==0.24.0
scrapy==2.11.0
celery==5.3.4
redis==5.0.1
psycopg2-binary==2.9.7
apscheduler==3.10.4
sqlalchemy==2.0.23
alembic==1.12.1
pydantic==2.5.0
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
feedparser==6.0.10
```

---

## 📊 监控和告警

### 关键性能指标
- **采集速率**: 每分钟成功采集的数据条数
- **数据质量**: 各数据源的数据质量评分
- **错误率**: 采集失败率和错误类型分布
- **响应时间**: API响应时间和数据库查询时间
- **资源使用**: CPU、内存、磁盘使用率

### 告警规则配置
```python
ALERT_RULES = {
    'collection_failure_rate': {
        'threshold': 0.1,              # 失败率超过10%
        'action': 'email+slack'
    },
    'data_quality_score': {
        'threshold': 0.8,              # 质量评分低于80%
        'action': 'slack'
    },
    'source_unavailable': {
        'threshold': 300,              # 数据源不可用超过5分钟
        'action': 'email+sms'
    }
}
```

---

*文档更新时间: 2025-09-16*
*严格遵循外部设计规范，确保接口一致性*