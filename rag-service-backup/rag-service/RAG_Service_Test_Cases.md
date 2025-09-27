# RAG Service 完整测试案例文档

## 📋 文档信息

- **文档名称**: RAG Service 测试案例规格书
- **版本**: v1.0
- **创建日期**: 2025-09-18
- **适用版本**: RAG Service 隔离架构版本
- **测试环境**: Prism2共享基础设施 (PostgreSQL + Redis + ChromaDB)

---

## 🎯 测试概述

### 测试目标
验证RAG Service的**完整功能性**，包括业务功能和维护功能，确保在共享基础设施环境下的稳定运行。**所有测试必须使用真实数据源，不得使用任何模拟或测试数据。**

### 测试范围
- **A组**: 系统维护功能 (启动、配置、监控)
- **B组**: 核心业务功能 (RSS、向量化、搜索)
- **C组**: 数据管理功能 (Bootstrap、质量控制)
- **D组**: 集成测试功能 (端到端流程)

### 测试环境要求
```bash
# 必需的共享基础设施
✅ PostgreSQL: localhost:5432 (prism2-postgres)
✅ Redis: localhost:6379 (prism2-redis)
✅ ChromaDB: localhost:8000 (prism2-chromadb)
✅ RAG Service: localhost:8001 (目标服务)

# 必需的真实数据
✅ RSS真实数据: rss_data/isolated_rss_*.json (真实采集的新闻数据)
✅ 真实数据源: Reuters, Bloomberg, 新浪财经 等实际新闻源
✅ 真实时间范围: 基于实际RSS数据的时间戳
✅ 真实关键词: 从真实新闻标题中提取的关键词
```

---

## 📊 RAG Service 功能列表

### 🔧 A组: 系统维护功能

| 功能ID | 功能名称 | 功能描述 | 优先级 |
|--------|----------|----------|--------|
| A1 | 服务启动管理 | 启动、停止、重启RAG Service | P0 |
| A2 | 依赖服务连接 | 连接PostgreSQL、Redis、ChromaDB | P0 |
| A3 | 配置管理 | 环境变量、配置文件加载 | P0 |
| A4 | 健康监控 | API健康检查、服务状态监控 | P0 |
| A5 | 日志管理 | 服务日志记录和查看 | P1 |
| A6 | 错误处理 | 异常恢复、容错机制 | P1 |

### 🏢 B组: 核心业务功能

| 功能ID | 功能名称 | 功能描述 | 优先级 |
|--------|----------|----------|--------|
| B1 | RSS监控收集 | 定时收集RSS新闻数据 | P0 |
| B2 | 文档向量化 | 使用bge-large-zh-v1.5进行向量化 | P0 |
| B3 | 语义搜索 | ChromaDB向量相似度搜索 | P0 |
| B4 | 上下文增强 | 为AI Service提供增强上下文 | P0 |
| B5 | 翻译服务 | 隔离翻译服务处理 | P1 |
| B6 | 相似度计算 | 文档相似度计算 | P1 |

### 📈 C组: 数据管理功能

| 功能ID | 功能名称 | 功能描述 | 优先级 |
|--------|----------|----------|--------|
| C1 | Bootstrap初始化 | 大量历史数据导入管理 | P0 |
| C2 | 任务进度跟踪 | Bootstrap任务状态和进度监控 | P0 |
| C3 | 批量处理记录 | 批次处理日志和统计 | P1 |
| C4 | 文档质量评估 | 文档质量打分和过滤 | P1 |
| C5 | 数据去重 | 重复文档检测和处理 | P1 |

### 🔄 D组: 集成测试功能

| 功能ID | 功能名称 | 功能描述 | 优先级 |
|--------|----------|----------|--------|
| D1 | 端到端流程 | RSS→向量化→存储→搜索完整流程 | P0 |
| D2 | 并发处理 | 多用户并发访问测试 | P1 |
| D3 | 性能基准 | 响应时间、吞吐量测试 | P1 |
| D4 | 数据一致性 | 数据完整性和一致性验证 | P1 |

---

## 🧪 详细测试案例

### TC-A1: 服务启动管理测试

#### A1.1 服务启动功能测试
**测试描述**: 验证RAG Service可以正常启动并监听8001端口

**测试步骤**:
```bash
1. 确保依赖服务运行: podman ps | grep prism2
2. 启动RAG Service: ./start_rag_service.sh
3. 验证进程存在: ps -ef | grep uvicorn
4. 验证端口监听: netstat -tuln | grep 8001
```

**预期结果**:
- ✅ 服务进程正常启动
- ✅ 端口8001处于LISTEN状态
- ✅ 服务PID写入rag_service.pid

**验证命令**:
```bash
curl -f http://localhost:8001/api/health
# 期望: HTTP 200, {"status": "healthy"}
```

#### A1.2 服务停止功能测试
**测试描述**: 验证RAG Service可以优雅停止

**测试步骤**:
```bash
1. 记录当前PID: cat rag_service.pid
2. 停止服务: ./stop_rag_service.sh
3. 验证进程终止: ps -p $PID
4. 验证端口释放: netstat -tuln | grep 8001
```

**预期结果**:
- ✅ 进程优雅终止
- ✅ 端口8001释放
- ✅ PID文件清理

**验证命令**:
```bash
curl -f http://localhost:8001/api/health
# 期望: Connection failed
```

### TC-A2: 依赖服务连接测试

#### A2.1 PostgreSQL连接测试
**测试描述**: 验证RAG Service可以连接共享PostgreSQL数据库

**测试步骤**:
```bash
1. 启动RAG Service
2. 检查启动日志: tail -f logs/rag_service_*.log
3. 查找数据库连接日志
```

**预期结果**:
- ✅ 无PostgreSQL连接错误
- ✅ 数据表自动创建成功
- ✅ 服务正常启动完成

**验证命令**:
```bash
# 检查表是否创建
podman exec prism2-postgres psql -U postgres -c "\dt" | grep bootstrap_tasks
# 期望: bootstrap_tasks表存在
```

#### A2.2 ChromaDB连接测试
**测试描述**: 验证RAG Service可以连接共享ChromaDB服务

**预期结果**:
- ✅ ChromaDB连接正常
- ✅ 集合可以创建和查询

**验证命令**:
```bash
curl -s http://localhost:8001/api/health | jq '.dependencies.chromadb'
# 期望: "connected"
```

#### A2.3 Redis连接测试
**测试描述**: 验证RAG Service可以连接共享Redis缓存

**预期结果**:
- ✅ Redis连接正常
- ✅ 缓存读写功能正常

**验证命令**:
```bash
curl -s http://localhost:8001/api/health | jq '.dependencies.redis'
# 期望: "connected"
```

### TC-A4: 健康监控测试

#### A4.1 API健康检查测试
**测试描述**: 验证健康检查API返回正确状态

**测试步骤**:
```bash
1. 发送健康检查请求
2. 验证响应格式和内容
3. 验证HTTP状态码
```

**验证命令**:
```bash
response=$(curl -s http://localhost:8001/api/health)
echo $response | jq '.status, .dependencies'
# 期望: status="healthy", 所有dependencies="connected"
```

**预期结果**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-18T...",
  "dependencies": {
    "chromadb": "connected",
    "postgresql": "connected",
    "redis": "connected"
  },
  "version": "1.0.0"
}
```

---

### TC-B1: RSS监控收集测试

#### B1.1 RSS数据收集测试
**测试描述**: 验证隔离RSS监控可以收集新闻数据

**测试步骤**:
```bash
1. 启动RSS监控: ./start_isolated_rss.sh
2. 等待15分钟数据收集周期
3. 检查数据文件: ls rss_data/
4. 验证数据内容格式
```

**预期结果**:
- ✅ 生成JSON数据文件
- ✅ 数据格式符合schema
- ✅ 包含文章标题、内容、链接等

**验证命令**:
```bash
latest_file=$(ls -t rss_data/isolated_rss_*.json | head -1)
cat $latest_file | jq '.metadata.total_articles, .articles[0].title'
# 期望: 数字 > 0, 有效文章标题
```

#### B1.2 翻译服务测试
**测试描述**: 验证隔离翻译服务正常工作

**预期结果**:
- ✅ 英文内容被翻译
- ✅ 中文内容跳过翻译
- ✅ 翻译状态正确记录

**验证命令**:
```bash
latest_file=$(ls -t rss_data/isolated_rss_*.json | head -1)
cat $latest_file | jq '.articles[] | select(.translated==true)'
# 期望: 有翻译记录的文章
```

#### B1.3 数据格式标准化测试
**测试描述**: 验证RSS数据符合标准JSON schema

**预期结果**:
- ✅ 包含metadata字段
- ✅ 包含articles数组
- ✅ 每篇文章有必需字段

**验证命令**:
```bash
latest_file=$(ls -t rss_data/isolated_rss_*.json | head -1)
cat $latest_file | jq -e '.metadata, .articles[0].id, .articles[0].title, .articles[0].content'
# 期望: 所有字段存在，jq命令成功退出
```

---

### TC-B2: 文档向量化测试

#### B2.1 基础向量化测试
**测试描述**: 验证使用真实RSS数据进行文档向量化功能

**测试步骤**:
```bash
1. 获取最新的真实RSS数据
2. 提取真实文章内容
3. 调用向量化API处理真实数据
4. 验证响应结果
```

**API调用**:
```bash
# 获取真实RSS数据中的第一篇文章
latest_rss=$(ls -t rss_data/isolated_rss_*.json | head -1)
real_article=$(cat "$latest_rss" | jq -r '.articles[0]')
article_id=$(echo "$real_article" | jq -r '.id')
article_content=$(echo "$real_article" | jq -r '.content')
article_title=$(echo "$real_article" | jq -r '.title')
article_source=$(echo "$real_article" | jq -r '.source')

# 使用真实文章数据进行向量化测试
curl -X POST http://localhost:8001/api/rag/embed \
  -H "Content-Type: application/json" \
  -d "{
    \"documents\": [
      {
        \"id\": \"$article_id\",
        \"content\": \"$article_content\",
        \"metadata\": {
          \"source\": \"$article_source\",
          \"title\": \"$article_title\"
        }
      }
    ]
  }"
```

**预期结果**:
```json
{
  "success": true,
  "processed_count": 1,
  "failed_documents": [],
  "processing_time": 1.23
}
```

#### B2.2 批量向量化测试
**测试描述**: 验证批量文档向量化性能

**预期结果**:
- ✅ 批量处理成功率 > 95%
- ✅ 处理时间合理 (< 2秒/文档)
- ✅ 失败文档有明确错误信息

---

### TC-B3: 语义搜索测试

#### B3.1 基础搜索测试
**测试描述**: 验证使用真实关键词进行语义搜索功能

**测试步骤**:
```bash
1. 从真实RSS数据中提取关键词
2. 使用真实关键词进行搜索
3. 验证搜索结果的真实性
```

**API调用**:
```bash
# 从真实RSS数据中提取关键词进行搜索
latest_rss=$(ls -t rss_data/isolated_rss_*.json | head -1)
real_keywords=$(cat "$latest_rss" | jq -r '.articles[0].title' | head -c 50)

curl -X POST http://localhost:8001/api/rag/search \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"$real_keywords\",
    \"limit\": 5,
    \"similarity_threshold\": 0.6
  }"
```

**预期结果**:
```json
{
  "results": [
    {
      "document_id": "doc_xxx",
      "content": "相关文档内容片段...",
      "similarity_score": 0.85,
      "metadata": {
        "title": "文档标题",
        "source": "来源"
      }
    }
  ],
  "search_time": 0.05,
  "total_documents": 1520
}
```

#### B3.2 过滤搜索测试
**测试描述**: 验证使用真实数据源进行元数据过滤搜索

**测试步骤**:
```bash
1. 从真实RSS数据中获取实际的数据源信息
2. 使用真实数据源进行过滤搜索
3. 验证过滤结果的准确性
```

**API调用**:
```bash
# 使用真实RSS数据中的数据源进行过滤搜索
latest_rss=$(ls -t rss_data/isolated_rss_*.json | head -1)
real_source=$(cat "$latest_rss" | jq -r '.articles[0].source')
real_query=$(cat "$latest_rss" | jq -r '.articles[1].title' | head -c 30)

curl -X POST http://localhost:8001/api/rag/search \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"$real_query\",
    \"filters\": {\"source\": \"$real_source\"},
    \"limit\": 3
  }"
```

**预期结果**:
- ✅ 只返回指定真实数据源的文档
- ✅ 相似度分数合理 (> 0.5)
- ✅ 响应时间 < 100ms

---

### TC-C1: Bootstrap初始化测试

#### C1.1 Bootstrap任务创建测试
**测试描述**: 验证使用真实数据源创建数据初始化任务

**测试步骤**:
```bash
1. 检查现有真实RSS数据源
2. 使用真实的时间范围创建Bootstrap任务
3. 验证任务创建和真实数据源配置
```

**API调用**:
```bash
# 获取真实RSS数据的时间范围
latest_rss=$(ls -t rss_data/isolated_rss_*.json | head -1)
real_sources=$(cat "$latest_rss" | jq -r '.articles[].source' | sort -u | head -3 | jq -R . | jq -s .)
earliest_date=$(cat "$latest_rss" | jq -r '.articles[].published' | sort | head -1 | cut -d'T' -f1)
latest_date=$(cat "$latest_rss" | jq -r '.articles[].published' | sort -r | head -1 | cut -d'T' -f1)

curl -X POST http://localhost:8001/api/rag/bootstrap \
  -H "Content-Type: application/json" \
  -d "{
    \"data_sources\": $real_sources,
    \"time_range\": {
      \"start\": \"$earliest_date\",
      \"end\": \"$latest_date\"
    },
    \"batch_size\": 50,
    \"max_concurrent\": 3
  }"
```

**预期结果**:
```json
{
  "task_id": "uuid-string",
  "estimated_documents": 5000,
  "estimated_time_hours": 2.5,
  "status": "pending",
  "progress_url": "/api/rag/bootstrap/{task_id}"
}
```

#### C1.2 任务进度查询测试
**测试描述**: 验证可以查询Bootstrap任务进度

**API调用**:
```bash
curl -X GET http://localhost:8001/api/rag/bootstrap/{task_id}
```

**预期结果**:
```json
{
  "task_id": "uuid-string",
  "status": "running",
  "progress_percentage": 45.5,
  "processed_documents": 2275,
  "total_documents": 5000,
  "current_stage": "向量化处理",
  "error_count": 12,
  "estimated_remaining_time": 1.25
}
```

---

### TC-D1: 端到端集成测试

#### D1.1 完整流程测试
**测试描述**: 验证RSS→向量化→存储→搜索完整流程

**测试步骤**:
```bash
1. 启动RSS监控，收集数据
2. 等待数据文件生成
3. 触发向量化处理
4. 执行语义搜索验证
5. 检查数据一致性
```

**预期结果**:
- ✅ RSS数据成功收集
- ✅ 文档成功向量化存储
- ✅ 搜索返回相关结果
- ✅ 数据链路完整无损失

**验证命令**:
```bash
# 1. 检查RSS数据
ls rss_data/isolated_rss_*.json

# 2. 检查向量存储
curl -s http://localhost:8001/api/rag/search -d '{"query":"测试","limit":1}' | jq '.results | length'

# 3. 检查数据库记录
podman exec prism2-postgres psql -U postgres -c "SELECT COUNT(*) FROM document_quality_scores;"
```

---

## 📊 测试执行结果记录模板

### 测试环境信息
```
测试日期: [YYYY-MM-DD HH:MM:SS]
测试执行者: [姓名]
RAG Service版本: [版本号]
基础设施状态:
  - PostgreSQL: [prism2-postgres状态]
  - Redis: [prism2-redis状态]
  - ChromaDB: [prism2-chromadb状态]
```

### 测试结果汇总表

| 测试组 | 总测试数 | 通过数 | 失败数 | 跳过数 | 通过率 |
|--------|---------|--------|--------|--------|--------|
| A组-系统维护 | 6 | _ | _ | _ | _% |
| B组-业务功能 | 6 | _ | _ | _ | _% |
| C组-数据管理 | 5 | _ | _ | _ | _% |
| D组-集成测试 | 4 | _ | _ | _ | _% |
| **总计** | **21** | **_** | **_** | **_** | **_%** |

### 详细测试记录

| 测试ID | 测试名称 | 状态 | 执行时间 | 备注 |
|--------|----------|------|----------|------|
| A1.1 | 服务启动功能 | [PASS/FAIL] | [时间] | [备注] |
| A1.2 | 服务停止功能 | [PASS/FAIL] | [时间] | [备注] |
| A2.1 | PostgreSQL连接 | [PASS/FAIL] | [时间] | [备注] |
| A2.2 | ChromaDB连接 | [PASS/FAIL] | [时间] | [备注] |
| A2.3 | Redis连接 | [PASS/FAIL] | [时间] | [备注] |
| ... | ... | ... | ... | ... |

### 缺陷记录

| 缺陷ID | 缺陷描述 | 严重程度 | 相关测试案例 | 状态 |
|--------|----------|----------|--------------|------|
| BUG-001 | [缺陷描述] | [高/中/低] | [测试ID] | [待修复/已修复] |

### 测试结论

- **整体评估**: [通过/不通过]
- **关键发现**: [重要发现]
- **风险提示**: [风险点]
- **建议**: [改进建议]

---

## 🚀 自动化测试脚本

为方便执行，提供自动化测试脚本 `run_rag_tests.sh`:

```bash
#!/bin/bash
# RAG Service 自动化测试脚本
# 基于本测试案例文档

echo "🧪 开始执行RAG Service完整测试"
echo "基于测试案例文档: RAG_Service_Test_Cases.md"

# 执行所有测试组
./test_group_A_system.sh  # 系统维护功能
./test_group_B_business.sh  # 业务功能
./test_group_C_data.sh      # 数据管理功能
./test_group_D_integration.sh  # 集成测试

# 生成测试报告
generate_test_report.sh
```

## ⚠️ 重要约束条件

### 🚫 严禁使用模拟数据
- **不允许**: 任何形式的测试数据、模拟数据、示例数据
- **不允许**: 硬编码的测试内容、虚构的新闻标题
- **不允许**: `test_*` 形式的虚假数据源名称

### ✅ 必须使用真实数据
- **必须**: 使用 `rss_data/isolated_rss_*.json` 中的真实RSS数据
- **必须**: 使用真实新闻源（Reuters、Bloomberg、新浪财经等）
- **必须**: 使用真实的文章标题、内容、发布时间
- **必须**: 使用真实的数据源名称和时间戳

### 🔍 数据真实性验证
每个测试案例都包含数据来源验证：
```bash
# 验证数据来源真实性
echo "数据来源验证:"
echo "文章标题: $article_title"
echo "数据源: $article_source"
echo "发布时间: $publish_time"
echo "内容长度: $(echo "$article_content" | wc -c) 字符"
```

---

这个测试案例文档提供了：
1. **完整功能列表** - 涵盖业务和维护功能
2. **真实数据测试方法** - 使用实际RSS数据的API调用和验证命令
3. **预期结果** - 明确的成功标准
4. **Evidence要求** - 可执行的验证命令（使用真实数据）
5. **结果记录模板** - 标准化的测试结果记录格式

**所有测试必须基于真实的RSS数据执行，确保测试结果的可信度和实用性。**