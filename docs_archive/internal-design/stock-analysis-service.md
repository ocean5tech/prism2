# Stock Analysis Service - 内部设计文档

## 📋 基本信息

- **模块名称**: Stock Analysis Service (股票分析服务)
- **技术栈**: FastAPI + Python 3.12 + SQLAlchemy + Redis + WebSocket + AKShare
- **部署端口**: 8000
- **依据**: 外部设计文档规范

---

## 📁 文件结构和权限

```
/home/wyatt/prism2/stock-analysis-service/
├── app/                                    # 应用主目录 (755)
│   ├── __init__.py                        # (644)
│   ├── main.py                            # FastAPI应用入口 (644)
│   ├── api/                               # API路由层 (755)
│   │   └── v1/endpoints/                  # API端点 (755)
│   │       ├── stocks.py                  # 股票相关API (644)
│   │       ├── search.py                  # 搜索API (644)
│   │       ├── dashboard.py               # Dashboard API (644)
│   │       └── websocket.py               # WebSocket端点 (644)
│   ├── models/                            # SQLAlchemy模型 (755)
│   │   ├── stock.py                       # 股票数据模型 (644)
│   │   └── analysis.py                    # 分析结果模型 (644)
│   ├── schemas/                           # Pydantic模式 (755)
│   │   └── external_design.py             # 外部设计接口模式 (644)
│   ├── services/                          # 业务逻辑层 (755)
│   │   ├── stock_service.py               # 股票业务逻辑 (644)
│   │   ├── dashboard_service.py           # Dashboard业务逻辑 (644)
│   │   ├── akshare_service.py             # AKShare数据获取 (644)
│   │   └── websocket_service.py           # WebSocket管理 (644)
│   ├── tasks/                             # 后台任务 (755)
│   │   ├── data_updater.py                # 数据更新任务 (644)
│   │   └── websocket_pusher.py            # WebSocket推送任务 (644)
│   └── utils/                             # 工具函数 (755)
│       └── calculators.py                 # 技术指标计算 (644)
├── requirements.txt                       # 依赖配置 (644)
├── .env                                   # 环境变量 (600)
└── Dockerfile                            # Docker配置 (644)
```

---

## 🗄️ 数据库表设计

### 表1: stocks (股票基础信息表)
```sql
CREATE TABLE stocks (
    code VARCHAR(10) PRIMARY KEY,           -- 股票代码
    name VARCHAR(100) NOT NULL,             -- 股票名称
    full_name VARCHAR(200),                 -- 公司全称
    market VARCHAR(10) NOT NULL,            -- 市场 (SH/SZ/HK/US)
    industry VARCHAR(100),                  -- 行业
    market_cap BIGINT,                      -- 市值
    total_shares BIGINT,                    -- 总股本
    float_shares BIGINT,                    -- 流通股本
    listing_date DATE,                      -- 上市日期
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_stocks_market ON stocks(market);
CREATE INDEX idx_stocks_industry ON stocks(industry);
CREATE INDEX idx_stocks_name_gin ON stocks USING gin(to_tsvector('simple', name));
```

### 表2: ohlcv_data (K线数据表)
```sql
CREATE TABLE ohlcv_data (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    period VARCHAR(10) NOT NULL,            -- 1m/5m/15m/30m/1h/1d/1w/1M
    timestamp TIMESTAMP NOT NULL,
    open_price DECIMAL(10, 3) NOT NULL,
    high_price DECIMAL(10, 3) NOT NULL,
    low_price DECIMAL(10, 3) NOT NULL,
    close_price DECIMAL(10, 3) NOT NULL,
    volume BIGINT NOT NULL,
    turnover DECIMAL(20, 2) NOT NULL,
    FOREIGN KEY (stock_code) REFERENCES stocks(code),
    UNIQUE(stock_code, period, timestamp)
);

SELECT create_hypertable('ohlcv_data', 'timestamp');
CREATE INDEX idx_ohlcv_code_period_time ON ohlcv_data(stock_code, period, timestamp DESC);
```

### 表3: technical_indicators (技术指标表)
```sql
CREATE TABLE technical_indicators (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    period VARCHAR(10) NOT NULL,
    ma5 DECIMAL(10, 3),
    ma10 DECIMAL(10, 3),
    ma20 DECIMAL(10, 3),
    ma60 DECIMAL(10, 3),
    macd_diff DECIMAL(10, 6),
    macd_dea DECIMAL(10, 6),
    macd_macd DECIMAL(10, 6),
    rsi DECIMAL(8, 4),
    kdj_k DECIMAL(8, 4),
    kdj_d DECIMAL(8, 4),
    kdj_j DECIMAL(8, 4),
    boll_upper DECIMAL(10, 3),
    boll_middle DECIMAL(10, 3),
    boll_lower DECIMAL(10, 3),
    FOREIGN KEY (stock_code) REFERENCES stocks(code),
    UNIQUE(stock_code, period, timestamp)
);

SELECT create_hypertable('technical_indicators', 'timestamp');
```

### 表4: financial_reports (财务数据表)
```sql
CREATE TABLE financial_reports (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    period VARCHAR(10) NOT NULL,            -- 2024Q3/2024Q2/2024
    report_type VARCHAR(20) NOT NULL,       -- quarterly/annual
    publish_date DATE NOT NULL,
    revenue DECIMAL(20, 2),                 -- 营业收入
    net_profit DECIMAL(20, 2),              -- 净利润
    gross_profit_margin DECIMAL(8, 4),      -- 毛利率
    net_profit_margin DECIMAL(8, 4),        -- 净利率
    roe DECIMAL(8, 4),                      -- 净资产收益率
    roa DECIMAL(8, 4),                      -- 总资产收益率
    debt_ratio DECIMAL(8, 4),               -- 资产负债率
    eps DECIMAL(10, 4),                     -- 每股收益
    bps DECIMAL(10, 4),                     -- 每股净资产
    FOREIGN KEY (stock_code) REFERENCES stocks(code),
    UNIQUE(stock_code, period)
);
```

### 表5: company_info (公司详细信息表)
```sql
CREATE TABLE company_info (
    stock_code VARCHAR(10) PRIMARY KEY,
    full_name VARCHAR(200),
    english_name VARCHAR(200),
    establishment_date DATE,
    legal_representative VARCHAR(100),
    registered_capital BIGINT,
    employees_count INTEGER,
    main_business TEXT,
    business_scope TEXT,
    industry_classification VARCHAR(200),
    FOREIGN KEY (stock_code) REFERENCES stocks(code)
);
```

### 表6: ai_analysis_results (AI分析结果表)
```sql
CREATE TABLE ai_analysis_results (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,     -- comprehensive/technical/fundamental
    analysis_date TIMESTAMP NOT NULL,
    six_dimension_scores JSONB NOT NULL,    -- 六维度评分
    detailed_analysis JSONB NOT NULL,       -- 详细分析
    investment_recommendation JSONB NOT NULL, -- 投资建议
    reasoning_chain JSONB NOT NULL,         -- 推理链条
    confidence_level DECIMAL(4, 3) NOT NULL,
    expires_at TIMESTAMP NOT NULL,          -- 过期时间
    FOREIGN KEY (stock_code) REFERENCES stocks(code)
);

CREATE INDEX idx_ai_analysis_code_date ON ai_analysis_results(stock_code, analysis_date DESC);
```

### 表7: company_announcements (公司公告表)
```sql
CREATE TABLE company_announcements (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    announcement_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    announcement_type VARCHAR(50) NOT NULL,    -- 年报/季报/重大事项/股东变更
    publish_date DATE NOT NULL,
    content TEXT,
    pdf_url VARCHAR(500),
    source VARCHAR(50) NOT NULL,               -- 上交所/深交所/AKShare
    importance_level INTEGER DEFAULT 3,       -- 1-5重要性等级
    FOREIGN KEY (stock_code) REFERENCES stocks(code)
);

CREATE INDEX idx_announcements_code_date ON company_announcements(stock_code, publish_date DESC);
CREATE INDEX idx_announcements_type ON company_announcements(announcement_type);
```

### 表8: stock_news (股票新闻表)
```sql
CREATE TABLE stock_news (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10),                    -- 可为空(大盘新闻)
    news_id VARCHAR(200) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    content TEXT,
    publish_time TIMESTAMP NOT NULL,
    source VARCHAR(100) NOT NULL,              -- 新浪财经/财联社
    source_url VARCHAR(500),
    sentiment_score DECIMAL(4, 3),             -- 情感分析得分
    relevance_score DECIMAL(4, 3),             -- 相关性得分
    FOREIGN KEY (stock_code) REFERENCES stocks(code)
);

CREATE INDEX idx_news_code_time ON stock_news(stock_code, publish_time DESC);
CREATE INDEX idx_news_time ON stock_news(publish_time DESC);
```

### 表9: longhubang_data (龙虎榜数据表)
```sql
CREATE TABLE longhubang_data (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    rank_reason VARCHAR(200) NOT NULL,         -- 上榜原因
    buy_amount DECIMAL(20, 2) NOT NULL,        -- 买入金额
    sell_amount DECIMAL(20, 2) NOT NULL,       -- 卖出金额
    net_amount DECIMAL(20, 2) NOT NULL,        -- 净买入金额
    total_amount DECIMAL(20, 2) NOT NULL,      -- 成交总额
    seats_data JSONB NOT NULL,                 -- 营业部席位详情
    FOREIGN KEY (stock_code) REFERENCES stocks(code),
    UNIQUE(stock_code, trade_date)
);

CREATE INDEX idx_longhubang_code_date ON longhubang_data(stock_code, trade_date DESC);
```

### 表10: shareholder_changes (股东变更表)
```sql
CREATE TABLE shareholder_changes (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    shareholder_name VARCHAR(200) NOT NULL,
    shareholder_type VARCHAR(50) NOT NULL,     -- 个人/机构/基金
    change_date DATE NOT NULL,
    change_type VARCHAR(50) NOT NULL,          -- 增持/减持/新进/退出
    change_shares BIGINT NOT NULL,             -- 变动股数
    change_ratio DECIMAL(8, 4) NOT NULL,       -- 变动比例
    holdings_after BIGINT,                     -- 变动后持股数
    holdings_ratio DECIMAL(8, 4),              -- 变动后持股比例
    reason VARCHAR(500),                       -- 变动原因
    FOREIGN KEY (stock_code) REFERENCES stocks(code)
);

CREATE INDEX idx_shareholder_code_date ON shareholder_changes(stock_code, change_date DESC);
```

---

## 🔧 Redis缓存设计

### 缓存键规范
```python
CACHE_KEYS = {
    # 股票基础信息 (TTL: 1天)
    'STOCK_INFO': 'stock:info:{code}',

    # 公司详细信息 (TTL: 1天)
    'COMPANY_INFO': 'stock:company:{code}',

    # 财务数据 (TTL: 1天)
    'FINANCIAL_DATA': 'stock:financial:{code}',

    # K线数据 (TTL: 30分钟)
    'KLINE_DATA': 'stock:kline:{code}:{period}',

    # 公司公告 (TTL: 1天)
    'ANNOUNCEMENTS': 'stock:announcements:{code}',

    # 股票新闻 (TTL: 4小时)
    'STOCK_NEWS': 'stock:news:{code}',

    # 龙虎榜数据 (TTL: 1天)
    'LONGHUBANG': 'stock:longhubang:{code}',

    # 股东变更 (TTL: 1天)
    'SHAREHOLDERS': 'stock:shareholders:{code}',

    # AI分析结果 (TTL: 1天)
    'AI_ANALYSIS': 'ai:analysis:{code}:{type}',

    # 搜索结果 (TTL: 5分钟)
    'SEARCH_RESULTS': 'search:{query_hash}',

    # API限流 (TTL: 1分钟)
    'RATE_LIMIT': 'rate:{ip}:{endpoint}'
}
```

---

## 🔌 API端点实现 (严格按照外部设计)

### API1: 股票搜索
- **URL**: `POST /api/stock/search`
- **输入参数**: 外部设计的 `StockSearchRequest`
- **输出结果**: 外部设计的 `StockSearchResponse`
- **资源**: stocks表, Redis缓存
- **逻辑**:
  1. 检查缓存是否有搜索结果
  2. 根据query_type构建不同的SQL查询条件
  3. 从stocks表查询匹配记录
  4. 获取每只股票的实时价格(直接从AKShare API查询)
  5. 格式化结果并缓存5分钟
  6. 返回符合外部设计规范的响应格式

### API2: 获取基础数据 (非实时)
- **URL**: `GET /api/stock/{stock_code}/info`
- **输入参数**: stock_code (路径参数)
- **输出结果**: 外部设计的基础股票信息
- **资源**:
  - stocks表, company_info表 (本地数据库)
  - AKShare API (外部数据源)
- **逻辑**:
  1. 查询本地数据库中是否有该股票基础信息
  2. 检查数据是否需要更新 (超过24小时)
  3. 如果数据不存在或过期，调用AKShare API获取最新信息
  4. 将AKShare数据标准化并插入/更新到本地数据库
  5. 返回标准格式的股票基础信息

### API3: Dashboard完整数据
- **URL**: `POST /api/stock/dashboard`
- **输入参数**: 外部设计的 `DashboardDataRequest`
- **输出结果**: 外部设计的 `DashboardDataResponse`
- **资源**:
  - stocks表, company_info表 (公司信息)
  - ohlcv_data表 (K线数据)
  - financial_reports表 (财务数据)
  - ai_analysis_results表 (AI分析)
- **逻辑**:
  1. 根据data_types参数并行获取不同类型数据
  2. 如果包含realtime: 调用实时数据获取逻辑
  3. 如果包含kline: 从ohlcv_data表获取指定周期的K线数据
  4. 如果包含company_info: 从stocks和company_info表获取公司详细信息
  5. 如果包含financial: 从financial_reports表获取最近2期财报
  6. 如果包含ai_analysis: 从ai_analysis_results表获取或触发新的AI分析
  7. 组装完整响应数据

### API4: WebSocket实时数据推送
- **URL**: `WebSocket ws://localhost:8000/ws/stock-data`
- **输入参数**: 外部设计的订阅消息
  ```json
  {
    "type": "subscribe",
    "stock_codes": ["000001", "000002"],
    "data_types": ["price", "kline", "indicators"]
  }
  ```
- **输出结果**: 实时数据推送
  ```json
  {
    "type": "price_update",
    "stock_code": "000001",
    "data": {实时价格数据},
    "timestamp": "2025-09-16T10:00:00Z"
  }
  ```
- **资源**:
  - AKShare实时数据 (如果有WebSocket支持)
  - 定时轮询AKShare API作为备选方案
  - Redis发布订阅机制
- **逻辑**:
  1. 前端建立WebSocket连接并发送订阅消息
  2. 服务端维护活跃连接列表和订阅股票清单
  3. 后台任务定时 (每5-30秒) 从AKShare获取最新数据
  4. 比较数据是否有变化，有变化则通过WebSocket推送给订阅的前端
  5. 同时更新本地数据库和Redis缓存

### API5: K线数据获取 (历史数据)
- **URL**: `GET /api/stock/{stock_code}/kline`
- **输入参数**: stock_code, period, limit (查询参数)
- **输出结果**: 外部设计的 `KLineData`
- **资源**:
  - ohlcv_data表 (本地存储)
  - AKShare API (外部数据源)
- **逻辑**:
  1. 查询本地数据库是否有足够的K线数据
  2. 如果数据不足或过期，调用AKShare获取历史K线数据
  3. 使用技术指标计算器计算MA、MACD、RSI等指标
  4. 将数据存储到本地数据库
  5. 返回格式化的K线数据和技术指标

---

## 🚀 业务逻辑服务

### AKShareService (AKShare数据获取服务)
- **文件**: `app/services/akshare_service.py`
- **功能**: 统一管理AKShare API调用和数据标准化
- **依赖**: akshare库, 数据库ORM
- **核心方法**:
  - `get_stock_info(code)`: 获取股票基础信息，检查本地数据库→AKShare API→更新数据库
  - `get_realtime_price(code)`: 获取实时价格数据
  - `get_historical_kline(code, period, limit)`: 获取历史K线数据
  - `get_financial_data(code)`: 获取财务报表数据
  - `check_and_update_stock(code)`: 检查股票是否存在，不存在则从AKShare获取并入库
- **数据缓存策略**:
  - 基础信息缓存24小时
  - 财务数据缓存7天
  - 实时价格不缓存 (通过WebSocket推送)

### StockService (股票业务逻辑)
- **文件**: `app/services/stock_service.py`
- **功能**: 处理股票搜索、基础信息获取、数据组装
- **依赖**: AKShareService, SQLAlchemy ORM, Redis缓存
- **核心方法**:
  - `search_stocks()`: 本地搜索→AKShare搜索→结果合并
  - `get_stock_info()`: 本地查询→AKShare补全→标准化返回
  - `ensure_stock_exists()`: 确保股票在本地数据库中存在

### WebSocketService (WebSocket连接管理)
- **文件**: `app/services/websocket_service.py`
- **功能**: 管理WebSocket连接和实时数据推送
- **依赖**: FastAPI WebSocket, Redis发布订阅
- **核心方法**:
  - `add_connection()`: 添加WebSocket连接
  - `remove_connection()`: 移除连接
  - `subscribe_stocks()`: 订阅股票实时数据
  - `broadcast_update()`: 广播数据更新到订阅的连接
  - `get_active_subscriptions()`: 获取当前活跃订阅列表

### DashboardService (Dashboard业务逻辑)
- **文件**: `app/services/dashboard_service.py`
- **功能**: 组装Dashboard页面所需的完整数据
- **依赖**: StockService, AKShareService, AIService客户端, RAGService客户端
- **核心方法**:
  - `get_dashboard_data()`: 并行获取多种类型数据
  - `get_kline_data()`: 本地查询→AKShare补全→计算技术指标
  - `get_company_info()`: 本地查询→AKShare补全
  - `get_financial_data()`: 本地查询→AKShare补全
  - `prepare_ai_analysis_data()`: AI分析数据准备和充分性检查
  - `check_data_completeness()`: 检查PostgreSQL中股票数据完整性
  - `trigger_full_data_collection()`: 数据不足时触发AKShare全量采集

### AIAnalysisService (AI分析数据准备服务)
- **文件**: `app/services/ai_analysis_service.py`
- **功能**: 专门处理AI分析的数据准备和生成
- **依赖**: PostgreSQL ORM, AKShareService, RAGService客户端
- **核心方法**:
  - `check_analysis_cache()`: 检查Redis中的AI分析缓存
  - `assess_data_completeness()`: 评估PostgreSQL数据完整性
    - 检查基础信息、财务数据、公告、新闻、龙虎榜、股东变更
    - 返回数据完整性评分(0-100%)
  - `collect_missing_data()`: 股票信息为零时的全量数据采集
    - 从AKShare获取所有历史数据
    - 批量存储到PostgreSQL
    - 触发RAG向量化处理
  - `assemble_analysis_context()`: 组装AI分析上下文
    - 从PostgreSQL获取历史数据
    - 从AKShare获取实时价格
    - 从RAG Service获取相关文档
    - 生成标准化分析数据包
  - `generate_ai_analysis()`: 调用AI Service生成分析
    - 发送完整上下文到AI Service
    - 接收六维度分析结果
    - 存储到ai_analysis_results表
    - 更新Redis缓存(TTL: 1天)

---

## 🔄 外部服务依赖

### 依赖1: AI Service (端口11434)
- **用途**: AI分析生成
- **接口**: `POST /api/generate`
- **调用时机**: Dashboard请求ai_analysis数据且缓存过期时
- **错误处理**: AI服务不可用时返回缓存的历史分析结果

### 依赖2: RAG Service (端口8001)
- **用途**: 为AI分析提供上下文信息
- **接口**: `POST /api/rag/search`
- **调用时机**: 生成AI分析前获取相关文档
- **错误处理**: RAG服务不可用时使用基础分析模式

### 依赖3: Data Service (端口8003)
- **用途**: 获取外部实时数据
- **接口**: `GET /api/data/stocks/{code}/realtime`
- **调用时机**: 本地数据过期时
- **错误处理**: 数据服务不可用时使用本地缓存数据

### 依赖4: Authentication Service (端口8004)
- **用途**: 用户认证和权限验证
- **接口**: JWT token验证
- **调用时机**: 每个需要认证的API请求
- **错误处理**: 认证失败返回401错误

---

## 🔄 后台任务

### NightlyBatchCrawler (夜间批处理爬取任务)
- **文件**: `app/tasks/nightly_crawler.py`
- **功能**: 夜间批量爬取和更新历史性数据
- **执行时间**: 每日凌晨2:00-6:00 (非交易时间)
- **数据类型**:
  - 股票基础信息 (上市公司列表、行业分类、公司详情)
  - 财务报表数据 (季报、年报、业绩预告)
  - 公司公告 (重大事项、股东变更、分红派息)
  - 龙虎榜数据 (大单交易、机构席位)
  - 新闻资讯 (公司新闻、行业动态)
  - 历史K线数据补全
- **执行逻辑**:
  1. **2:00-2:30**: 更新股票基础信息列表
  2. **2:30-3:30**: 批量获取财务报表数据
  3. **3:30-4:30**: 爬取公司公告和新闻
  4. **4:30-5:30**: 获取龙虎榜和股东数据
  5. **5:30-6:00**: 数据质量检查和RAG向量化
- **数据来源**:
  - AKShare API (主要数据源)
  - 新浪财经RSS (有效新闻源)
  - 交易所官方API (公告数据)

### DataUpdater (实时数据更新任务)
- **文件**: `app/tasks/data_updater.py`
- **功能**: 交易时间内的实时数据获取和WebSocket推送
- **执行频率**: 仅在交易时间运行
  - K线数据: 每5分钟
  - 技术指标计算: 每5分钟
- **逻辑**:
  1. 获取当前活跃订阅的股票列表
  2. 批量调用AKShare API获取K线数据
  3. 计算技术指标并更新数据库
  4. 通知WebSocketPusher推送更新

### WebSocketPusher (实时推送任务)
- **文件**: `app/tasks/websocket_pusher.py`
- **功能**: 将数据变化推送给WebSocket连接
- **触发方式**: 接收Redis发布的数据更新消息
- **逻辑**:
  1. 监听Redis发布的数据更新事件
  2. 获取该股票的所有WebSocket订阅连接
  3. 格式化数据并推送给前端
  4. 处理连接断开和错误情况

## 📊 数据流设计

### 统一数据查询优先级: Redis → PostgreSQL → AKShare

所有数据查询都遵循三级优先级策略：

#### 1️⃣ Redis缓存查询 (第一优先级)
- **查询时间**: < 1ms
- **适用数据**: 所有已缓存的数据
- **命中策略**: 直接返回缓存结果
- **失效处理**: 缓存未命中或过期时进入第二级

#### 2️⃣ PostgreSQL数据库查询 (第二优先级)
- **查询时间**: 10-50ms
- **适用数据**: 历史性、变化较少的数据
- **命中策略**: 返回数据库结果并更新Redis缓存
- **失效处理**: 数据不存在或过期时进入第三级

#### 3️⃣ AKShare API查询 (第三优先级)
- **查询时间**: 200-2000ms
- **适用数据**: 实时价格、最新数据
- **命中策略**: 获取最新数据，更新PostgreSQL和Redis
- **失效处理**: API失败时返回PostgreSQL历史数据

### 具体数据类型的查询流程

#### 🏢 基础数据查询流程 (公司信息、财务数据、公告等)
```
用户请求 → Redis查询 → 命中?
   ↓ 未命中
PostgreSQL查询 → 存在且未过期?
   ↓ 不存在/过期
AKShare API → 获取最新数据 → 更新PostgreSQL → 更新Redis → 返回结果
```

#### 💰 实时价格查询流程 (价格、成交量)
```
用户请求 → 直接调用AKShare API → 返回结果
(不存储在PostgreSQL和Redis中，始终获取最新数据)
```

#### 📈 K线数据查询流程
```
用户请求 → Redis查询 → 命中且未过期?
   ↓ 未命中/过期
PostgreSQL查询 → 数据完整且最新?
   ↓ 不完整/过期
AKShare API → 获取缺失数据 → 补全PostgreSQL → 更新Redis → 返回结果
```

#### 🤖 AI分析数据准备和查询流程
```
用户请求AI分析 → Redis查询分析结果 → 命中且未过期(1天)?
   ↓ 未命中/过期
PostgreSQL数据充分性检查:
   - 基础信息(stocks + company_info)
   - 财务数据(financial_reports)
   - 公司公告(announcements)
   - 龙虎榜数据(longhubang_data)
   - 股东变更(shareholder_changes)
   - 股票新闻(stock_news)

数据充分 → 有RAG向量化信息?
   ↓ 数据不足 → 股票信息为零
AKShare API全量获取 → 批量存储到PostgreSQL → RAG向量化

数据准备完成 → 获取AKShare实时价格 → 组装分析数据包:
   {
     "基础信息": PostgreSQL数据,
     "财务数据": PostgreSQL数据,
     "历史新闻": PostgreSQL数据,
     "实时价格": AKShare数据,
     "RAG上下文": 相关向量化文档
   }
   ↓
调用AI Service生成分析 → 存储到ai_analysis_results → 更新Redis → 返回结果
```

### 实时数据推送流程 (仅交易时间)
1. WebSocket连接建立 → 记录订阅信息
2. 定时任务(每30秒) → 直接调用AKShare获取实时价格
3. 价格变化检测 → 通过WebSocket推送给订阅客户端
4. 不存储实时价格数据 (直接透传)

---

## ⚡ 性能优化

### 数据库优化
- **索引策略**: 为常用查询字段创建合适索引
- **分区策略**: 使用TimescaleDB对时序数据分区
- **连接池**: SQLAlchemy连接池配置 (pool_size=20)

### 缓存优化
- **分层缓存**: Redis + 应用内存缓存
- **缓存预热**: 定时任务预热热门股票数据
- **缓存穿透保护**: 空结果也缓存一定时间

### 并发优化
- **异步处理**: 使用asyncio并行获取不同类型数据
- **连接复用**: HTTP客户端连接池复用
- **限流保护**: API级别的限流防护

---

## 🔒 配置管理

### 环境变量 (.env)
```bash
# 数据库配置
DATABASE_URL=postgresql://user:pass@postgres:5432/prism2

# Redis配置
REDIS_URL=redis://redis:6379/0

# 外部服务 (对应外部设计端口)
AI_SERVICE_URL=http://ollama:11434
RAG_SERVICE_URL=http://rag-service:8001
DATA_SERVICE_URL=http://data-service:8003
AUTH_SERVICE_URL=http://auth-service:8004

# 缓存TTL配置
CACHE_TTL_BASIC_INFO=86400
CACHE_TTL_COMPANY_INFO=86400
CACHE_TTL_FINANCIAL_DATA=86400
CACHE_TTL_AI_ANALYSIS=86400
CACHE_TTL_KLINE=1800

# API限流配置
RATE_LIMIT_PER_MINUTE=100
```

---

*文档更新时间: 2025-09-16*
*严格遵循外部设计规范，确保模块间接口一致性*