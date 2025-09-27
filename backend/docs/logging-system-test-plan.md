# Prism2 日志系统综合测试计划书

## 📋 测试概述

### 测试目标
验证 Prism2 日志系统在各种业务场景下的完整性、准确性和性能表现，确保所有关键操作都能被正确记录和追踪。

### 测试范围
- **API 调用日志** - Backend API 端点的请求/响应记录
- **AKShare 服务日志** - 数据源调用和结果记录
- **批处理系统日志** - 自动化任务执行记录
- **RAG 操作日志** - 向量化和语义搜索记录
- **自动化批处理验证** - RSS 监控和自选股批处理状态检查

### 测试环境
- **测试目录**: `/home/wyatt/prism2/logs/`
- **日志格式**: `.log` (文本) + `.json` (结构化)
- **时间戳格式**: `YYYYMMDD_HHMMSS`

---

## 🧪 测试用例设计

### 1. API 调用日志测试 (Test Suite A)

#### A1: 股票搜索API测试
**测试目标**: 验证股票搜索API调用的完整日志记录
**预期结果**:
- 生成 `api_backend_YYYYMMDD_HHMMSS.log` 和 `.json` 文件
- 记录包含 endpoint、method、request_data、response_data、status_code、execution_time

**测试步骤**:
```python
# GET /api/v1/stocks/search?query=平安银行&limit=10
# Expected Log Entry:
{
  "log_type": "api",
  "endpoint": "/api/v1/stocks/search",
  "method": "GET",
  "request_data": {"query": "平安银行", "limit": 10},
  "status_code": 200,
  "execution_time_ms": "<measured_time>"
}
```

#### A2: 股票详情API测试
**测试目标**: 验证单只股票详情查询的日志记录
**预期结果**: 记录详细的股票数据响应和性能指标

#### A3: 批量股票数据API测试
**测试目标**: 验证批量股票数据请求的日志记录
**预期结果**: 记录大量数据传输的性能指标和数据量统计

#### A4: 错误处理API测试
**测试目标**: 验证无效请求的错误日志记录
**预期结果**:
- 记录 4xx/5xx 状态码
- 包含错误信息和调试详情

#### A5: 高并发API测试
**测试目标**: 验证并发请求下的日志完整性
**预期结果**:
- 50个并发请求全部记录
- 无日志丢失或重复
- 性能指标准确

---

### 2. AKShare 服务日志测试 (Test Suite B)

#### B1: 股票列表获取测试
**测试目标**: 验证 `stock_zh_a_spot_em()` 调用日志
**预期结果**:
```json
{
  "log_type": "akshare",
  "function_name": "stock_zh_a_spot_em",
  "input_params": {},
  "output_keys": ["代码", "名称", "最新价", "涨跌幅", "涨跌额"],
  "data_count": ">5000",
  "status_code": 200,
  "execution_time_ms": "<measured_time>"
}
```

#### B2: 个股历史数据测试
**测试目标**: 验证 `stock_zh_a_hist()` 调用日志
**预期结果**: 记录股票代码、日期范围、数据量等参数

#### B3: 财务数据获取测试
**测试目标**: 验证财务报表数据获取的日志记录
**预期结果**: 记录财务数据类型和数据结构信息

#### B4: 实时行情数据测试
**测试目标**: 验证实时行情数据获取的性能和日志
**预期结果**: 记录实时数据的延迟和刷新频率

#### B5: AKShare 错误处理测试
**测试目标**: 验证 AKShare API 限流或错误时的日志记录
**预期结果**:
- 记录错误类型和错误码
- 包含重试机制的执行记录

---

### 3. 批处理系统日志测试 (Test Suite C)

#### C1: RSS 新闻源监控批处理测试
**测试目标**: 验证 RSS 监控批处理的自动执行和日志记录
**预期结果**:
```json
{
  "log_type": "batch",
  "category": "batch_execution",
  "process_name": "rss_news_monitor",
  "data_source": "financial_rss_feeds",
  "input_count": "<news_articles>",
  "output_count": "<processed_articles>",
  "rag_stored_count": "<vectorized_articles>",
  "execution_time_ms": "<measured_time>",
  "success_rate": ">90%"
}
```

**验证点**:
- 定期执行频率 (每小时/每日)
- 新闻源URL列表处理
- 文章去重和过滤逻辑
- RAG向量化存储统计

#### C2: 自选股优先批处理测试
**测试目标**: 验证基于用户自选股的优先数据处理
**预期结果**:
```json
{
  "log_type": "batch",
  "process_name": "watchlist_priority_processing",
  "data_source": "user_watchlists",
  "input_count": "<watchlist_stocks>",
  "output_count": "<processed_stocks>",
  "rag_stored_count": "<vectorized_data>",
  "cache_stats": {
    "hits": "<cache_hits>",
    "misses": "<cache_misses>",
    "hit_ratio": "<percentage>"
  }
}
```

**验证点**:
- 用户自选股列表获取
- 优先级排序逻辑
- AKShare 数据获取
- RAG向量化处理
- 缓存机制效果

#### C3: 定时AKShare数据同步测试
**测试目标**: 验证定时同步所有股票基础数据的批处理
**预期结果**: 记录大规模数据同步的性能指标和完成状态

#### C4: 批处理错误恢复测试
**测试目标**: 验证批处理任务中断后的恢复和重试机制
**预期结果**: 记录错误类型、重试次数、恢复状态

#### C5: 批处理性能优化测试
**测试目标**: 验证并发批处理的性能和资源使用
**预期结果**: 记录CPU、内存使用率和处理吞吐量

---

### 4. RAG 操作日志测试 (Test Suite D)

#### D1: 文档向量化测试
**测试目标**: 验证文档向量化操作的详细日志
**预期结果**:
```json
{
  "log_type": "rag",
  "operation": "vectorization",
  "stock_info": {"code": "000001", "data_type": "financial_report"},
  "processing": {
    "input_chunks": "<chunk_count>",
    "output_vectors": "<vector_count>",
    "embedding_model": "bge-large-zh-v1.5",
    "collection": "prism2_000001_financial",
    "version_id": "<uuid>"
  },
  "performance": {
    "execution_time_ms": "<measured_time>",
    "vectors_per_sec": "<throughput>"
  }
}
```

#### D2: 语义搜索查询测试
**测试目标**: 验证RAG查询操作的性能和结果记录
**预期结果**: 记录查询词、匹配结果、相似度分数

#### D3: 向量数据库操作测试
**测试目标**: 验证ChromaDB的增删改查操作日志
**预期结果**: 记录数据库操作类型、affected_rows、执行时间

#### D4: 嵌入模型性能测试
**测试目标**: 验证不同文档类型的嵌入处理性能
**预期结果**: 记录不同数据类型的处理速度差异

#### D5: RAG错误处理测试
**测试目标**: 验证向量数据库连接异常等错误的处理
**预期结果**: 记录错误类型、恢复策略、数据完整性检查

---

## 🔄 自动化批处理验证

### 自动化任务检查清单

#### 1. RSS 新闻源监控系统
**检查项目**:
- [ ] RSS监控服务是否在运行
- [ ] 新闻源配置文件是否存在
- [ ] 定时任务调度器状态
- [ ] 最近执行记录和日志
- [ ] 新闻数据入库统计

**验证命令**:
```bash
# 检查RSS监控进程
ps aux | grep rss_monitor
# 检查定时任务
crontab -l | grep rss
# 查看最新RSS日志
ls -la /home/wyatt/prism2/logs/ | grep batch | head -5
```

#### 2. AKShare 自选股批处理系统
**检查项目**:
- [ ] 自选股批处理调度器状态
- [ ] 用户自选股数据源连接
- [ ] AKShare API调用频率限制
- [ ] RAG向量化处理队列
- [ ] 缓存系统工作状态

**验证命令**:
```bash
# 检查批处理进程
ps aux | grep batch_processor
# 检查最新自选股处理日志
grep "watchlist" /home/wyatt/prism2/logs/batch_processor_*.log | tail -10
```

#### 3. 定时任务配置验证
**检查内容**:
- APScheduler 任务列表
- Cron job 配置
- 任务执行历史
- 失败重试机制
- 资源使用监控

---

## 📊 预期日志格式验证标准

### 1. 日志文件命名规范验证
```
✅ api_backend_20250923_143005.log
✅ api_backend_20250923_143005.json
✅ akshare_service_20250923_143005.log
✅ akshare_service_20250923_143005.json
✅ batch_processor_20250923_143005.log
✅ batch_processor_20250923_143005.json
✅ rag_service_20250923_143005.log
✅ rag_service_20250923_143005.json
```

### 2. 必要字段验证清单

#### API 日志必要字段:
- [ ] timestamp
- [ ] log_type: "api"
- [ ] endpoint
- [ ] method
- [ ] status_code
- [ ] execution_time_ms
- [ ] request_data
- [ ] response_data

#### AKShare 日志必要字段:
- [ ] timestamp
- [ ] log_type: "akshare"
- [ ] function_name
- [ ] input_params
- [ ] output_keys
- [ ] data_count
- [ ] execution_time_ms

#### 批处理日志必要字段:
- [ ] timestamp
- [ ] log_type: "batch"
- [ ] process_name
- [ ] data_source
- [ ] input_count
- [ ] output_count
- [ ] rag_stored_count
- [ ] success_rate
- [ ] execution_time_ms

#### RAG 日志必要字段:
- [ ] timestamp
- [ ] log_type: "rag"
- [ ] operation
- [ ] stock_info
- [ ] processing
- [ ] performance
- [ ] status

---

## 🚀 测试执行计划

### Phase 1: 环境准备 (预计30分钟)
1. **清理旧日志文件** - 确保测试环境干净
2. **检查服务状态** - 验证所有相关服务运行正常
3. **准备测试数据** - 设置测试用的股票代码和参数

### Phase 2: 单元测试执行 (预计60分钟)
1. **API测试执行** - 按照 Test Suite A 逐项测试
2. **AKShare测试执行** - 按照 Test Suite B 逐项测试
3. **批处理测试执行** - 按照 Test Suite C 逐项测试
4. **RAG测试执行** - 按照 Test Suite D 逐项测试

### Phase 3: 集成测试执行 (预计45分钟)
1. **端到端流程测试** - 从API调用到RAG存储的完整流程
2. **并发压力测试** - 模拟高负载情况
3. **自动化批处理验证** - 检查定时任务和RSS监控

### Phase 4: 结果验证 (预计30分钟)
1. **日志文件完整性检查** - 验证所有预期日志文件生成
2. **日志内容准确性验证** - 对比实际日志与预期格式
3. **性能指标分析** - 评估系统性能表现
4. **错误处理验证** - 确认异常情况的正确记录

### Phase 5: 报告生成 (预计15分钟)
1. **测试结果汇总** - 统计通过/失败用例
2. **问题总结和建议** - 记录发现的问题和改进建议
3. **性能基准建立** - 为未来监控建立性能基准

---

## 📈 成功标准定义

### 功能完整性标准
- [ ] 100% 测试用例执行完成
- [ ] 95% 以上测试用例通过
- [ ] 所有日志文件格式符合规范
- [ ] 关键性能指标在可接受范围内

### 性能标准
- [ ] API响应时间 < 500ms (95th percentile)
- [ ] AKShare调用成功率 > 95%
- [ ] 批处理任务完成率 > 90%
- [ ] RAG向量化处理速度 > 10 docs/sec

### 可靠性标准
- [ ] 并发测试无日志丢失
- [ ] 错误情况正确记录和处理
- [ ] 自动化任务按预期执行
- [ ] 系统资源使用合理

---

## 🔧 故障排除预案

### 常见问题预防
1. **日志文件权限问题** - 预先检查目录权限
2. **AKShare API限流** - 设置合理的请求间隔
3. **数据库连接异常** - 准备连接恢复机制
4. **磁盘空间不足** - 监控日志目录空间使用

### 测试中断恢复
1. **保存中间状态** - 记录已完成的测试项目
2. **错误诊断** - 快速定位问题原因
3. **部分重试** - 支持从中断点继续测试

---

**测试计划创建时间**: 2025-09-23
**预计总执行时间**: 3小时
**负责人**: 系统测试团队
**审核状态**: 待审核