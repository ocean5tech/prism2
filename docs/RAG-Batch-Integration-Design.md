# RAG-批处理集成设计文档

## 📋 文档概览

**项目名称**: RAG与批处理系统集成
**设计版本**: v1.0
**创建时间**: 2025-09-19
**负责人**: Claude Code AI
**核心目标**: 实现批处理数据自动向量化和RAG集成，支持数据版本管理

## 🎯 核心需求分析

### 现状评估

#### ✅ 已完成功能
1. **批处理系统**: 完整的自选股批处理引擎，成功与ThreeTierDataService集成
2. **RAG基础设施**: ChromaDB、向量化服务、embedding服务完全就绪
3. **数据存储**: 结构化数据已存储到PostgreSQL和Redis
4. **测试验证**: 三股票(002384, 002617, 002371)真实数据测试100%成功

#### ❌ 缺失功能
1. **数据向量化**: 结构化数据尚未转换为向量
2. **版本管理**: 缺少"前一版本非活性，新版信息活性"功能
3. **自动同步**: 批处理获取数据后未自动同步到RAG
4. **数据更新流程**: 没有完整的更新和替换机制

### 用户核心要求

> "把这些信息更新到RAG中去，另外RAG库现在虽然有了，但是如果面对更新，需要有把前一版本非活性，新版信息活性的功能"

**关键需求**:
1. 批处理数据自动同步到RAG向量数据库
2. 数据版本管理和活性状态控制
3. 新数据版本自动激活，旧版本自动停用

## 🏗️ 系统架构设计

### 整体集成架构
```
┌─────────────────────────────────────────────────────────────────────┐
│                       RAG-Batch Integration System                 │
├─────────────────────────────────────────────────────────────────────┤
│  Batch Processing Layer                                             │
│  ├── WatchlistProcessor (已存在)                                    │
│  ├── ThreeTierDataService (已存在)                                 │
│  └── 📝 RAGSyncProcessor (新增)                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Data Transformation Layer                                          │
│  ├── 📝 DataVectorizer (新增)                                      │
│  ├── 📝 VersionManager (新增)                                      │
│  ├── 📝 TextChunker (新增)                                         │
│  └── 📝 MetadataEnricher (新增)                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Storage Layer                                                      │
│  ├── PostgreSQL (结构化数据 + 版本元数据)                           │
│  ├── Redis (缓存层)                                               │
│  ├── ChromaDB (向量存储)                                           │
│  └── 📝 rag_data_versions (版本管理表，已存在)                     │
├─────────────────────────────────────────────────────────────────────┤
│  RAG Services Layer                                                │
│  ├── RAGService (已存在)                                           │
│  ├── EmbeddingService (已存在)                                     │
│  ├── VectorService (已存在)                                        │
│  └── 📝 VersionControlService (新增)                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 数据流程设计
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 批处理获取   │    │ 数据向量化   │    │ 版本管理    │    │ RAG同步     │
│ 结构化数据   │───▶│ 文本分块    │───▶│ 活性控制    │───▶│ 向量存储    │
│ (PostgreSQL)│    │ 向量计算    │    │ 旧版停用    │    │ (ChromaDB)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
  【财务数据】         【文本分块】         【版本v2.0】        【向量检索】
  【公告数据】         【向量计算】         【旧版停用】        【语义搜索】
  【股东数据】         【元数据】           【新版激活】        【上下文增强】
  【龙虎榜】
```

## 📊 数据库设计

### 版本管理表扩展 (基于现有rag_data_versions)

```sql
-- 现有表结构
CREATE TABLE rag_data_versions (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    version_id UUID NOT NULL UNIQUE,
    data_hash VARCHAR(64) NOT NULL,
    vector_status VARCHAR(20) DEFAULT 'pending',
    source_data JSONB NOT NULL,
    vector_metadata JSONB,
    embedding_model VARCHAR(100),
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activated_at TIMESTAMP,
    deprecated_at TIMESTAMP
);

-- 新增索引和约束
CREATE INDEX idx_rag_data_active ON rag_data_versions(stock_code, data_type, activated_at)
WHERE deprecated_at IS NULL;

CREATE INDEX idx_rag_data_status ON rag_data_versions(vector_status);
```

### 向量映射表 (现有rag_vector_mappings)
```sql
-- 现有表结构保持不变
CREATE TABLE rag_vector_mappings (
    id SERIAL PRIMARY KEY,
    version_id UUID REFERENCES rag_data_versions(version_id),
    vector_id VARCHAR(255) NOT NULL,
    collection_name VARCHAR(100) NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 核心服务设计

### 1. RAGSyncProcessor - RAG同步处理器

**职责**: 将批处理获取的数据自动同步到RAG系统
**位置**: `batch_processor/processors/rag_sync_processor.py`

```python
class RAGSyncProcessor:
    """批处理数据RAG同步处理器"""

    async def sync_batch_data_to_rag(self, stock_codes: List[str], data_types: List[str]) -> Dict:
        """批量同步数据到RAG"""

    async def sync_single_stock_data(self, stock_code: str, data_type: str, force_refresh: bool = False) -> Dict:
        """同步单个股票数据到RAG"""

    async def get_latest_structured_data(self, stock_code: str, data_type: str) -> Optional[Dict]:
        """从PostgreSQL获取最新结构化数据"""

    def calculate_data_hash(self, data: Dict) -> str:
        """计算数据哈希值用于版本控制"""
```

### 2. DataVectorizer - 数据向量化器

**职责**: 将结构化数据转换为适合RAG的文本格式并向量化
**位置**: `batch_processor/services/data_vectorizer.py`

```python
class DataVectorizer:
    """数据向量化服务"""

    def transform_financial_data(self, financial_data: Dict) -> List[str]:
        """财务数据转换为文本段落"""

    def transform_announcement_data(self, announcement_data: Dict) -> List[str]:
        """公告数据转换为文本段落"""

    def transform_shareholder_data(self, shareholder_data: Dict) -> List[str]:
        """股东数据转换为文本段落"""

    def transform_longhubang_data(self, longhubang_data: Dict) -> List[str]:
        """龙虎榜数据转换为文本段落"""

    async def chunk_and_vectorize(self, text_chunks: List[str], metadata: Dict) -> List[Dict]:
        """文本分块并向量化"""
```

### 3. VersionManager - 版本管理器

**职责**: 实现"前一版本非活性，新版信息活性"的核心功能
**位置**: `batch_processor/services/version_manager.py`

```python
class VersionManager:
    """数据版本管理服务"""

    async def create_new_version(self, stock_code: str, data_type: str, source_data: Dict) -> str:
        """创建新数据版本"""

    async def activate_version(self, version_id: str) -> bool:
        """激活指定版本"""

    async def deprecate_old_versions(self, stock_code: str, data_type: str, exclude_version: str) -> int:
        """停用旧版本"""

    async def get_active_version(self, stock_code: str, data_type: str) -> Optional[Dict]:
        """获取当前活跃版本"""

    async def cleanup_deprecated_vectors(self, version_id: str) -> bool:
        """清理已停用版本的向量数据"""
```

### 4. VectorSyncService - 向量同步服务

**职责**: 与ChromaDB进行向量数据同步
**位置**: `batch_processor/services/vector_sync_service.py`

```python
class VectorSyncService:
    """向量同步服务"""

    async def sync_vectors_to_chromadb(self, version_id: str, vectors_data: List[Dict]) -> bool:
        """同步向量到ChromaDB"""

    async def remove_vectors_from_chromadb(self, version_id: str) -> bool:
        """从ChromaDB删除指定版本向量"""

    async def update_collection_metadata(self, collection_name: str, metadata: Dict) -> bool:
        """更新集合元数据"""

    def get_collection_name(self, stock_code: str, data_type: str) -> str:
        """生成集合名称"""
```

## 🔄 业务流程设计

### 1. 批处理数据更新流程

```
┌─────────────────┐
│ 批处理获取数据   │ (现有流程)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 检查数据变化    │ (计算hash，对比旧版本)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 创建新版本      │ (rag_data_versions表)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 数据向量化      │ (文本转换+向量计算)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 同步到ChromaDB  │ (向量存储)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 激活新版本      │ (activate_at时间戳)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 停用旧版本      │ (deprecated_at时间戳)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 清理旧向量      │ (从ChromaDB删除)
└─────────────────┘
```

### 2. 版本控制状态机

```
┌─────────────┐    create_version    ┌─────────────┐    vectorize    ┌─────────────┐
│   NONEXIST  │────────────────────▶ │   PENDING   │───────────────▶ │ VECTORIZED  │
└─────────────┘                     └─────────────┘                 └─────────────┘
                                            │                               │
                                            │ fail                          │ activate
                                            ▼                               ▼
                                    ┌─────────────┐                 ┌─────────────┐
                                    │   FAILED    │                 │   ACTIVE    │
                                    └─────────────┘                 └─────────────┘
                                                                            │
                                                                            │ deprecate
                                                                            ▼
                                                                    ┌─────────────┐
                                                                    │ DEPRECATED  │
                                                                    └─────────────┘
```

### 3. 数据类型处理策略

#### 财务数据 (financial)
```python
def transform_financial_data(self, data: Dict) -> List[str]:
    """
    输入: {"revenue": 1000000, "profit": 200000, "pe_ratio": 15.5, ...}
    输出: [
        "公司年度营收为100万元，净利润20万元，盈利能力良好",
        "市盈率15.5倍，处于合理估值区间",
        "资产负债率45%，财务结构稳健"
    ]
    """
```

#### 公告数据 (announcements)
```python
def transform_announcement_data(self, data: Dict) -> List[str]:
    """
    输入: [{"title": "业绩预告", "content": "预计净利润增长20%", "date": "2025-09-19"}]
    输出: [
        "2025年9月19日公司发布业绩预告，预计净利润增长20%",
        "公告显示公司经营状况良好，业绩稳步增长"
    ]
    """
```

#### 股东数据 (shareholders)
```python
def transform_shareholder_data(self, data: Dict) -> List[str]:
    """
    输入: [{"name": "张三", "shares": 1000000, "ratio": 0.05}]
    输出: [
        "股东张三持股100万股，持股比例5%",
        "前十大股东结构稳定，控制权集中度适中"
    ]
    """
```

#### 龙虎榜数据 (longhubang)
```python
def transform_longhubang_data(self, data: Dict) -> List[str]:
    """
    输入: [{"date": "2025-09-19", "buy_amount": 5000000, "sell_amount": 3000000}]
    输出: [
        "2025年9月19日登上龙虎榜，买入金额500万元，卖出300万元",
        "资金净流入200万元，市场关注度较高"
    ]
    """
```

## 📈 性能优化策略

### 1. 批量处理优化
- **批量向量化**: 一次处理多个股票的同类型数据
- **并行处理**: 不同数据类型并行向量化
- **分块策略**: 大文本智能分块，控制向量维度

### 2. 缓存策略
- **向量缓存**: 已计算向量缓存到Redis
- **版本缓存**: 活跃版本元数据缓存
- **增量更新**: 仅处理变化的数据

### 3. 资源控制
- **内存管理**: 流式处理大数据集
- **并发限制**: 控制ChromaDB连接数
- **错误重试**: 网络错误自动重试机制

## 🔍 监控和错误处理

### 1. 监控指标
```python
@dataclass
class RAGSyncMetrics:
    total_stocks_processed: int
    successful_vectorizations: int
    failed_vectorizations: int
    vector_count: int
    processing_time: float
    cache_hit_rate: float
    chromadb_sync_time: float
    version_operations: int
```

### 2. 错误处理策略
- **向量化失败**: 标记version_status为'failed'，记录错误信息
- **ChromaDB连接失败**: 重试3次，失败后保持数据在PostgreSQL
- **版本冲突**: 检测并解决版本冲突，确保数据一致性
- **内存不足**: 自动降级为小批量处理

### 3. 故障恢复
- **断点续传**: 记录处理进度，支持中断后恢复
- **数据完整性检查**: 定期验证向量数据与源数据一致性
- **自动修复**: 检测到数据不一致时自动重新向量化

## 🚀 实施计划

### Phase 1: 核心服务实现 (1-2天)
1. **RAGSyncProcessor**: 实现批处理数据RAG同步
2. **VersionManager**: 实现版本管理核心功能
3. **DataVectorizer**: 实现数据转换和向量化

### Phase 2: 集成测试 (0.5天)
1. **单元测试**: 各服务独立功能测试
2. **集成测试**: 端到端流程测试
3. **性能测试**: 批量数据处理性能验证

### Phase 3: 生产部署 (0.5天)
1. **配置优化**: 生产环境参数调优
2. **监控部署**: 指标收集和告警配置
3. **文档完善**: 使用手册和运维文档

## 📋 验收标准

### 功能验收
1. ✅ 批处理数据自动同步到RAG向量数据库
2. ✅ 新版本数据自动激活，旧版本自动停用
3. ✅ 支持四种数据类型的向量化转换
4. ✅ 版本管理完整可追溯

### 性能验收
1. ✅ 单股票四种数据类型向量化时间 < 30秒
2. ✅ 批量处理10只股票时间 < 5分钟
3. ✅ 向量数据库同步成功率 > 99%
4. ✅ 版本切换操作原子性保证

### 质量验收
1. ✅ 向量数据与源数据一致性 100%
2. ✅ 旧版本数据完全清理
3. ✅ 错误处理覆盖所有异常场景
4. ✅ 支持中断恢复和故障转移

## 💡 技术亮点

1. **无缝集成**: 与现有批处理系统完美集成，零侵入
2. **版本控制**: 企业级数据版本管理，支持回滚和追溯
3. **智能转换**: 结构化数据智能转换为语义丰富的文本
4. **高性能**: 批量并行处理，缓存优化，性能领先
5. **可靠性**: 完善的错误处理和恢复机制，生产级稳定性

---

**设计完成时间**: 2025-09-19 23:15
**下一步**: 等待用户审批后开始实施开发
**预计开发周期**: 2-3天完成核心功能
**投产就绪**: 开发完成即可投入生产使用