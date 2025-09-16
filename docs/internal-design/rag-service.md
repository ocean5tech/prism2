# RAG Service - 内部设计文档

## 📋 基本信息

- **模块名称**: RAG Service (检索增强生成服务)
- **技术栈**: FastAPI + LangChain + ChromaDB + bge-large-zh-v1.5
- **部署端口**: 8001
- **依据**: 外部设计文档规范

---

## 📁 文件结构和权限

```
/home/wyatt/prism2/rag-service/
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
│   │       ├── rag.py                    # RAG相关端点 (644)
│   │       └── health.py                 # 健康检查端点 (644)
│   ├── services/                         # 业务服务层 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── vector_service.py             # 向量检索服务 (644)
│   │   ├── embedding_service.py          # 文档嵌入服务 (644)
│   │   ├── rag_service.py                # RAG核心服务 (644)
│   │   └── context_service.py            # 上下文增强服务 (644)
│   ├── models/                           # 数据模型 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── requests.py                   # 请求模型 (644)
│   │   └── responses.py                  # 响应模型 (644)
│   └── utils/                            # 工具函数 (755)
│       ├── __init__.py                   # (644)
│       ├── text_processing.py            # 文本处理工具 (644)
│       └── similarity.py                 # 相似度计算 (644)
├── data/                                 # 数据目录 (755)
│   ├── models/                           # 模型文件存储 (755)
│   └── collections/                      # ChromaDB集合 (755)
├── requirements.txt                      # Python依赖 (644)
├── Dockerfile                           # 容器化配置 (644)
└── .env                                 # 环境变量 (600)
```

---

## 🗄️ 数据库表设计 (支持初始化和增量更新)

### 系统初始化任务表 (bootstrap_tasks)
```sql
CREATE TABLE bootstrap_tasks (
    id SERIAL PRIMARY KEY,
    task_id UUID UNIQUE NOT NULL,           -- 任务唯一ID
    data_sources JSONB NOT NULL,            -- 数据源配置
    time_range JSONB NOT NULL,              -- 时间范围配置
    status VARCHAR(20) DEFAULT 'pending',   -- pending/running/completed/failed
    progress_percentage FLOAT DEFAULT 0,    -- 完成百分比
    processed_documents INTEGER DEFAULT 0,  -- 已处理文档数
    total_documents INTEGER DEFAULT 0,      -- 总文档数
    current_stage VARCHAR(50),              -- 当前处理阶段
    stages_completed JSONB DEFAULT '[]',    -- 已完成阶段列表
    error_count INTEGER DEFAULT 0,          -- 错误计数
    error_details JSONB,                    -- 错误详情
    start_time TIMESTAMP DEFAULT NOW(),     -- 开始时间
    estimated_completion TIMESTAMP,         -- 预估完成时间
    actual_completion TIMESTAMP,            -- 实际完成时间
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_bootstrap_tasks_task_id ON bootstrap_tasks(task_id);
CREATE INDEX idx_bootstrap_tasks_status ON bootstrap_tasks(status);
CREATE INDEX idx_bootstrap_tasks_created_at ON bootstrap_tasks(created_at);
```

### 批量处理记录表 (batch_processing_logs)
```sql
CREATE TABLE batch_processing_logs (
    id SERIAL PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES bootstrap_tasks(task_id),
    batch_number INTEGER NOT NULL,          -- 批次号
    data_source VARCHAR(50) NOT NULL,       -- 数据源类型
    batch_size INTEGER NOT NULL,            -- 批次大小
    processing_status VARCHAR(20) NOT NULL, -- processing/completed/failed
    documents_processed INTEGER DEFAULT 0,  -- 已处理文档数
    documents_failed INTEGER DEFAULT 0,     -- 失败文档数
    start_time TIMESTAMP DEFAULT NOW(),
    completion_time TIMESTAMP,
    processing_time_seconds INTEGER,        -- 处理耗时(秒)
    error_message TEXT,                     -- 错误信息
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_batch_logs_task_id ON batch_processing_logs(task_id);
CREATE INDEX idx_batch_logs_status ON batch_processing_logs(processing_status);
```

### 文档质量评估表 (document_quality_scores)
```sql
CREATE TABLE document_quality_scores (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) UNIQUE NOT NULL, -- 文档ID
    data_source VARCHAR(50) NOT NULL,         -- 数据源类型
    content_length INTEGER NOT NULL,          -- 内容长度
    readability_score FLOAT,                  -- 可读性评分(0-1)
    relevance_score FLOAT,                    -- 相关性评分(0-1)
    information_density FLOAT,                -- 信息密度评分(0-1)
    overall_quality FLOAT NOT NULL,           -- 综合质量评分(0-1)
    quality_tags JSONB,                       -- 质量标签
    is_filtered BOOLEAN DEFAULT FALSE,        -- 是否被过滤
    filter_reason TEXT,                       -- 过滤原因
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_quality_document_id ON document_quality_scores(document_id);
CREATE INDEX idx_quality_source ON document_quality_scores(data_source);
CREATE INDEX idx_quality_score ON document_quality_scores(overall_quality);
```

---

## 🔌 API接口定义 (严格按照外部设计)

### 基础配置
```python
# 服务配置
CHROMADB_HOST = os.getenv('CHROMADB_HOST', 'localhost')
CHROMADB_PORT = int(os.getenv('CHROMADB_PORT', '8000'))
EMBEDDING_MODEL_PATH = os.getenv('EMBEDDING_MODEL_PATH', './data/models/bge-large-zh-v1.5')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'financial_documents')
```

### API1: 语义搜索 (对接外部设计接口)
- **URL**: `POST /api/rag/search`
- **输入参数**: 严格按照外部设计的RAG搜索请求
  ```python
  class RAGSearchRequest(BaseModel):
      query: str                         # 查询文本
      stock_code: Optional[str] = None   # 关联股票代码
      search_type: str = "semantic"      # 搜索类型: semantic/keyword/hybrid
      limit: int = 5                     # 返回结果数量
      similarity_threshold: float = 0.7   # 相似度阈值
      filters: Optional[Dict[str, Any]] = None  # 元数据过滤条件
  ```
- **输出结果**: 外部设计的RAGSearchResponse
  ```python
  class DocumentMatch(BaseModel):
      document_id: str
      content: str
      similarity_score: float
      metadata: Dict[str, Any]

  class RAGSearchResponse(BaseModel):
      results: List[DocumentMatch]
      query_embedding: List[float]
      search_time: float
      total_documents: int
  ```
- **资源**: ChromaDB向量数据库集合
- **逻辑**: 接收用户查询文本，使用bge-large-zh-v1.5生成查询向量，在ChromaDB中检索最相似的文档片段，返回排序后的匹配结果

### API2: 文档嵌入 (对接News Service数据)
- **URL**: `POST /api/rag/embed`
- **输入参数**: 外部设计的文档嵌入请求
  ```python
  class DocumentEmbedRequest(BaseModel):
      documents: List[Dict[str, Any]]    # 文档列表
      collection_name: Optional[str] = None  # 目标集合名称

  class DocumentInput(BaseModel):
      id: str                           # 唯一文档ID
      content: str                      # 文档文本内容
      metadata: Dict[str, Any]          # 元数据(股票代码、文档类型等)
  ```
- **输出结果**: 嵌入处理状态
  ```python
  class EmbedResponse(BaseModel):
      success: bool
      processed_count: int
      failed_documents: List[str]
      processing_time: float
  ```
- **资源**: bge-large-zh-v1.5向量模型、ChromaDB存储
- **逻辑**: 批量接收文档，使用bge模型生成向量表示，存储到ChromaDB指定集合中，支持增量更新和重复文档检测

### API3: 系统初始化 (Bootstrap大量历史数据)
- **URL**: `POST /api/rag/bootstrap`
- **输入参数**: 初始化配置请求
  ```python
  class BootstrapRequest(BaseModel):
      data_sources: List[str]               # 要初始化的数据源类型
      time_range: Dict[str, str]           # 时间范围配置
      batch_size: int = 100                # 批处理大小
      max_concurrent: int = 5              # 最大并发数
      enable_quality_filter: bool = True   # 启用质量过滤
  ```
- **输出结果**: 初始化任务状态
  ```python
  class BootstrapResponse(BaseModel):
      task_id: str                         # 任务ID
      estimated_documents: int             # 预估文档数量
      estimated_time_hours: float          # 预估完成时间
      status: str                          # 任务状态
      progress_url: str                    # 进度查询URL
  ```
- **资源**: 多线程爬虫、AI Service批量调用、ChromaDB批量插入
- **逻辑**: 启动后台初始化任务，批量采集历史数据，分批次调用AI Service进行向量化，按类型和时间分集合存储，提供进度查询接口

### API4: 初始化进度查询
- **URL**: `GET /api/rag/bootstrap/{task_id}`
- **输入参数**: task_id (路径参数)
- **输出结果**: 详细进度信息
  ```python
  class BootstrapProgress(BaseModel):
      task_id: str
      status: str                          # running/completed/failed
      progress_percentage: float           # 完成百分比
      processed_documents: int             # 已处理文档数
      total_documents: int                 # 总文档数
      current_stage: str                   # 当前阶段
      stages_completed: List[str]          # 已完成阶段
      estimated_remaining_time: float      # 预估剩余时间
      error_count: int                     # 错误数量
      last_update_time: datetime          # 最后更新时间
  ```

### API5: 上下文增强 (为AI Service提供增强上下文)
- **URL**: `POST /api/rag/context`
- **输入参数**: AI上下文增强请求
  ```python
  class ContextEnhancementRequest(BaseModel):
      query: str                        # 用户问题
      stock_code: Optional[str] = None  # 当前关注股票
      context_type: str = "investment"  # 上下文类型
      max_context_length: int = 2000    # 最大上下文长度
  ```
- **输出结果**: 增强上下文响应
  ```python
  class RAGContextResponse(BaseModel):
      context: str                      # 组装的背景上下文
      sources: List[str]                # 来源文档ID列表
      relevance_score: float            # 相关性评分
      token_count: int                  # 上下文token数量
  ```
- **资源**: ChromaDB检索、文本组装算法
- **逻辑**: 基于用户问题和股票代码检索相关文档，智能筛选和组装成连贯的背景上下文，控制长度不超过限制，为AI模型提供准确的领域知识

### API4: 相似度计算
- **URL**: `POST /api/rag/similarity`
- **输入参数**: 文档相似度计算请求
  ```python
  class SimilarityRequest(BaseModel):
      document_pairs: List[Tuple[str, str]]  # 文档ID对列表
      similarity_method: str = "cosine"      # 相似度算法
  ```
- **输出结果**: 相似度计算结果
  ```python
  class SimilarityResponse(BaseModel):
      similarities: List[float]          # 相似度分数列表
      computation_time: float
  ```
- **资源**: 向量存储和计算引擎
- **逻辑**: 获取指定文档的向量表示，计算文档间的余弦相似度，用于重复文档检测和内容聚类分析

---

## 🗄️ 数据存储结构

### ChromaDB集合配置
```python
# 主要集合设计
FINANCIAL_COLLECTIONS = {
    'financial_documents': {
        'description': '金融文档向量集合',
        'embedding_function': 'bge-large-zh-v1.5',
        'metadata_schema': {
            'stock_code': str,      # 关联股票代码
            'doc_type': str,        # 文档类型: news/report/announcement
            'source': str,          # 来源: sina/eastmoney/official
            'publish_time': str,    # 发布时间 ISO格式
            'title': str,           # 文档标题
            'category': str,        # 分类: 业绩/重组/分红等
            'sentiment': str,       # 情感: positive/negative/neutral
            'importance': int       # 重要性评分 1-10
        }
    },
    'user_queries': {
        'description': '用户查询历史向量集合',
        'embedding_function': 'bge-large-zh-v1.5',
        'metadata_schema': {
            'user_id': str,
            'session_id': str,
            'timestamp': str,
            'stock_context': str
        }
    }
}
```

### 向量索引结构
```python
# 文档分片策略
class DocumentChunk:
    chunk_id: str           # 分片唯一ID
    parent_doc_id: str      # 父文档ID
    content: str            # 分片文本内容 (最大500字符)
    chunk_index: int        # 在父文档中的序号
    overlap_size: int = 50  # 与前后分片的重叠字符数

# 向量存储格式
class VectorDocument:
    id: str                 # 文档唯一标识
    embedding: List[float]  # 768维向量 (bge-large-zh-v1.5)
    metadata: Dict[str, Any] # 元数据信息
    timestamp: datetime     # 存储时间
```

---

## 🔧 核心服务实现

### 1. VectorService (向量检索服务)
- **文件**: `app/services/vector_service.py`
- **功能**: ChromaDB向量数据库操作封装
- **输入**: 查询向量和过滤条件
- **输出**: 相似文档列表
- **资源**: ChromaDB客户端连接
- **逻辑**: 连接ChromaDB数据库，执行向量相似度搜索，支持元数据过滤，返回按相似度排序的文档结果

### 2. EmbeddingService (文档嵌入服务)
- **文件**: `app/services/embedding_service.py`
- **功能**: 文本向量化和模型管理
- **输入**: 原始文本内容
- **输出**: 768维向量表示
- **资源**: bge-large-zh-v1.5模型文件
- **逻辑**: 加载预训练的bge中文向量模型，对输入文本进行tokenization和embedding，缓存模型以提高性能，支持批量处理

### 3. BootstrapManager (系统初始化管理器)
- **文件**: `app/services/bootstrap_manager.py`
- **功能**: RAG系统大量历史数据初始化
- **输入**: 初始化配置和数据源参数
- **输出**: 初始化任务进度和结果
- **逻辑**: 管理多阶段初始化流程，协调爬虫采集、数据预处理、批量向量化、分布式存储等任务，提供实时进度监控和错误恢复机制

### 4. DataBootstrapper (数据初始化器)
- **文件**: `app/services/data_bootstrapper.py`
- **功能**: 具体的数据源初始化实现
- **核心方法**:
  ```python
  class DataBootstrapper:
      async def bootstrap_announcements(self, time_range: Dict) -> AsyncIterator[Document]:
          """批量获取公司公告历史数据"""
          # 1. 调用上交所/深交所API获取公告列表
          # 2. 多线程下载公告PDF/HTML内容
          # 3. 解析文本内容并结构化
          # 4. 返回标准化文档对象

      async def bootstrap_financial_reports(self, time_range: Dict) -> AsyncIterator[Document]:
          """批量获取财报数据"""
          # 1. 调用AKShare获取所有股票财报列表
          # 2. 批量下载年报/季报原文
          # 3. 提取关键财务信息和管理层讨论
          # 4. 返回结构化财报文档

      async def bootstrap_research_reports(self, time_range: Dict) -> AsyncIterator[Document]:
          """批量获取券商研报"""
          # 1. 爬取主要券商研报网站
          # 2. 下载研报PDF并进行OCR识别
          # 3. 提取投资评级、目标价、核心观点
          # 4. 返回标准化研报文档

      async def bootstrap_policy_documents(self, time_range: Dict) -> AsyncIterator[Document]:
          """批量获取政策文件"""
          # 1. 爬取证监会、央行官网政策文件
          # 2. 解析HTML/PDF政策内容
          # 3. 提取政策要点和影响分析
          # 4. 返回结构化政策文档
  ```

### 5. RAGService (RAG核心服务)
- **文件**: `app/services/rag_service.py`
- **功能**: 检索增强生成核心逻辑
- **输入**: 用户查询和上下文参数
- **输出**: 增强的上下文信息
- **资源**: 向量服务和嵌入服务
- **逻辑**: 协调向量检索和上下文组装，实现混合搜索策略（语义+关键词），智能过滤和排序检索结果，组装符合长度限制的连贯上下文

### 4. ContextService (上下文增强服务)
- **文件**: `app/services/context_service.py`
- **功能**: 智能上下文组装和优化
- **输入**: 检索到的文档片段
- **输出**: 结构化的上下文文本
- **逻辑**: 分析文档片段的重要性和相关性，去除重复和冗余信息，按逻辑顺序组装上下文，确保文本连贯性和信息完整性

---

## 🌐 数据流设计

## 📊 **RAG数据生命周期管理**

### Phase 1: 系统初始化 (Bootstrap阶段)

#### 大量历史数据导入流程
```python
# 初始化数据源配置
BOOTSTRAP_DATA_SOURCES = {
    "historical_announcements": {
        "source": "上交所/深交所公告爬取",
        "time_range": "2022-01-01 to present",
        "estimated_documents": 50000,
        "data_types": ["公司公告", "交易所通知", "监管文件"]
    },
    "financial_reports": {
        "source": "AKShare财报接口 + 爬虫",
        "time_range": "最近8个季度",
        "estimated_documents": 15000,
        "data_types": ["年报", "季报", "业绩预告"]
    },
    "research_reports": {
        "source": "券商研报爬取",
        "time_range": "2023-01-01 to present",
        "estimated_documents": 30000,
        "data_types": ["行业研报", "公司深度报告", "策略报告"]
    },
    "policy_documents": {
        "source": "证监会/央行政策爬取",
        "time_range": "2022-01-01 to present",
        "estimated_documents": 2000,
        "data_types": ["政策解读", "法规文件", "监管指导"]
    },
    "historical_news": {
        "source": "AKShare新闻接口",
        "time_range": "2023-01-01 to present",
        "estimated_documents": 100000,
        "data_types": ["财经新闻", "公司新闻", "行业动态"]
    }
}
```

#### 初始化处理流程
1. **批量数据采集** → 多线程爬虫/API调用 → 获取大量历史文档
2. **数据预处理** → 格式统一化 → 质量过滤 → 重复检测
3. **分批向量化** → 调用AI Service批量embedding → 进度监控
4. **分片存储** → 按时间/类型分集合存储到ChromaDB → 建立索引

### Phase 2: 增量更新流程 (Incremental Updates)

#### 实时文档处理流程
1. **文档接收** → News Service推送新文档 → RAG Service接收
2. **文本预处理** → 清洗HTML标签 → 分片处理 → 去重检测
3. **向量生成** → 调用AI Service embedding → 向量标准化 → 质量检查
4. **存储更新** → ChromaDB插入 → 索引重建 → 元数据更新

### 检索增强流程
1. **查询处理** → 用户问题 → 查询向量化 → 过滤条件构建
2. **相似度检索** → ChromaDB搜索 → 相似度计算 → 结果排序
3. **上下文组装** → 文档片段提取 → 重复去除 → 逻辑排序 → 长度控制
4. **质量评估** → 相关性评分 → 完整性检查 → 最终输出

---

## ⚡ 性能优化策略

### 向量计算优化
- **模型缓存**: bge模型常驻内存，避免重复加载
- **批量处理**: 支持批量向量化，提高GPU利用率
- **量化加速**: 使用INT8量化减少内存占用
- **异步处理**: 文档嵌入采用异步队列处理

### 检索性能优化
- **索引优化**: ChromaDB使用HNSW索引加速检索
- **缓存策略**: 热门查询结果缓存30分钟
- **分层检索**: 先粗筛后精排，减少计算量
- **并行搜索**: 多集合并行检索后合并结果

---

## 🔒 环境配置

### 环境变量 (.env)
```bash
# ChromaDB配置
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_COLLECTION=financial_documents

# 向量模型配置
EMBEDDING_MODEL_PATH=./data/models/bge-large-zh-v1.5
MODEL_DEVICE=cuda  # cuda/cpu
MODEL_MAX_LENGTH=512

# 服务配置
RAG_SERVICE_PORT=8001
MAX_QUERY_LENGTH=1000
DEFAULT_SIMILARITY_THRESHOLD=0.7
CONTEXT_MAX_LENGTH=2000

# 缓存配置
REDIS_URL=redis://localhost:6379/2
CACHE_TTL=1800

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/rag-service.log
```

### 依赖配置 (requirements.txt)
```txt
fastapi==0.104.1
uvicorn==0.24.0
langchain==0.0.350
chromadb==0.4.18
sentence-transformers==2.2.2
torch==2.1.0
transformers==4.35.2
numpy==1.24.3
redis==5.0.1
pydantic==2.5.0
python-multipart==0.0.6
```

---

## 📊 监控和日志

### 性能指标监控
- **检索延迟**: 单次向量检索响应时间 < 100ms
- **吞吐量**: 并发处理能力 > 100 QPS
- **模型内存**: bge模型内存占用 < 2GB
- **缓存命中率**: 查询缓存命中率 > 60%

### 日志记录策略
```python
# 关键操作日志
LOG_EVENTS = {
    'document_embed': '文档向量化处理',
    'vector_search': '向量检索操作',
    'context_assembly': '上下文组装',
    'model_loading': '模型加载状态',
    'performance_metrics': '性能指标记录'
}
```

---

*文档更新时间: 2025-09-16*
*严格遵循外部设计规范，确保接口一致性*