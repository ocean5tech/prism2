# Prism2 全面系统测试计划

## 🔧 已验证的正确启动方式 (2025-09-24测试验证)

### Phase 1: 基础设施服务启动 (容器化服务)

#### PostgreSQL + TimescaleDB
```bash
podman run -d --name prism2-postgres \
  -p 5432:5432 \
  -v /home/wyatt/prism2/data/postgres:/var/lib/postgresql/data \
  -e POSTGRES_DB=prism2 \
  -e POSTGRES_USER=prism2 \
  -e POSTGRES_PASSWORD=prism2_secure_password \
  docker.io/timescale/timescaledb:latest-pg15
```
**镜像**: docker.io/timescale/timescaledb:latest-pg15
**容器名**: prism2-postgres
**端口映射**: 5432:5432
**数据库**: prism2
**用户名**: prism2
**密码**: prism2_secure_password
**数据卷**: /home/wyatt/prism2/data/postgres:/var/lib/postgresql/data
**验证状态**: ✅ 运行正常，端口5432

#### Redis
```bash
podman run -d --name prism2-redis \
  -p 6379:6379 \
  -v /home/wyatt/prism2/data/redis:/data \
  docker.io/library/redis:7-alpine \
  redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
```
**镜像**: docker.io/library/redis:7-alpine
**容器名**: prism2-redis
**端口映射**: 6379:6379
**数据卷**: /home/wyatt/prism2/data/redis:/data
**配置**: appendonly yes, maxmemory 512mb, maxmemory-policy allkeys-lru
**验证状态**: ✅ 运行正常，端口6379

#### ChromaDB
```bash
podman run -d --name prism2-chromadb \
  -p 8003:8000 \
  -v chromadb_data:/chroma/chroma \
  docker.io/chromadb/chroma:latest \
  run /config.yaml
```
**镜像**: docker.io/chromadb/chroma:latest
**容器名**: prism2-chromadb
**端口映射**: 8003:8000 (外部8003映射到容器内8000)
**数据卷**: chromadb_data:/chroma/chroma
**启动参数**: run /config.yaml
**API地址**: http://localhost:8003/api/v2/
**验证状态**: ✅ 运行正常，端口8003，API v2正常

#### Nginx (暂时未使用)
```bash
podman run -d --name prism2-nginx \
  -p 9080:80 \
  -v /home/wyatt/prism2/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  docker.io/library/nginx:alpine
```
**镜像**: docker.io/library/nginx:alpine
**容器名**: prism2-nginx
**端口映射**: 9080:80
**配置文件**: /home/wyatt/prism2/nginx/nginx.conf:ro (只读)

### Phase 2: 应用服务启动方式

#### Enhanced Dashboard API系统
```bash
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
python enhanced_dashboard_api.py
```
**工作目录**: /home/wyatt/prism2/backend
**虚拟环境**: test_venv
**启动文件**: enhanced_dashboard_api.py
**端口**: 8081
**架构**: 三层架构 (Redis → PostgreSQL → AKShare)
**验证状态**: ✅ 三层架构正常运行

#### RAG批处理集成系统
```bash
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
python test_rag_batch_integration.py
```
**工作目录**: /home/wyatt/prism2/backend
**虚拟环境**: test_venv
**启动文件**: test_rag_batch_integration.py
**功能**: RAG系统集成测试和批处理系统验证
**验证状态**: ✅ 80%成功率 (4/5项测试通过)

### 服务连接信息汇总

| 服务 | 端口 | 连接地址 | 认证信息 |
|------|------|---------|----------|
| PostgreSQL | 5432 | localhost:5432 | prism2/prism2_secure_password |
| Redis | 6379 | localhost:6379 | 无密码 |
| ChromaDB | 8003 | http://localhost:8003 | 无认证 |
| Dashboard API | 8081 | http://localhost:8081 | 无认证 |
| Nginx | 9080 | http://localhost:9080 | 无认证 |

### 连接字符串示例

#### PostgreSQL连接
```
Database URL: postgresql://prism2:prism2_secure_password@localhost:5432/prism2
```

#### Redis连接
```
Redis URL: redis://localhost:6379/0
```

#### ChromaDB连接
```
ChromaDB API: http://localhost:8003/api/v2/
```

---

## 📋 测试总体定义

### 🎯 **全面测试定义**
- **数据要求**: 100% 真实数据源，严禁任何模拟数据
- **功能覆盖**: 全部系统功能必须启动并测试，包括batch自动化功能
- **端到端验证**: 从API调用到数据库存储到RAG检索的完整数据流
- **对比验证**: 记录测试前后所有存储系统的数据变化
- **只测试不修复**: 测试过程中只记录问题，不进行代码修正

### 📊 **测试范围矩阵**

| 测试类别 | 测试组件 | 验证内容 | 成功标准 |
|---------|---------|---------|---------|
| **API验证** | 全部Backend API | 所有端点响应、数据完整性 | 100% API正常响应 |
| **数据存储** | PostgreSQL + Redis | 数据写入、读取、一致性 | 数据完整存储并可检索 |
| **三层架构** | Redis→PostgreSQL→AKShare | 缓存机制、降级机制 | 三层数据流正常工作 |
| **RAG系统** | 切片→嵌入→查询 | 向量化、存储、检索 | RAG全流程可工作 |
| **批处理** | 自动化任务 | RSS监控、定时任务 | 批处理自动执行 |
| **日志系统** | 全组件日志 | 日志记录、格式、完整性 | 所有操作被正确记录 |

---

## 🔍 Phase 1: 测试前环境基线记录

### 1.1 数据库状态基线
**目标**: 记录所有数据存储的初始状态，作为测试后对比基准

#### PostgreSQL 表数据统计
```sql
-- 需要记录的表和初始数量
SELECT 'stock_basic_info' as table_name, COUNT(*) as count FROM stock_basic_info
UNION ALL
SELECT 'stock_kline_daily', COUNT(*) FROM stock_kline_daily
UNION ALL
SELECT 'stock_financial', COUNT(*) FROM stock_financial
UNION ALL
SELECT 'stock_announcements', COUNT(*) FROM stock_announcements
UNION ALL
SELECT 'stock_shareholders', COUNT(*) FROM stock_shareholders
UNION ALL
SELECT 'stock_longhubang', COUNT(*) FROM stock_longhubang
UNION ALL
SELECT 'stock_news', COUNT(*) FROM stock_news
UNION ALL
SELECT 'stock_realtime', COUNT(*) FROM stock_realtime
UNION ALL
SELECT 'stock_ai_analysis', COUNT(*) FROM stock_ai_analysis;
```

#### Redis 缓存状态基线
```bash
# Redis键数量和类型统计
redis-cli DBSIZE
redis-cli KEYS "basic_info:*" | wc -l
redis-cli KEYS "kline:*" | wc -l
redis-cli KEYS "financial:*" | wc -l
redis-cli KEYS "announcements:*" | wc -l
redis-cli KEYS "shareholders:*" | wc -l
redis-cli KEYS "news:*" | wc -l
```

#### ChromaDB RAG状态基线
```python
# RAG向量数据库统计
collections = rag_client.list_collections()
for collection in collections:
    collection_info = rag_client.get_collection(collection.name)
    count = collection_info.count()
```

### 1.2 服务运行状态检查
- [ ] PostgreSQL + TimescaleDB 服务状态
- [ ] Redis 服务状态
- [ ] ChromaDB 服务状态
- [ ] Nginx 代理状态
- [ ] 批处理调度器状态
- [ ] RSS监控服务状态

---

## 🧪 Phase 2: 全面功能测试执行

### 2.1 API端点全面验证测试

#### Test Suite A: 股票基础API测试
**测试目标**: 验证所有股票相关API端点的完整功能

**测试用例**:
```
A1: GET /api/v1/stocks/search?query=平安银行&limit=10
   - 验证: 返回真实搜索结果，包含股票代码、名称、市场信息
   - 验证: 数据写入Redis缓存
   - 验证: 响应时间 < 500ms

A2: GET /api/v1/stocks/{stock_code}/basic
   - 测试股票: 000001, 600519, 000002, 688001
   - 验证: 返回完整基础信息
   - 验证: 数据写入PostgreSQL stock_basic_info表
   - 验证: 数据缓存到Redis

A3: GET /api/v1/stocks/{stock_code}/kline?period=daily&limit=30
   - 测试股票: 000001, 600519, 000002
   - 验证: 返回真实K线数据
   - 验证: 数据写入PostgreSQL stock_kline_daily表
   - 验证: 数据量 >= 30条记录

A4: GET /api/v1/stocks/{stock_code}/financial
   - 测试股票: 000001, 600519, 000002
   - 验证: 返回真实财务数据
   - 验证: 数据写入PostgreSQL stock_financial表

A5: GET /api/v1/stocks/{stock_code}/announcements
   - 测试股票: 000001, 600519, 000002
   - 验证: 返回真实公告数据
   - 验证: 数据写入PostgreSQL stock_announcements表

A6: GET /api/v1/stocks/{stock_code}/shareholders
   - 测试股票: 000001, 600519, 000002
   - 验证: 返回真实股东数据
   - 验证: 数据写入PostgreSQL stock_shareholders表

A7: GET /api/v1/stocks/{stock_code}/news
   - 测试股票: 000001, 600519, 000002
   - 验证: 返回真实新闻数据
   - 验证: 数据写入PostgreSQL stock_news表

A8: POST /api/v1/stocks/batch
   - 请求体: {"codes": ["000001", "600519", "000002"], "data_types": ["basic", "kline"]}
   - 验证: 批量处理所有股票
   - 验证: 所有数据正确存储
```

#### Test Suite B: RAG系统API测试
**测试目标**: 验证RAG系统的完整API功能

**测试用例**:
```
B1: POST /api/v1/rag/vectorize
   - 请求体: {"stock_code": "000001", "data_type": "financial", "content": "真实财务报告内容"}
   - 验证: 文档成功切片
   - 验证: 向量成功生成并存储到ChromaDB
   - 验证: 返回向量数量和集合信息

B2: POST /api/v1/rag/query
   - 请求体: {"query": "平安银行盈利情况", "stock_codes": ["000001"], "limit": 5}
   - 验证: 返回相关度排序的结果
   - 验证: 包含完整的匹配信息和相似度分数

B3: GET /api/v1/rag/collections
   - 验证: 返回所有RAG集合列表
   - 验证: 包含每个集合的统计信息

B4: GET /api/v1/rag/collections/{collection_name}/stats
   - 验证: 返回指定集合的详细统计
   - 验证: 包含向量数量、维度等信息
```

### 2.2 三层数据架构完整性测试

#### Test Suite C: 三层调用机制验证
**测试目标**: 验证Redis→PostgreSQL→AKShare的完整数据流

**测试场景**:
```
C1: 冷启动测试 (清空缓存后的首次调用)
   - 步骤1: 清空Redis中指定股票的缓存
   - 步骤2: 调用API获取股票数据
   - 验证: 数据从AKShare获取
   - 验证: 数据存储到PostgreSQL
   - 验证: 数据缓存到Redis
   - 验证: 响应时间符合AKShare调用特征

C2: 缓存命中测试 (相同请求的重复调用)
   - 步骤1: 重复调用相同的API
   - 验证: 数据从Redis获取
   - 验证: 响应时间 < 100ms
   - 验证: 返回数据与首次调用一致

C3: 数据库降级测试 (Redis不可用时)
   - 步骤1: 模拟Redis服务停止
   - 步骤2: 调用API获取股票数据
   - 验证: 数据从PostgreSQL获取
   - 验证: 系统正常响应

C4: AKShare降级测试 (数据库无数据时)
   - 步骤1: 请求数据库中不存在的股票数据
   - 步骤2: 调用API获取新股票数据
   - 验证: 数据从AKShare获取
   - 验证: 新数据存储到完整的三层架构
```

### 2.3 RAG系统端到端测试

#### Test Suite D: RAG完整流水线验证
**测试目标**: 验证文档切片→向量嵌入→检索查询的完整流程

**测试用例**:
```
D1: 文档向量化流水线测试
   - 输入: 000001平安银行的真实财务报告
   - 验证: 文档正确分割成语义块
   - 验证: 每个块成功生成768维向量
   - 验证: 向量存储到ChromaDB指定集合
   - 验证: 生成版本ID和元数据

D2: 多类型数据向量化测试
   - 输入: 600519贵州茅台的多种数据类型
     * 财务报告、新闻资讯、公告信息
   - 验证: 不同数据类型分别处理
   - 验证: 创建相应的向量集合
   - 验证: 元数据正确标记数据类型

D3: 语义检索准确性测试
   - 查询: "白酒行业龙头企业盈利能力分析"
   - 验证: 正确检索到茅台相关向量
   - 验证: 相似度分数 > 0.7
   - 验证: 返回原始文档片段

D4: 跨股票语义检索测试
   - 查询: "银行业风险控制措施"
   - 验证: 检索到多只银行股票的相关信息
   - 验证: 结果按相关度正确排序
   - 验证: 包含股票代码和数据来源

D5: RAG增量更新测试
   - 步骤1: 添加新的股票文档
   - 步骤2: 验证新向量正确添加
   - 步骤3: 验证旧数据仍可检索
   - 步骤4: 验证版本管理正确
```

### 2.4 批处理系统全功能测试

#### Test Suite E: 自动化批处理验证
**测试目标**: 验证所有批处理任务的自动执行

**测试用例**:
```
E1: RSS新闻监控自动化测试
   - 验证: RSS监控进程自动启动
   - 验证: 定期抓取新闻源数据
   - 验证: 新闻数据自动存储到数据库
   - 验证: 新闻数据自动向量化到RAG
   - 验证: 异常情况自动重试

E2: 自选股优先处理自动化测试
   - 步骤1: 配置高优先级自选股列表
   - 验证: 自选股数据优先更新
   - 验证: 批处理按优先级执行
   - 验证: 缓存预热完成
   - 验证: RAG数据及时更新

E3: 定时数据同步自动化测试
   - 验证: 每日收盘后自动同步数据
   - 验证: 所有活跃股票数据更新
   - 验证: 增量数据正确处理
   - 验证: 失败任务自动重试

E4: 批处理任务调度测试
   - 验证: APScheduler正常工作
   - 验证: 任务按设定时间执行
   - 验证: 并发任务正确管理
   - 验证: 任务状态正确跟踪
```

### 2.5 日志系统完整性测试

#### Test Suite F: 全组件日志验证
**测试目标**: 验证所有系统组件的日志记录功能

**测试用例**:
```
F1: API调用日志完整性测试
   - 执行: 上述所有API测试用例
   - 验证: 每个API调用都有对应日志记录
   - 验证: 日志包含请求参数、响应数据、执行时间
   - 验证: 错误情况正确记录

F2: AKShare调用日志测试
   - 执行: 所有需要AKShare的数据获取
   - 验证: AKShare函数调用被记录
   - 验证: 参数、返回数据、执行时间准确
   - 验证: API限流情况被记录

F3: 批处理执行日志测试
   - 执行: 所有批处理任务
   - 验证: 批处理开始、结束、进度被记录
   - 验证: 数据流量统计准确
   - 验证: 成功率和错误率正确

F4: RAG操作日志测试
   - 执行: 所有RAG操作
   - 验证: 向量化、查询操作被记录
   - 验证: 性能指标准确
   - 验证: 集合操作被跟踪

F5: 错误和异常日志测试
   - 模拟: 各种异常情况
   - 验证: 错误详情被完整记录
   - 验证: 堆栈跟踪信息完整
   - 验证: 恢复过程被记录
```

---

## 📊 Phase 3: 测试后数据变化统计

### 3.1 数据库变化对比
**记录格式**:
```
表名 | 测试前数量 | 测试后数量 | 新增数量 | 变化率
stock_basic_info | X | Y | Y-X | ((Y-X)/X)*100%
stock_kline_daily | X | Y | Y-X | ((Y-X)/X)*100%
... (所有表)
```

### 3.2 Redis缓存变化对比
**记录格式**:
```
缓存类型 | 测试前键数 | 测试后键数 | 新增键数 | 缓存命中率
basic_info:* | X | Y | Y-X | 计算命中率
kline:* | X | Y | Y-X | 计算命中率
... (所有缓存类型)
```

### 3.3 RAG向量库变化对比
**记录格式**:
```
集合名称 | 测试前向量数 | 测试后向量数 | 新增向量 | 数据类型
prism2_000001_financial | X | Y | Y-X | 财务数据
prism2_600519_news | X | Y | Y-X | 新闻数据
... (所有集合)
```

---

## 📋 Phase 4: 性能指标测量

### 4.1 API响应时间统计
- 各API端点的平均响应时间
- 95%分位数响应时间
- 最大响应时间
- 三层架构下的性能表现

### 4.2 数据处理吞吐量
- AKShare API调用频率和成功率
- 数据库写入性能 (记录/秒)
- RAG向量化处理速度 (文档/秒)
- 批处理任务执行效率

### 4.3 系统资源使用
- CPU使用率 (各个服务)
- 内存使用量 (PostgreSQL, Redis, ChromaDB)
- 磁盘I/O统计
- 网络带宽使用

---

## 🚨 Phase 5: 错误和异常测试

### 5.1 网络异常处理测试
- AKShare API超时处理
- 数据库连接中断恢复
- Redis服务不可用降级
- 网络波动影响测试

### 5.2 数据异常处理测试
- 股票代码不存在的处理
- 数据格式异常的处理
- 空数据和缺失数据处理
- 数据一致性验证

### 5.3 资源限制测试
- 并发请求上限测试
- 内存不足情况处理
- 磁盘空间不足处理
- API限流处理

---

## 📊 Phase 6: 测试报告生成要求

### 6.1 报告结构要求
```
1. 执行摘要
   - 测试覆盖率
   - 总体成功率
   - 关键发现

2. 功能测试结果
   - 各测试套件详细结果
   - 失败用例分析
   - 性能指标统计

3. 数据变化分析
   - 测试前后对比表
   - 数据流向验证
   - 存储效率分析

4. 系统性能评估
   - 响应时间分析
   - 吞吐量统计
   - 资源使用评估

5. 问题和风险清单
   - 发现的Bug列表
   - 性能瓶颈分析
   - 潜在风险评估

6. 改进建议
   - 优化建议
   - 扩展建议
   - 监控建议
```

### 6.2 报告格式要求
- JSON格式数据文件 (机器可读)
- Markdown格式报告 (人类可读)
- 包含图表和统计数据
- 支持版本对比

---

## ⚙️ 测试执行要求

### 🔧 测试环境要求
- 所有服务必须正常运行
- 网络连接稳定
- 充足的系统资源
- 真实数据源可访问

### 📝 测试执行原则
1. **严格按顺序执行**: 不得跳过任何测试用例
2. **完整记录过程**: 所有操作和结果必须记录
3. **只测试不修复**: 发现问题只记录，不修改代码
4. **数据真实性**: 100%使用真实数据源
5. **异常不中断**: 个别失败不影响整体测试进行

### 🎯 成功标准定义
- **API测试**: 所有端点返回正确数据格式
- **数据存储**: 所有数据正确写入对应存储系统
- **三层架构**: 缓存、降级机制正常工作
- **RAG系统**: 向量化和检索功能完整可用
- **批处理**: 自动化任务按预期执行
- **日志系统**: 所有操作被完整记录

---

## 📅 测试时间估算

| 测试阶段 | 预计耗时 | 说明 |
|---------|---------|------|
| 环境准备和基线记录 | 30分钟 | 记录初始状态 |
| API全面测试 | 90分钟 | 所有端点测试 |
| 三层架构测试 | 60分钟 | 缓存和降级测试 |
| RAG系统测试 | 45分钟 | 向量化和检索测试 |
| 批处理系统测试 | 120分钟 | 自动化任务测试 |
| 日志系统测试 | 30分钟 | 日志验证 |
| 异常和压力测试 | 60分钟 | 边界条件测试 |
| 数据统计和报告 | 45分钟 | 结果分析和报告 |
| **总计** | **8小时** | **完整系统测试** |

---

**测试计划批准**: 待用户确认后开始执行
**执行方式**: 严格按照本计划逐步执行，不进行任何代码修改
**最终目标**: 生成完整、准确、可信的系统功能和性能报告