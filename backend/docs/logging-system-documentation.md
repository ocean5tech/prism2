# Prism2 日志系统文档

## 概述

Prism2 后端日志系统是一个综合性的日志记录框架，用于监控和分析系统中的所有关键操作。该系统提供结构化日志记录，支持多种格式输出，并包含详细的性能指标和错误跟踪。

## 系统架构

### 核心组件

1. **PrismLogger 类** (`app/utils/logger.py`)
   - 主要日志记录引擎
   - 支持多种日志操作类型
   - 自动文件管理和时间戳命名
   - JSON 和文本格式双输出

2. **装饰器系统**
   - `@log_api_calls` - API 调用自动日志记录
   - `@log_akshare_calls` - AKShare 调用自动日志记录
   - 自动参数捕获和性能测量

3. **增强服务层**
   - Enhanced API endpoints
   - Enhanced AKShare service
   - Enhanced batch processors
   - Enhanced RAG processors

## 日志文件结构

### 文件命名规范

```
/home/wyatt/prism2/logs/
├── api_backend_YYYYMMDD_HHMMSS.log
├── api_backend_YYYYMMDD_HHMMSS.json
├── akshare_service_YYYYMMDD_HHMMSS.log
├── akshare_service_YYYYMMDD_HHMMSS.json
├── batch_processor_YYYYMMDD_HHMMSS.log
├── batch_processor_YYYYMMDD_HHMMSS.json
├── rag_service_YYYYMMDD_HHMMSS.log
└── rag_service_YYYYMMDD_HHMMSS.json
```

### 日志分类

- **api_backend**: Backend API 调用日志
- **akshare_service**: AKShare 数据源调用日志
- **batch_processor**: 批处理执行日志
- **rag_service**: RAG 操作日志

## 日志记录类型

### 1. API 调用日志 (API Backend Logs)

**记录内容:**
- 请求端点和 HTTP 方法
- 请求参数和响应数据
- HTTP 状态码
- 执行时间（毫秒）
- 客户端 IP 和用户 ID

**文本格式示例:**
```
2025-09-23 09:31:06,962 - prism2.api.backend - INFO - API Call: GET /stocks/search | Status: 200 | Time: 125.00ms | Params: 2 | Response: 53 chars
```

**JSON 格式示例:**
```json
{
  "timestamp": "2025-09-23T09:31:06.962341",
  "log_type": "api",
  "component": "backend",
  "category": "api_call",
  "endpoint": "/stocks/search",
  "method": "GET",
  "request_data": {"query": "平安银行", "limit": 10},
  "response_data": {"stocks": [...], "total": 1},
  "status_code": 200,
  "execution_time_ms": 125.0,
  "client_ip": "127.0.0.1",
  "user_id": null
}
```

### 2. AKShare 调用日志 (AKShare Service Logs)

**记录内容:**
- 调用的 AKShare 函数名
- 输入参数
- 输出数据的键名和数据量
- 返回状态码
- 执行时间
- 错误信息（如有）

**文本格式示例:**
```
2025-09-23 09:31:51,160 - prism2.akshare.service - INFO - AKShare Call: stock_zh_a_spot_em | Params: {} | Output: 5431 records | Keys: ['代码','名称','最新价'...] | Time: 2500.00ms
```

**JSON 格式示例:**
```json
{
  "timestamp": "2025-09-23T09:31:51.160124",
  "log_type": "akshare",
  "component": "service",
  "category": "akshare_call",
  "function_name": "stock_zh_a_spot_em",
  "input_params": {},
  "output_keys": ["代码", "名称", "最新价", "涨跌幅", "涨跌额"],
  "data_count": 5431,
  "status_code": 200,
  "execution_time_ms": 2500.0,
  "error": null
}
```

### 3. 批处理执行日志 (Batch Processor Logs)

**记录内容:**
- 批处理任务名称和数据源
- 输入数据量、输出数据量、RAG 存储量
- 执行时间和成功率
- 缓存命中/未命中统计
- 错误详情

**文本格式示例:**
```
2025-09-23 09:31:51,160 - prism2.batch.processor - INFO - Batch Process: test_batch_process | Source: test_stock_list | In: 100 -> Out: 95 -> RAG: 85 | Success: 95.0% | Time: 15500.00ms | Cache: 30H/70M
```

**JSON 格式示例:**
```json
{
  "timestamp": "2025-09-23T09:31:51.160641",
  "log_type": "batch",
  "component": "processor",
  "category": "batch_execution",
  "process_name": "test_batch_process",
  "data_source": "test_stock_list",
  "input_count": 100,
  "output_count": 95,
  "rag_stored_count": 85,
  "success_rate": 95.0,
  "execution_time_ms": 15500.0,
  "cache_stats": {
    "hits": 30,
    "misses": 70,
    "hit_ratio": 0.3
  },
  "status": "success",
  "error_details": null
}
```

### 4. RAG 操作日志 (RAG Service Logs)

**记录内容:**
- RAG 操作类型（vectorization, query, embedding）
- 股票代码和数据类型
- 输入块数和输出向量数
- 集合名称和版本 ID
- 嵌入模型信息
- 执行时间和状态

**文本格式示例:**
```
2025-09-23 09:31:51,161 - prism2.rag.service - INFO - RAG vectorization: 000001-financial | Chunks: 5 -> Vectors: 5 | Collection: prism2_000001_financial | Version: 123e4567... | Time: 2500.00ms
```

**JSON 格式示例:**
```json
{
  "timestamp": "2025-09-23T09:31:51.161641",
  "log_type": "rag",
  "component": "service",
  "category": "rag_operation",
  "operation": "vectorization",
  "stock_info": {
    "code": "000001",
    "data_type": "financial"
  },
  "processing": {
    "input_chunks": 5,
    "output_vectors": 5,
    "embedding_model": "bge-large-zh-v1.5",
    "collection": "prism2_000001_financial",
    "version_id": "123e4567-e89b-12d3-a456-426614174000"
  },
  "performance": {
    "execution_time_ms": 2500.0,
    "vectors_per_sec": 2.0
  },
  "status": "success",
  "error": null
}
```

## 使用方法

### 1. 基本日志记录

```python
from app.utils.logger import PrismLogger

# 创建日志实例
logger = PrismLogger()

# 记录 API 调用
logger.log_api_call(
    endpoint="/stocks/search",
    method="GET",
    request_data={"query": "平安银行"},
    response_data={"stocks": [...], "total": 1},
    status_code=200,
    execution_time=125.0,
    client_ip="127.0.0.1"
)

# 记录 AKShare 调用
logger.log_akshare_call(
    function_name="stock_zh_a_spot_em",
    input_params={},
    output_keys=["代码", "名称", "最新价"],
    data_count=5431,
    status_code=200,
    execution_time=2500.0
)
```

### 2. 装饰器使用

```python
from app.utils.logger import log_api_calls, log_akshare_calls, PrismLogger

# 创建日志实例
api_logger = PrismLogger()
akshare_logger = PrismLogger()

# API 装饰器
@log_api_calls(api_logger)
async def search_stocks(request: Request, query: str):
    # API 逻辑
    return results

# AKShare 装饰器
@log_akshare_calls(akshare_logger)
def get_stock_list(self):
    # AKShare 调用逻辑
    return data
```

### 3. 批处理和 RAG 日志

```python
# 批处理日志
logger.log_batch_execution(
    process_name="watchlist_processing",
    data_source="user_watchlists",
    input_count=100,
    output_count=95,
    rag_stored_count=85,
    execution_time=15500.0,
    success_rate=95.0,
    cache_hits=30,
    cache_misses=70
)

# RAG 操作日志
logger.log_rag_operation(
    operation_type="vectorization",
    stock_code="000001",
    data_type="financial",
    input_chunks=5,
    output_vectors=5,
    collection_name="prism2_000001_financial",
    version_id="123e4567-e89b-12d3-a456-426614174000",
    execution_time=2500.0
)
```

## 配置选项

### 日志级别配置

```python
# 在 logger.py 中配置
logging.basicConfig(
    level=logging.INFO,  # 可设置为 DEBUG, INFO, WARNING, ERROR
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 文件轮转配置

系统使用基于时间戳的文件命名，不需要额外配置文件轮转。每次应用启动时会创建新的日志文件。

## 性能指标

### 支持的性能指标

1. **执行时间** - 所有操作的毫秒级时间测量
2. **数据量统计** - 输入/输出数据的计数
3. **成功率** - 批处理操作的成功百分比
4. **缓存统计** - 缓存命中率和未命中数
5. **吞吐量** - 向量化操作的每秒处理量

### 并发性能

系统支持高并发日志记录：
- 测试显示支持 50 个并发请求
- 每个日志操作独立处理
- 文件锁定机制确保数据完整性

## 错误处理

### 错误分类

1. **系统错误** - 文件 I/O、网络连接等
2. **数据错误** - 数据格式、验证失败等
3. **外部服务错误** - AKShare API、数据库连接等

### 错误日志格式

```json
{
  "timestamp": "2025-09-23T09:31:51.161940",
  "log_type": "rag",
  "status": "failed",
  "error": "ChromaDB connection timeout",
  "error_details": {
    "error_type": "ConnectionError",
    "error_code": "TIMEOUT",
    "retry_count": 3
  }
}
```

## 监控和分析

### 日志分析建议

1. **性能监控** - 跟踪执行时间趋势
2. **错误率分析** - 监控失败率和错误模式
3. **使用统计** - 分析 API 调用频率和模式
4. **资源利用率** - 跟踪数据处理量和缓存效率

### 推荐工具

- **日志聚合**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **监控**: Grafana + Prometheus
- **分析**: Python pandas + jupyter notebook

## 故障排除

### 常见问题

1. **日志文件未创建**
   - 检查 `/home/wyatt/prism2/logs/` 目录权限
   - 确认日志目录存在

2. **JSON 格式错误**
   - 检查输入数据是否包含不可序列化对象
   - 验证字符编码（UTF-8）

3. **性能问题**
   - 考虑异步日志记录
   - 定期清理旧日志文件

### 调试模式

```python
# 启用调试日志
import logging
logging.getLogger('prism2').setLevel(logging.DEBUG)
```

## 扩展指南

### 添加新的日志类型

1. 在 `PrismLogger` 类中添加新方法
2. 定义相应的装饰器（如需要）
3. 更新文档和测试

### 自定义格式化器

```python
class CustomFormatter(logging.Formatter):
    def format(self, record):
        # 自定义格式化逻辑
        return super().format(record)
```

## 版本信息

- **当前版本**: 1.0.0
- **Python 版本**: 3.12+
- **依赖**: FastAPI, pandas, logging, json
- **创建日期**: 2025-09-23
- **最后更新**: 2025-09-23

## 联系信息

如有问题或建议，请联系开发团队或在项目仓库中提交 issue。