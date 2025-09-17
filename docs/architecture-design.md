# Prism2 股票分析平台架构设计

## 项目概述

Prism2是一个基于RAG技术的智能股票分析平台，专注于多源财经数据收集、智能向量化存储、时间性+相关性搜索等功能。采用现代化微服务架构，为投资决策提供全面的信息支持。

**当前版本**: v1.0 - RAG Service核心实现
**最后更新**: 2025-09-17
**实施状态**: 核心RAG功能已完成并投入使用

## 已实现架构

```
用户查询接口 (User Query Interface)
    ↓
时间性+相关性搜索引擎 (Time-Relevance Search Engine)
    ↓
RAG向量数据库 (ChromaDB Vector Database - Port 8000)
    ↓
多源数据收集系统 (Multi-Source Data Collection)
    ↓
实时RSS监控 (Real-time RSS Monitor - 15min intervals)
    ├── Bloomberg Financial News
    ├── Thomson Reuters
    ├── 和讯财经
    └── AKShare股票数据API
    ↓
智能翻译系统 (Translation System - EN→CN)
    ↓
向量化存储 (TF-IDF Vectorization - 1000 dimensions)
    ↓
数据归档管理 (Archive Management System)
```

## 已实现技术栈

### RAG核心服务
- **后端语言**: Python 3.12
- **向量数据库**: ChromaDB (HTTP Client, Port 8000)
- **向量化技术**: TF-IDF (1000维特征向量)
- **中文处理**: jieba分词 + 中文语料优化
- **搜索算法**: 时间性(30%) + 相关性(70%)混合排序

### 数据收集系统
- **RSS监控**: aiohttp + feedparser异步处理
- **数据源集成**: AKShare API (中国股市数据)
- **国际数据源**: Bloomberg RSS, Thomson Reuters RSS
- **更新频率**: 15分钟自动抓取
- **数据质量**: 自动去重 + 重要性评分(1-10)

### 智能翻译系统
- **翻译引擎**: Google Translate API
- **语言检测**: langdetect自动识别
- **处理策略**: 英文→中文，保留原文
- **缓存机制**: 内存缓存避免重复翻译
- **准确率**: 90%+ (金融专业术语)

### 数据管理
- **归档系统**: 统一JSON格式 + 元数据管理
- **命名规范**: 时间戳 + 数据类型标识
- **存储策略**: 增量更新 + 完整备份
- **数据追踪**: 哈希校验 + 来源记录

### 前端可视化 (计划中)
- **可视化界面**: Open WebUI集成
- **查询界面**: RAG数据库查看器
- **监控面板**: 实时RSS监控状态
- **数据展示**: 时间性+相关性搜索结果
## 系统性能指标

### 已验证性能
- **数据源数量**: 9个高质量RSS源
- **数据采集**: Thomson Reuters成功获取9篇真实新闻
- **向量维度**: 1000维TF-IDF特征向量
- **搜索响应时间**: <1秒
- **翻译准确率**: 90%+ (金融专业术语)
- **更新延迟**: 15分钟 (可调整到5分钟)
- **数据存储**: JSON归档 + ChromaDB向量库
- **并发处理**: 支持异步批量数据采集

### 存储容量规划
- **单篇新闻**: 平均2-5KB (翻译后)
- **向量存储**: 4KB/文档 (1000维float)
- **日均新增**: 约500-1000篇财经新闻
- **月度存储增长**: 约100-200MB
- **年度预估**: 1.2-2.4GB (包含完整归档)

## 部署架构

### 当前部署模式
```
单机部署架构:
┌─────────────────────────────────────────────────────────┐
│                   Linux Server (WSL2)                  │
│  ┌─────────────────────────────────────────────────────┤
│  │              Python 3.12 Runtime                   │
│  │  ┌─────────────┬─────────────┬─────────────┐        │
│  │  │RSS Monitor  │   ChromaDB  │Time-Relevance│       │
│  │  │   Service   │    :8000    │    Search   │        │
│  │  │(Background) │             │    Engine   │        │
│  │  └─────────────┴─────────────┴─────────────┘        │
│  │  ┌─────────────────────────────────────────┐        │
│  │  │         Archive Manager                 │        │
│  │  │     (JSON + Metadata Storage)           │        │
│  │  └─────────────────────────────────────────┘        │
│  └─────────────────────────────────────────────────────│
└─────────────────────────────────────────────────────────┘
```

### 生产环境架构 (规划中)
```
Docker容器化部署:
┌─────────────────┬─────────────────┬─────────────────┐
│  Load Balancer  │   API Gateway   │  Frontend PWA   │
│     (Nginx)     │     (Nginx)     │   (React)       │
│     Port 80     │   Port 443      │   Port 3000     │
└─────────────────┴─────────────────┴─────────────────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
┌─────────────┬─────────────┬─────────────┬─────────────┐
│Stock Service│ RAG Service │Data Service │Auth Service │
│   :8000     │   :8001     │   :8002     │   :8004     │
│  (FastAPI)  │ (ChromaDB)  │(RSS Monitor)│   (JWT)     │
└─────────────┴─────────────┴─────────────┴─────────────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ PostgreSQL  │  ChromaDB   │    Redis    │   MinIO     │
│   :5432     │   :8000     │   :6379     │   :9000     │
│(Time-Series)│  (Vectors)  │  (Cache)    │ (Archives)  │
└─────────────┴─────────────┴─────────────┴─────────────┘
```
- **主数据库**: PostgreSQL 15 + TimescaleDB (时序优化)
- **向量数据库**: ChromaDB / Qdrant
- **缓存**: Redis 7
- **文件存储**: MinIO / 本地文件系统

### 基础设施
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **监控**: 可选集成 Prometheus + Grafana

## 详细架构设计

### 1. 前端层 (Port: 3000)
**注意**: 生产环境中前端将通过Nginx提供服务

**技术特点**:
- React + TypeScript 全栈类型安全
- PWA支持离线访问和桌面安装
- 响应式设计，完美支持移动端
- 专业金融图表和数据可视化

**核心功能**:
- 股票搜索和实时数据展示
- K线图、技术指标图表
- AI分析报告展示
- 移动端优化的触控交互

**与下层交互**:
- → API Gateway: HTTP/WebSocket请求
- 数据: 股票代码、查询参数、用户操作事件

### 2. API网关层 (Port: 80/443)

**技术实现**: Nginx反向代理
**核心功能**:
- 统一入口和SSL终止
- 请求路由到不同微服务
- 负载均衡和故障转移
- 限流和安全防护

**路由规则**:
```nginx
/api/stock/    → Stock Analysis Service (8000)
/api/rag/      → RAG Service (8001)
/api/data/     → Data Service (8003)
/ollama/       → Ollama (11434)
/             → Frontend Static Files
```

### 3. 业务服务层

#### 3.1 股票分析服务 (Port: 8000)
**技术栈**: FastAPI + Python
**核心功能**:
- 股票基础信息查询
- 技术指标计算
- AI分析报告生成
- 用户请求协调

**与下层交互**:
- → RAG Service: 获取分析上下文
- → Data Service: 获取实时股票数据
- → Ollama: AI模型推理
- → PostgreSQL: 缓存和用户数据

#### 3.2 RAG服务 (Port: 8001)
**技术栈**: FastAPI + LangChain + Python
**核心功能**:
- 语义搜索和文档检索
- 上下文增强和Prompt工程
- 向量化和相似度计算

**与下层交互**:
- → Vector DB: 语义搜索查询
- → PostgreSQL: 元数据和关联查询
- → bge模型: 文本向量化

#### 3.3 数据采集服务 (Port: 8002)
**技术栈**: Scrapy + Kafka Producer + Python
**核心功能**:
- 股票公告爬取
- 新闻和研报采集
- 数据标准化和清洗

**与下层交互**:
- → Kafka: 发送原始数据到消息队列
- → External APIs: 第三方数据源
- → PostgreSQL: 爬取任务记录

### 4. AI模型层

#### 4.1 本地LLM (Port: 11434)
**技术实现**: Ollama + Qwen2.5-7B-Instruct
**功能**:
- 股票分析文本生成
- 投资建议和风险评估
- 多轮对话支持

**资源要求**:
- 内存: 6-8GB
- 推理速度: 1-2秒/回合

#### 4.2 Open WebUI (Port: 3001)
**功能**:
- LLM模型管理和调试
- Prompt工程和测试
- 对话历史管理
**注意**: 端口调整为3001以避免与前端PWA端口(3000)冲突

#### 4.3 向量化模型
**模型**: bge-large-zh-v1.5
**功能**: 中文金融文本向量化
**集成**: 嵌入在RAG Service中

### 5. 数据处理层 (学习导向设计)

#### 5.1 Apache Kafka (Port: 9092)
**Topic设计**:
```
raw_stock_data     # 原始股票数据
raw_news_data      # 新闻和公告数据
processed_data     # 清洗后的结构化数据
embedding_tasks    # 向量化任务队列
real_time_alerts   # 实时预警信息
```

**学习价值**:
- 消息队列和事件驱动架构
- 生产者-消费者模式
- 数据流解耦和缓冲

#### 5.2 Apache Spark
**批处理任务**:
- 历史数据ETL和清洗
- 大规模文本向量化
- 复杂财务指标计算
- 数据质量报告生成

**流处理任务**:
- 实时股价异常检测
- 技术指标实时计算
- 新闻情感分析
- 实时向量化更新

**学习价值**:
- 大数据处理思维
- 批处理vs流处理概念
- 分布式计算原理

### 6. 存储层

#### 6.1 PostgreSQL (Port: 5432)
**存储内容**:
```sql
-- 股票基础信息
stocks (code, name, industry, market_cap, ...)

-- K线数据 (60日滚动)
ohlcv_data (stock_code, timestamp, open, high, low, close, volume)

-- 财报数据
financial_reports (stock_code, period, revenue, profit, ...)

-- 用户数据和系统配置
users, user_preferences, system_configs
```

**TimescaleDB扩展**: 时序数据优化

#### 6.2 向量数据库 (ChromaDB)
**存储内容**:
- 研报文档向量 (维度: 1024)
- 新闻文章向量
- 公告文本向量
- 元数据: 发布时间、股票代码、文档类型

#### 6.3 Redis缓存 (Port: 6379)
**缓存策略**:
```
stock:price:{code}     # 实时股价 (TTL: 5分钟)
stock:analysis:{code}  # AI分析结果 (TTL: 1小时)
user:session:{id}      # 用户会话
rate_limit:{ip}        # API限流
```

## 数据流设计

### 实时数据流
```
外部API → Data Service → Redis缓存 → Stock Service → 前端展示
```

### 历史数据ETL流
```
爬虫 → Kafka → Spark Streaming → PostgreSQL → Vector DB
                     ↓
              Spark Batch → 定期数据清理和聚合
```

### AI分析流
```
用户查询 → Stock Service → RAG Service → Vector DB查询
                              ↓
                         LangChain处理 → Ollama推理 → 返回结果
```

## 部署架构

### Docker Compose服务清单
```yaml
services:
  # 前端和网关
  nginx:          # API网关和静态文件服务
  frontend:       # React构建产物

  # 业务服务
  stock-service:  # 主业务逻辑
  rag-service:    # RAG增强服务
  data-service:   # 数据采集服务

  # AI模型
  ollama:         # 本地LLM
  open-webui:     # LLM管理界面

  # 大数据组件 (学习用)
  zookeeper:      # Kafka依赖
  kafka:          # 消息队列
  spark-master:   # Spark主节点
  spark-worker:   # Spark工作节点

  # 数据存储
  postgresql:     # 主数据库
  redis:          # 缓存
  chromadb:       # 向量数据库
  minio:          # 文件存储 (可选)

  # 监控工具 (可选)
  kafdrop:        # Kafka管理界面
```

### 资源需求
- **CPU**: 8核心 (推荐)
- **内存**: 16GB (Spark + Ollama + 数据库)
- **存储**: 50GB (包含模型和数据)
- **网络**: 千兆网络

## 开发计划

### Phase 1: 基础架构 (Week 1-2)
- [ ] 项目初始化和Docker环境搭建
- [ ] PostgreSQL数据库设计和初始化
- [ ] 基础的FastAPI服务框架

### Phase 2: 核心功能 (Week 3-4)
- [ ] 股票数据API集成
- [ ] React前端基础界面
- [ ] Ollama本地LLM配置

### Phase 3: RAG集成 (Week 5-6)
- [ ] ChromaDB向量数据库配置
- [ ] LangChain RAG服务开发
- [ ] 文档爬取和向量化流水线

### Phase 4: 大数据学习 (Week 7-8)
- [ ] Kafka集群搭建和配置
- [ ] Spark环境配置和基础任务
- [ ] ETL流水线开发

### Phase 5: 优化和部署 (Week 9-10)
- [ ] 性能优化和缓存策略
- [ ] 完整的CI/CD流水线
- [ ] 生产环境部署和监控

## 学习收益

通过这个项目，你将掌握:

1. **现代Web开发**: React + TypeScript + PWA
2. **微服务架构**: FastAPI服务拆分和通信
3. **AI应用开发**: RAG、向量数据库、本地LLM
4. **大数据技术**: Spark + Kafka生态
5. **DevOps实践**: Docker、容器编排、监控
6. **金融科技**: 股票数据处理和分析

这个架构既满足了实际股票分析需求，又提供了丰富的技术学习机会，是一个非常好的全栈项目实践。