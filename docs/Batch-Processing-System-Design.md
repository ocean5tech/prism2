# Prism2 批处理系统设计文档

## 📋 文档概览

**项目名称**: Prism2 Backend批处理系统
**设计版本**: v1.0
**创建时间**: 2025-09-19
**最后更新**: 2025-09-19
**负责人**: Claude Code AI
**依据**: 基于现有三层架构 (Redis → PostgreSQL → AKShare)

### 🎯 核心目标

1. **自选股优先批处理**: 用户可配置自选股列表，夜间优先预热数据
2. **RAG数据同步**: 结构化数据自动同步到向量数据库，支持版本管理
3. **性能优化**: 缓存命中率提升至80%+，响应时间减少90%
4. **系统稳定性**: 减少AKShare API调用压力，提升系统可靠性

## 🏗️ 系统架构设计

### 整体架构图
```
┌─────────────────────────────────────────────────────────────┐
│                    Batch Processing System                  │
├─────────────────────────────────────────────────────────────┤
│  Scheduler Service (APScheduler)                            │
│  ├── Priority Watchlist Processor                          │
│  ├── Market Data Warm Processor                            │
│  ├── Cache Maintenance Processor                           │
│  └── RAG Sync Processor                                    │
├─────────────────────────────────────────────────────────────┤
│  Data Layer Integration                                     │
│  ├── Redis Cache (Layer 1)                                 │
│  ├── PostgreSQL Storage (Layer 2)                          │
│  ├── AKShare API (Layer 3)                                 │
│  └── ChromaDB Vector Store (RAG Layer)                     │
├─────────────────────────────────────────────────────────────┤
│  Monitoring & Management                                    │
│  ├── Job Status Tracking                                   │
│  ├── Performance Metrics                                   │
│  ├── Error Handling & Recovery                             │
│  └── API Management Interface                              │
└─────────────────────────────────────────────────────────────┘
```

### 模块结构设计
```
backend/
├── batch_processor/                 # 批处理模块
│   ├── __init__.py
│   ├── scheduler.py                # APScheduler调度器主服务
│   ├── config/                     # 配置管理
│   │   ├── __init__.py
│   │   ├── batch_config.py         # 批处理配置
│   │   ├── schedules.yaml          # 调度配置文件
│   │   └── stock_pools.yaml        # 股票池配置
│   ├── processors/                 # 处理器模块
│   │   ├── __init__.py
│   │   ├── watchlist_processor.py  # 自选股处理器
│   │   ├── market_data_processor.py # 市场数据处理器
│   │   ├── cache_processor.py      # 缓存维护处理器
│   │   └── rag_processor.py        # RAG同步处理器
│   ├── models/                     # 数据模型
│   │   ├── __init__.py
│   │   ├── watchlist.py           # 自选股模型
│   │   ├── batch_job.py           # 批处理任务模型
│   │   ├── rag_version.py         # RAG版本模型
│   │   └── job_status.py          # 任务状态模型
│   ├── services/                   # 服务层
│   │   ├── __init__.py
│   │   ├── watchlist_service.py   # 自选股服务
│   │   ├── rag_sync_service.py    # RAG同步服务
│   │   ├── priority_service.py    # 优先级管理服务
│   │   └── monitor_service.py     # 监控服务
│   ├── utils/                      # 工具模块
│   │   ├── __init__.py
│   │   ├── data_hasher.py         # 数据指纹生成
│   │   ├── vector_utils.py        # 向量化工具
│   │   ├── performance_tracker.py # 性能跟踪
│   │   └── logger_config.py       # 日志配置
│   └── api/                        # API接口
│       ├── __init__.py
│       ├── watchlist_api.py       # 自选股管理API
│       ├── batch_api.py           # 批处理管理API
│       └── monitor_api.py         # 监控API
├── enhanced_dashboard_api.py        # 现有API (复用)
├── batch_service.py                # 批处理服务主入口
└── requirements_batch.txt          # 批处理依赖包
```

## 📊 数据层设计

### 1. 自选股相关表
```sql
-- 用户自选股列表表
CREATE TABLE user_watchlists (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,              -- 用户标识
    watchlist_name VARCHAR(100) NOT NULL,       -- 自选股列表名称
    description TEXT,                           -- 列表描述
    stock_codes TEXT[] NOT NULL,               -- 股票代码数组
    priority_level INTEGER DEFAULT 3,          -- 优先级 (1-5, 5最高)
    auto_batch BOOLEAN DEFAULT true,           -- 是否参与自动批处理
    data_types TEXT[] DEFAULT ARRAY['financial', 'announcements', 'shareholders'], -- 需要预热的数据类型
    schedule_time TIME DEFAULT '01:00:00',     -- 自定义调度时间
    is_active BOOLEAN DEFAULT true,           -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_priority CHECK (priority_level BETWEEN 1 AND 5),
    CONSTRAINT valid_data_types CHECK (array_length(data_types, 1) > 0)
);

-- 自选股使用统计表
CREATE TABLE watchlist_usage_stats (
    id SERIAL PRIMARY KEY,
    watchlist_id INTEGER NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    access_count INTEGER DEFAULT 0,           -- 访问次数
    last_accessed TIMESTAMP,                  -- 最后访问时间
    avg_response_time DECIMAL(10,3),          -- 平均响应时间
    cache_hit_rate DECIMAL(5,4),             -- 缓存命中率
    date_recorded DATE DEFAULT CURRENT_DATE,  -- 统计日期

    FOREIGN KEY (watchlist_id) REFERENCES user_watchlists(id) ON DELETE CASCADE,
    CONSTRAINT uk_watchlist_stats UNIQUE(watchlist_id, date_recorded)
);
```

### 2. RAG版本管理表
```sql
-- RAG数据版本表
CREATE TABLE rag_data_versions (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    data_type VARCHAR(50) NOT NULL,           -- financial, announcements, shareholders, longhubang
    version_id UUID DEFAULT gen_random_uuid(),
    data_hash VARCHAR(64) NOT NULL,           -- 数据MD5指纹
    vector_status VARCHAR(20) DEFAULT 'active', -- active, deprecated, archived, failed
    source_data JSONB NOT NULL,               -- 原始结构化数据
    vector_metadata JSONB,                    -- 向量化元数据
    embedding_model VARCHAR(100) DEFAULT 'bge-large-zh-v1.5',
    chunk_count INTEGER DEFAULT 0,           -- 分块数量
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activated_at TIMESTAMP,                  -- 激活时间
    deprecated_at TIMESTAMP,                 -- 废弃时间

    CONSTRAINT uk_stock_data_active UNIQUE(stock_code, data_type, vector_status)
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT valid_vector_status CHECK (vector_status IN ('active', 'deprecated', 'archived', 'failed'))
);

-- 向量映射表
CREATE TABLE rag_vector_mappings (
    id SERIAL PRIMARY KEY,
    version_id UUID NOT NULL,                -- 对应的版本ID
    vector_id VARCHAR(100) NOT NULL,         -- ChromaDB中的向量ID
    collection_name VARCHAR(100) NOT NULL,   -- ChromaDB集合名
    chunk_index INTEGER NOT NULL,           -- 分块索引
    chunk_text TEXT NOT NULL,               -- 分块文本内容
    metadata JSONB,                         -- 向量元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (version_id) REFERENCES rag_data_versions(version_id) ON DELETE CASCADE,
    CONSTRAINT uk_vector_mapping UNIQUE(vector_id, collection_name)
);
```

### 3. 批处理任务管理表
```sql
-- 批处理任务表
CREATE TABLE batch_jobs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,          -- 任务名称
    job_type VARCHAR(50) NOT NULL,           -- watchlist_warm, market_scan, cache_clean, rag_sync
    job_category VARCHAR(30) NOT NULL,       -- scheduled, manual, priority
    stock_code VARCHAR(10),                  -- 处理的股票代码 (可选)
    data_type VARCHAR(50),                   -- 处理的数据类型 (可选)
    watchlist_id INTEGER,                   -- 关联的自选股列表 (可选)
    status VARCHAR(20) DEFAULT 'pending',    -- pending, running, success, failed, cancelled
    priority_level INTEGER DEFAULT 3,        -- 任务优先级
    scheduled_time TIMESTAMP,               -- 计划执行时间
    start_time TIMESTAMP,                   -- 实际开始时间
    end_time TIMESTAMP,                     -- 完成时间
    duration_seconds INTEGER,               -- 执行耗时(秒)
    processed_count INTEGER DEFAULT 0,      -- 处理数量
    success_count INTEGER DEFAULT 0,        -- 成功数量
    failed_count INTEGER DEFAULT 0,         -- 失败数量
    error_message TEXT,                     -- 错误信息
    result_summary JSONB,                   -- 结果摘要
    retry_count INTEGER DEFAULT 0,         -- 重试次数
    max_retries INTEGER DEFAULT 3,         -- 最大重试次数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_job_status CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
    CONSTRAINT valid_job_type CHECK (job_type IN ('watchlist_warm', 'market_scan', 'cache_clean', 'rag_sync')),
    CONSTRAINT valid_priority CHECK (priority_level BETWEEN 1 AND 5)
);

-- 批处理性能统计表
CREATE TABLE batch_performance_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    metric_type VARCHAR(50) NOT NULL,        -- job_count, avg_duration, success_rate, cache_hit_rate
    metric_category VARCHAR(30),             -- job_type分类
    metric_value DECIMAL(15,6) NOT NULL,
    additional_data JSONB,                   -- 额外统计数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_daily_metric UNIQUE(date, metric_type, metric_category)
);
```

### 4. 索引设计
```sql
-- 自选股表索引
CREATE INDEX idx_watchlists_user_active ON user_watchlists(user_id, is_active);
CREATE INDEX idx_watchlists_priority_batch ON user_watchlists(priority_level, auto_batch) WHERE is_active = true;
CREATE INDEX idx_watchlists_schedule ON user_watchlists(schedule_time) WHERE auto_batch = true AND is_active = true;

-- RAG版本表索引
CREATE INDEX idx_rag_versions_stock_type ON rag_data_versions(stock_code, data_type);
CREATE INDEX idx_rag_versions_status ON rag_data_versions(vector_status, created_at);
CREATE INDEX idx_rag_versions_hash ON rag_data_versions(data_hash);

-- 批处理任务表索引
CREATE INDEX idx_batch_jobs_status_time ON batch_jobs(status, scheduled_time);
CREATE INDEX idx_batch_jobs_type_priority ON batch_jobs(job_type, priority_level);
CREATE INDEX idx_batch_jobs_watchlist ON batch_jobs(watchlist_id) WHERE watchlist_id IS NOT NULL;

-- 性能指标表索引
CREATE INDEX idx_performance_date_type ON batch_performance_metrics(date, metric_type);
```

## 🔗 接口设计

### 1. 自选股管理API
```python
# 自选股CRUD操作
POST   /api/v1/watchlist                    # 创建自选股列表
GET    /api/v1/watchlist/{user_id}          # 获取用户所有自选股列表
GET    /api/v1/watchlist/{watchlist_id}     # 获取特定自选股列表详情
PUT    /api/v1/watchlist/{watchlist_id}     # 更新自选股列表
DELETE /api/v1/watchlist/{watchlist_id}     # 删除自选股列表

# 自选股批处理操作
POST   /api/v1/watchlist/{watchlist_id}/batch/trigger    # 手动触发批处理
GET    /api/v1/watchlist/{watchlist_id}/batch/status     # 获取批处理状态
PUT    /api/v1/watchlist/{watchlist_id}/batch/config     # 更新批处理配置

# 自选股统计信息
GET    /api/v1/watchlist/{watchlist_id}/stats            # 获取使用统计
GET    /api/v1/watchlist/{user_id}/stats/summary         # 获取用户统计摘要
```

### 2. 批处理管理API
```python
# 批处理任务管理
GET    /api/v1/batch/jobs                   # 获取批处理任务列表
GET    /api/v1/batch/jobs/{job_id}          # 获取特定任务详情
POST   /api/v1/batch/jobs/trigger           # 手动触发批处理任务
PUT    /api/v1/batch/jobs/{job_id}/cancel   # 取消批处理任务
DELETE /api/v1/batch/jobs/{job_id}          # 删除批处理任务记录

# 批处理调度管理
GET    /api/v1/batch/schedule               # 获取调度配置
PUT    /api/v1/batch/schedule               # 更新调度配置
POST   /api/v1/batch/schedule/pause         # 暂停调度
POST   /api/v1/batch/schedule/resume        # 恢复调度

# 批处理性能监控
GET    /api/v1/batch/metrics                # 获取性能指标
GET    /api/v1/batch/metrics/dashboard      # 获取监控面板数据
GET    /api/v1/batch/health                 # 健康检查
```

### 3. RAG同步管理API
```python
# RAG版本管理
GET    /api/v1/rag/versions                 # 获取RAG版本列表
GET    /api/v1/rag/versions/{version_id}    # 获取特定版本详情
POST   /api/v1/rag/sync/trigger             # 手动触发RAG同步
PUT    /api/v1/rag/versions/{version_id}/activate   # 激活特定版本
PUT    /api/v1/rag/versions/{version_id}/deprecate  # 废弃特定版本

# RAG数据查询
POST   /api/v1/rag/query                    # RAG增强查询
GET    /api/v1/rag/collections              # 获取向量集合信息
GET    /api/v1/rag/stats                    # 获取RAG统计信息
```

### 4. 接口数据模型
```python
# 自选股模型
class WatchlistCreate(BaseModel):
    user_id: str
    watchlist_name: str
    description: Optional[str] = None
    stock_codes: List[str]
    priority_level: int = 3
    data_types: List[str] = ["financial", "announcements", "shareholders"]
    schedule_time: Optional[time] = None
    auto_batch: bool = True

class WatchlistResponse(BaseModel):
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

# 批处理任务模型
class BatchJobResponse(BaseModel):
    id: int
    job_name: str
    job_type: str
    status: str
    priority_level: int
    scheduled_time: Optional[datetime]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    processed_count: int
    success_count: int
    failed_count: int
    error_message: Optional[str]
    result_summary: Optional[dict]

# RAG版本模型
class RAGVersionResponse(BaseModel):
    id: int
    stock_code: str
    data_type: str
    version_id: str
    vector_status: str
    chunk_count: int
    embedding_model: str
    created_at: datetime
    activated_at: Optional[datetime]
    deprecated_at: Optional[datetime]
```

## 📦 外部依赖列表

### Python包依赖
```txt
# requirements_batch.txt
# 调度框架
apscheduler==3.10.4
croniter==1.4.1

# 数据处理
pandas==2.1.3
numpy==1.24.3
akshare>=1.12.0

# 向量化处理
sentence-transformers==2.2.2
chromadb==0.4.15
jieba==0.42.1

# 数据库
psycopg2-binary==2.9.9
redis==5.0.1
sqlalchemy==2.0.23

# Web框架扩展
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0

# 工具库
pyyaml==6.0.1
python-multipart==0.0.6
httpx==0.25.2
hashlib-compat==1.0.1

# 监控和日志
prometheus-client==0.19.0
structlog==23.2.0

# 测试框架
pytest==7.4.3
pytest-asyncio==0.21.1
```

### 系统依赖
```yaml
# 必需服务
required_services:
  - Redis 7.0+          # 缓存层
  - PostgreSQL 15+      # 数据存储层
  - ChromaDB 0.4+       # 向量数据库

# 可选服务
optional_services:
  - Prometheus          # 监控指标收集
  - Grafana            # 监控面板
  - Nginx              # 反向代理

# 硬件资源要求
hardware_requirements:
  cpu: "4 cores minimum, 8 cores recommended"
  memory: "8GB minimum, 16GB recommended"
  storage: "50GB available space"
  network: "Stable internet connection for AKShare API"
```

### 配置文件
```yaml
# config/schedules.yaml
schedules:
  priority_batches:
    level_5: "00:30"  # 最高优先级
    level_4: "01:00"
    level_3: "01:30"
    level_2: "02:00"
    level_1: "02:30"

  maintenance_tasks:
    cache_cleanup: "02:00"
    performance_report: "06:00"
    rag_optimization: "03:00"

  market_tasks:
    pre_market_warm: "09:15"
    intraday_update: "*/30 9-15 * * MON-FRI"
    post_market_update: "15:30"

# config/batch_config.yaml
batch_settings:
  max_concurrent_jobs: 5
  max_stocks_per_batch: 20
  default_timeout: 300
  retry_attempts: 3
  backoff_factor: 2.0

rag_settings:
  embedding_model: "bge-large-zh-v1.5"
  chunk_size: 512
  chunk_overlap: 50
  max_chunks_per_document: 100
  similarity_threshold: 0.7
```

## ✅ TodoList 与任务状态

### Phase 1: 基础框架搭建 (预计3天)
- [ ] **1.1 项目结构创建** (4小时)
  - [ ] 创建批处理模块目录结构
  - [ ] 初始化配置文件
  - [ ] 设置依赖包管理
  - [ ] 创建基础__init__.py文件

- [ ] **1.2 数据库表设计实现** (6小时)
  - [ ] 创建自选股相关表
  - [ ] 创建RAG版本管理表
  - [ ] 创建批处理任务表
  - [ ] 添加索引和约束
  - [ ] 编写数据库迁移脚本

- [ ] **1.3 基础模型定义** (4小时)
  - [ ] 实现自选股数据模型
  - [ ] 实现RAG版本数据模型
  - [ ] 实现批处理任务模型
  - [ ] 实现API响应模型

- [ ] **1.4 配置管理系统** (4小时)
  - [ ] 实现配置文件加载器
  - [ ] 实现环境变量管理
  - [ ] 实现运行时配置更新
  - [ ] 配置验证机制

### Phase 2: 核心服务实现 (预计5天)
- [ ] **2.1 自选股服务** (8小时)
  - [ ] 实现自选股CRUD操作
  - [ ] 实现优先级管理逻辑
  - [ ] 实现使用统计收集
  - [ ] 实现批处理触发机制

- [ ] **2.2 批处理调度器** (10小时)
  - [ ] 实现APScheduler集成
  - [ ] 实现任务队列管理
  - [ ] 实现优先级调度算法
  - [ ] 实现任务状态跟踪

- [ ] **2.3 RAG同步服务** (10小时)
  - [ ] 实现数据变化检测
  - [ ] 实现向量化处理流程
  - [ ] 实现版本管理逻辑
  - [ ] 实现ChromaDB集成

- [ ] **2.4 数据处理器** (12小时)
  - [ ] 实现自选股数据预热器
  - [ ] 实现市场数据扫描器
  - [ ] 实现缓存维护处理器
  - [ ] 实现性能监控收集器

### Phase 3: API接口开发 (预计4天)
- [ ] **3.1 自选股管理API** (8小时)
  - [ ] 实现自选股CRUD接口
  - [ ] 实现批处理管理接口
  - [ ] 实现统计查询接口
  - [ ] 接口参数验证和错误处理

- [ ] **3.2 批处理管理API** (8小时)
  - [ ] 实现任务管理接口
  - [ ] 实现调度配置接口
  - [ ] 实现性能监控接口
  - [ ] 实现健康检查接口

- [ ] **3.3 RAG管理API** (6小时)
  - [ ] 实现版本管理接口
  - [ ] 实现同步控制接口
  - [ ] 实现查询统计接口

- [ ] **3.4 API文档和测试** (6小时)
  - [ ] 生成OpenAPI文档
  - [ ] 编写接口测试用例
  - [ ] 实现API性能测试
  - [ ] 集成测试验证

### Phase 4: 集成测试和优化 (预计3天)
- [ ] **4.1 系统集成测试** (8小时)
  - [ ] 与现有Backend API集成测试
  - [ ] Redis缓存一致性测试
  - [ ] PostgreSQL数据一致性测试
  - [ ] ChromaDB向量同步测试

- [ ] **4.2 真实数据测试** (8小时)
  - [ ] 使用真实股票数据测试
  - [ ] 自选股批处理端到端测试
  - [ ] RAG同步完整流程测试
  - [ ] 性能基准测试

- [ ] **4.3 监控和运维** (6小时)
  - [ ] 实现监控指标收集
  - [ ] 实现告警机制
  - [ ] 编写运维文档
  - [ ] 性能调优

- [ ] **4.4 文档完善** (2小时)
  - [ ] 更新设计文档
  - [ ] 编写用户使用指南
  - [ ] 记录已知问题和解决方案

## 🧪 测试计划

### 单元测试
```python
# 测试覆盖率目标: 85%+
test_modules = [
    "test_watchlist_service.py",      # 自选股服务测试
    "test_batch_scheduler.py",        # 调度器测试
    "test_rag_sync_service.py",       # RAG同步测试
    "test_priority_processor.py",     # 优先级处理测试
    "test_data_versioning.py",        # 版本管理测试
    "test_api_endpoints.py",          # API接口测试
]
```

### 集成测试
```python
# 系统集成测试用例
integration_tests = [
    "test_end_to_end_watchlist_batch.py",     # 自选股端到端测试
    "test_rag_integration.py",                # RAG集成测试
    "test_existing_api_compatibility.py",     # 现有API兼容性测试
    "test_three_tier_architecture.py",        # 三层架构集成测试
]
```

### 真实数据测试场景
```python
# 测试股票池
test_stock_codes = [
    "000001",  # 平安银行 - 银行业代表
    "600519",  # 贵州茅台 - 消费业代表
    "688469",  # 科创板代表
    "600919",  # 江苏银行 - 已有测试数据
    "300059",  # 创业板代表
]

# 测试场景
test_scenarios = [
    {
        "name": "自选股优先批处理测试",
        "watchlist": {
            "user_id": "test_user_001",
            "stocks": ["000001", "600519"],
            "priority": 5,
            "data_types": ["financial", "announcements"]
        },
        "expected_results": {
            "cache_population": "100%",
            "response_time_improvement": ">90%",
            "rag_sync_success": "100%"
        }
    },
    {
        "name": "RAG版本管理测试",
        "test_data": {
            "stock_code": "600919",
            "data_updates": 3,
            "version_transitions": ["active", "deprecated", "archived"]
        },
        "expected_results": {
            "version_consistency": "100%",
            "vector_accuracy": ">95%",
            "query_relevance": ">90%"
        }
    }
]
```

### 性能基准测试
```python
# 性能测试指标
performance_benchmarks = {
    "cache_hit_rate": {
        "baseline": "30%",
        "target": "80%+",
        "measurement": "7天运行后统计"
    },
    "response_time": {
        "baseline": "5.0秒 (首次查询)",
        "target": "<0.5秒 (缓存命中)",
        "measurement": "自选股票查询时间"
    },
    "batch_processing_efficiency": {
        "target": "每小时处理1000+股票数据",
        "measurement": "夜间批处理吞吐量"
    },
    "rag_sync_latency": {
        "target": "<30秒 (数据更新到向量可查)",
        "measurement": "端到端RAG同步时间"
    }
}
```

## 📈 监控指标设计

### 核心业务指标
```python
business_metrics = {
    "watchlist_usage": {
        "active_watchlists": "每日活跃自选股列表数",
        "average_stocks_per_list": "平均每个列表股票数",
        "priority_distribution": "不同优先级列表分布"
    },
    "batch_performance": {
        "job_success_rate": "批处理任务成功率",
        "average_processing_time": "平均处理时间",
        "cache_hit_improvement": "缓存命中率提升"
    },
    "rag_effectiveness": {
        "vector_sync_success_rate": "向量同步成功率",
        "query_relevance_score": "查询相关性评分",
        "version_management_efficiency": "版本管理效率"
    }
}
```

### 技术性能指标
```python
technical_metrics = {
    "system_performance": {
        "memory_usage": "内存使用率",
        "cpu_utilization": "CPU使用率",
        "database_connection_pool": "数据库连接池状态"
    },
    "data_quality": {
        "data_freshness": "数据新鲜度",
        "data_completeness": "数据完整性",
        "error_rate_by_source": "各数据源错误率"
    }
}
```

## 🔧 开发环境设置

### 本地开发环境
```bash
# 1. 创建虚拟环境
cd /home/wyatt/prism2/backend
python -m venv batch_env
source batch_env/bin/activate

# 2. 安装依赖
pip install -r requirements_batch.txt

# 3. 环境变量配置
export BATCH_CONFIG_PATH="/home/wyatt/prism2/backend/batch_processor/config"
export DATABASE_URL="postgresql://prism2:prism2_secure_password@localhost:5432/prism2"
export REDIS_URL="redis://localhost:6379/1"
export CHROMADB_URL="http://localhost:8000"

# 4. 初始化数据库
python -m batch_processor.scripts.init_database

# 5. 启动服务
python batch_service.py
```

### Docker部署配置
```yaml
# docker-compose.batch.yml
services:
  batch-processor:
    build:
      context: ./backend
      dockerfile: Dockerfile.batch
    environment:
      - DATABASE_URL=postgresql://prism2:prism2_secure_password@postgres:5432/prism2
      - REDIS_URL=redis://redis:6379/1
      - CHROMADB_URL=http://chromadb:8000
    depends_on:
      - postgres
      - redis
      - chromadb
    volumes:
      - ./backend/batch_processor/config:/app/config
      - ./backend/batch_processor/logs:/app/logs
```

---

**📅 文档创建时间**: 2025-09-19 20:XX:XX
**👨‍💻 设计工程师**: Claude Code AI
**🎯 项目阶段**: Phase 2 → Phase 6 (批处理系统)
**📊 文档状态**: 设计完成，准备开发
**🔄 下一步**: 开始Phase 1基础框架搭建