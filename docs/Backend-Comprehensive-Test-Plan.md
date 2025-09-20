# Prism2 Backend全面测试计划

## 📋 测试概览

**测试计划版本**: v1.0
**创建时间**: 2025-09-20
**测试目标**: Backend全系统功能验证，涵盖在线API和批处理系统
**测试数据**:
- **Online测试股票**: 601727 (上海电气)
- **批处理自选股**: 603993 (洛阳钼业), 000630 (铜陵有色), 300085 (银之杰)

## 🎯 测试目标

### 1. 功能完整性验证
- ✅ 验证所有API endpoints正常工作
- ✅ 验证批处理jobs执行成功
- ✅ 验证数据流在三层架构中正确传递
- ✅ 验证RAG集成功能正常

### 2. 数据一致性验证
- ✅ Redis缓存数据正确性
- ✅ PostgreSQL存储数据完整性
- ✅ 向量数据库同步准确性
- ✅ 版本管理功能正确性

### 3. 性能指标验证
- ✅ API响应时间 < 2秒
- ✅ 缓存命中率 > 80%
- ✅ 批处理job执行时间合理
- ✅ 数据库查询效率

## 🧪 测试计划矩阵

| 模块类型 | 组件名称 | 测试方法 | 测试数据 | 预期结果 |
|---------|---------|---------|---------|---------|
| **Online API** | Dashboard API | HTTP请求 | 601727 | JSON响应+数据库更新 |
| **Batch Jobs** | 自选股处理 | 手动触发 | 603993,000630,300085 | 批处理日志+数据存储 |
| **RAG System** | 版本管理 | 集成测试 | 测试股票 | 版本创建+激活 |
| **Data Layer** | 三层架构 | 数据流测试 | 所有测试股票 | 缓存+存储+API一致性 |

---

## 🌐 Part 1: Online API系统测试

### 1.1 Enhanced Dashboard API测试

#### 测试用例 API-001: 主要仪表板接口
**接口**: `POST /api/v1/stocks/dashboard`
**测试股票**: 601727 (上海电气)

**测试步骤**:
```bash
# 1. 清空相关缓存
redis-cli DEL "*601727*"

# 2. 发送API请求
curl -X POST "http://localhost:8000/api/v1/stocks/dashboard" \
     -H "Content-Type: application/json" \
     -d '{
       "stock_code": "601727",
       "data_types": ["realtime", "kline", "basic_info", "financial", "announcements", "shareholders", "longhubang"],
       "kline_period": "daily",
       "kline_days": 60,
       "news_days": 7
     }'
```

**预期结果**:
```json
{
  "success": true,
  "stock_code": "601727",
  "timestamp": "2025-09-20T...",
  "data_sources": {
    "realtime": ["akshare"],
    "kline": ["akshare"],
    "basic_info": ["akshare"],
    "financial": ["akshare"],
    "announcements": ["akshare"],
    "shareholders": ["akshare"],
    "longhubang": ["akshare"]
  },
  "cache_info": {
    "redis_hits": "0",
    "postgres_hits": "0",
    "akshare_calls": "7"
  },
  "data": {
    "realtime": { /* 实时数据 */ },
    "kline": { /* K线数据 */ },
    "basic_info": { /* 基本信息 */ },
    "financial": { /* 财务数据 */ },
    "announcements": { /* 公告数据 */ },
    "shareholders": { /* 股东数据 */ },
    "longhubang": { /* 龙虎榜数据 */ }
  }
}
```

**数据库验证**:
```sql
-- 1. 检查PostgreSQL数据存储
SELECT COUNT(*) FROM stock_financial WHERE stock_code = '601727';
SELECT COUNT(*) FROM stock_announcements WHERE stock_code = '601727';
SELECT COUNT(*) FROM stock_shareholders WHERE stock_code = '601727';
SELECT COUNT(*) FROM stock_longhubang WHERE stock_code = '601727';

-- 预期结果: 每个表至少1条记录
```

**Redis验证**:
```bash
# 2. 检查Redis缓存
redis-cli KEYS "*601727*"
# 预期结果: 7个缓存键(对应7种数据类型)

redis-cli GET "realtime:601727"
# 预期结果: JSON格式的实时数据
```

#### 测试用例 API-002: 缓存命中测试
**目的**: 验证三层架构缓存机制

**测试步骤**:
```bash
# 1. 第二次请求相同数据
curl -X POST "http://localhost:8000/api/v1/stocks/dashboard" \
     -H "Content-Type: application/json" \
     -d '{
       "stock_code": "601727",
       "data_types": ["realtime", "kline", "basic_info"],
       "kline_period": "daily",
       "kline_days": 60
     }'
```

**预期结果**:
```json
{
  "success": true,
  "cache_info": {
    "redis_hits": "2",
    "postgres_hits": "1",
    "akshare_calls": "0"
  }
}
```

#### 测试用例 API-003: 根路径测试
**接口**: `GET /`

**测试步骤**:
```bash
curl -X GET "http://localhost:8000/"
```

**预期结果**:
```json
{
  "message": "Prism2 Enhanced Dashboard API",
  "status": "operational",
  "version": "v2.0",
  "timestamp": "2025-09-20T..."
}
```

---

## ⚡ Part 2: 批处理系统测试

### 2.1 自选股管理测试

#### 测试用例 BATCH-001: 创建测试自选股列表
**目的**: 创建包含测试股票的自选股列表

**测试步骤**:
```python
# 执行批处理自选股创建脚本
python -c "
from batch_processor.services.watchlist_service import WatchlistService
from batch_processor.models.watchlist import WatchlistCreate

service = WatchlistService()

# 创建测试自选股列表
watchlist_data = WatchlistCreate(
    user_id='test_user_comprehensive',
    watchlist_name='综合测试股票池',
    description='用于Backend全面测试的股票组合',
    stock_codes=['603993', '000630', '300085'],
    priority_level=5,
    data_types=['financial', 'announcements', 'shareholders', 'longhubang'],
    auto_batch=True
)

result = service.create_watchlist(watchlist_data)
print(f'自选股列表创建结果: {result}')
"
```

**预期结果**:
```python
{
  "id": 1,
  "user_id": "test_user_comprehensive",
  "watchlist_name": "综合测试股票池",
  "stock_codes": ["603993", "000630", "300085"],
  "priority_level": 5,
  "created_at": "2025-09-20T..."
}
```

**数据库验证**:
```sql
SELECT * FROM user_watchlists WHERE user_id = 'test_user_comprehensive';
-- 预期结果: 1条记录，包含3只股票代码
```

### 2.2 批处理任务执行测试

#### 测试用例 BATCH-002: 自选股批处理执行
**目的**: 验证自选股优先级批处理功能

**测试步骤**:
```python
# 执行自选股批处理
python -c "
import asyncio
from batch_processor.processors.watchlist_processor import WatchlistProcessor

async def test_watchlist_batch():
    processor = WatchlistProcessor()

    # 获取高优先级自选股列表
    watchlists = await processor.get_priority_watchlists(min_priority=4)
    print(f'发现 {len(watchlists)} 个高优先级自选股列表')

    # 执行批处理
    for watchlist in watchlists:
        print(f'处理自选股列表: {watchlist[\"watchlist_name\"]}')
        result = await processor.process_watchlist_batch(
            watchlist_id=watchlist['id'],
            force_refresh=True
        )
        print(f'批处理结果: {result}')

asyncio.run(test_watchlist_batch())
"
```

**预期结果**:
```python
发现 1 个高优先级自选股列表
处理自选股列表: 综合测试股票池
批处理结果: {
  "watchlist_id": 1,
  "processed_stocks": 3,
  "successful_stocks": 3,
  "failed_stocks": 0,
  "total_data_types": 4,
  "processing_time": 45.6,
  "cache_updates": 12,
  "errors": []
}
```

**数据库验证**:
```sql
-- 检查批处理任务记录
SELECT * FROM batch_jobs
WHERE job_type = 'watchlist_warm'
  AND status = 'success'
ORDER BY created_at DESC LIMIT 1;

-- 检查股票数据是否存储
SELECT stock_code, COUNT(*) FROM stock_financial
WHERE stock_code IN ('603993', '000630', '300085')
GROUP BY stock_code;

SELECT stock_code, COUNT(*) FROM stock_announcements
WHERE stock_code IN ('603993', '000630', '300085')
GROUP BY stock_code;

SELECT stock_code, COUNT(*) FROM stock_shareholders
WHERE stock_code IN ('603993', '000630', '300085')
GROUP BY stock_code;

SELECT stock_code, COUNT(*) FROM stock_longhubang
WHERE stock_code IN ('603993', '000630', '300085')
GROUP BY stock_code;
```

**Redis验证**:
```bash
# 检查缓存数据
redis-cli KEYS "*603993*" | wc -l  # 预期: >= 4
redis-cli KEYS "*000630*" | wc -l  # 预期: >= 4
redis-cli KEYS "*300085*" | wc -l  # 预期: >= 4

# 检查具体缓存数据
redis-cli GET "financial:603993"
redis-cli GET "announcements:000630"
redis-cli GET "shareholders:300085"
```

### 2.3 RAG同步系统测试

#### 测试用例 RAG-001: RAG批量同步测试
**目的**: 验证RAG集成功能完整性

**测试步骤**:
```python
# 执行RAG同步测试
python -c "
import asyncio
from batch_processor.processors.rag_sync_processor import RAGSyncProcessor

async def test_rag_sync():
    processor = RAGSyncProcessor()

    # 测试股票代码
    test_stocks = ['603993', '000630', '300085']
    test_data_types = ['financial', 'announcements']

    print('开始RAG同步测试...')
    result = await processor.sync_batch_data_to_rag(
        stock_codes=test_stocks,
        data_types=test_data_types,
        force_refresh=True
    )

    print(f'RAG同步结果: {result}')

    # 验证版本管理
    from batch_processor.services.version_manager import VersionManager
    vm = VersionManager()

    for stock_code in test_stocks:
        for data_type in test_data_types:
            active_version = await vm.get_active_version(stock_code, data_type)
            print(f'{stock_code}-{data_type} 活跃版本: {active_version[\"version_id\"] if active_version else \"None\"}')

asyncio.run(test_rag_sync())
"
```

**预期结果**:
```python
开始RAG同步测试...
RAG同步结果: {
  "total_stocks": 3,
  "total_data_types": 2,
  "processed_items": 6,
  "successful_syncs": 6,
  "failed_syncs": 0,
  "skipped_syncs": 0,
  "new_versions_created": 6,
  "versions_activated": 6,
  "processing_time": 12.5
}

603993-financial 活跃版本: 12345678-abcd-ef01-2345-678901234567
603993-announcements 活跃版本: 23456789-bcde-f012-3456-789012345678
000630-financial 活跃版本: 34567890-cdef-0123-4567-890123456789
...
```

**数据库验证**:
```sql
-- 检查RAG版本数据
SELECT stock_code, data_type, vector_status, chunk_count, activated_at
FROM rag_data_versions
WHERE stock_code IN ('603993', '000630', '300085')
  AND vector_status = 'active'
ORDER BY stock_code, data_type;

-- 预期结果: 6条active状态的版本记录

-- 检查向量映射数据
SELECT vm.version_id, vm.collection_name, vm.chunk_index, LENGTH(vm.chunk_text) as text_length
FROM rag_vector_mappings vm
JOIN rag_data_versions rdv ON vm.version_id = rdv.version_id
WHERE rdv.stock_code IN ('603993', '000630', '300085')
ORDER BY rdv.stock_code, rdv.data_type, vm.chunk_index;

-- 预期结果: 多条向量映射记录，每个版本对应多个文本块
```

#### 测试用例 RAG-002: 版本生命周期测试
**目的**: 验证"前一版本非活性，新版信息活性"功能

**测试步骤**:
```python
# 版本生命周期测试
python -c "
import asyncio
from batch_processor.services.version_manager import VersionManager

async def test_version_lifecycle():
    vm = VersionManager()

    test_stock = '603993'
    test_data_type = 'financial'

    print('=== 版本生命周期测试 ===')

    # 1. 创建第一个版本
    version1 = await vm.create_new_version(
        stock_code=test_stock,
        data_type=test_data_type,
        source_data={'version': 1, 'test_data': 'first_version'}
    )
    print(f'版本1创建: {version1}')

    # 2. 激活第一个版本
    await vm.activate_version(version1)
    active1 = await vm.get_active_version(test_stock, test_data_type)
    print(f'激活版本1: {active1[\"version_id\"]}')

    # 3. 创建第二个版本
    version2 = await vm.create_new_version(
        stock_code=test_stock,
        data_type=test_data_type,
        source_data={'version': 2, 'test_data': 'second_version'}
    )
    print(f'版本2创建: {version2}')

    # 4. 激活第二个版本（应该自动停用版本1）
    await vm.activate_version(version2)
    active2 = await vm.get_active_version(test_stock, test_data_type)
    print(f'激活版本2: {active2[\"version_id\"]}')

    # 5. 验证版本1被停用
    version1_info = await vm.get_version_by_id(version1)
    print(f'版本1状态: {version1_info[\"vector_status\"]}')

    # 6. 获取版本历史
    history = await vm.get_version_history(test_stock, test_data_type, limit=5)
    print(f'版本历史: {len(history)} 个版本')
    for h in history:
        print(f'  {h[\"version_id\"][:8]}... 状态: {h[\"vector_status\"]} 创建: {h[\"created_at\"]}')

asyncio.run(test_version_lifecycle())
"
```

**预期结果**:
```python
=== 版本生命周期测试 ===
版本1创建: 12345678-abcd-ef01-2345-678901234567
激活版本1: 12345678-abcd-ef01-2345-678901234567
版本2创建: 23456789-bcde-f012-3456-789012345678
激活版本2: 23456789-bcde-f012-3456-789012345678
版本1状态: deprecated
版本历史: 2 个版本
  23456789... 状态: active 创建: 2025-09-20 10:30:45
  12345678... 状态: deprecated 创建: 2025-09-20 10:30:40
```

---

## 📊 Part 3: 数据一致性验证测试

### 3.1 三层架构数据流测试

#### 测试用例 DATA-001: 完整数据流验证
**目的**: 验证 Redis → PostgreSQL → AKShare 三层架构数据一致性

**测试步骤**:
```python
# 数据流一致性测试
python -c "
import redis
import psycopg2
import json
from psycopg2.extras import RealDictCursor

def test_data_consistency():
    # 连接配置
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    pg_conn = psycopg2.connect(
        host='localhost', database='prism2', user='prism2',
        password='prism2_secure_password', cursor_factory=RealDictCursor
    )

    test_stock = '601727'
    data_types = ['financial', 'announcements', 'shareholders']

    print('=== 三层架构数据一致性验证 ===')

    for data_type in data_types:
        print(f'\\n检查 {test_stock} - {data_type}:')

        # 1. 检查Redis缓存
        cache_key = f'{data_type}:{test_stock}'
        redis_data = redis_client.get(cache_key)
        print(f'  Redis: {\"有数据\" if redis_data else \"无数据\"} ({len(redis_data) if redis_data else 0} 字符)')

        # 2. 检查PostgreSQL存储
        cursor = pg_conn.cursor()
        table_map = {
            'financial': ('stock_financial', 'summary_data'),
            'announcements': ('stock_announcements', 'announcement_data'),
            'shareholders': ('stock_shareholders', 'shareholders_data')
        }

        table_name, data_column = table_map[data_type]
        cursor.execute(f'SELECT {data_column}, updated_at FROM {table_name} WHERE stock_code = %s ORDER BY updated_at DESC LIMIT 1', (test_stock,))
        pg_result = cursor.fetchone()
        print(f'  PostgreSQL: {\"有数据\" if pg_result else \"无数据\"} (更新时间: {pg_result[\"updated_at\"] if pg_result else \"N/A\"})')

        # 3. 数据内容比对（如果都存在）
        if redis_data and pg_result:
            redis_obj = json.loads(redis_data)
            pg_obj = pg_result[data_column]

            # 简单的数据对比
            redis_keys = set(redis_obj.keys()) if isinstance(redis_obj, dict) else set()
            pg_keys = set(pg_obj.keys()) if isinstance(pg_obj, dict) else set()

            if redis_keys and pg_keys:
                common_keys = redis_keys & pg_keys
                consistency_rate = len(common_keys) / max(len(redis_keys), len(pg_keys))
                print(f'  数据一致性: {consistency_rate:.2%} ({len(common_keys)}/{max(len(redis_keys), len(pg_keys))} 字段匹配)')

    pg_conn.close()

test_data_consistency()
"
```

**预期结果**:
```
=== 三层架构数据一致性验证 ===

检查 601727 - financial:
  Redis: 有数据 (2341 字符)
  PostgreSQL: 有数据 (更新时间: 2025-09-20 10:25:30)
  数据一致性: 95.00% (19/20 字段匹配)

检查 601727 - announcements:
  Redis: 有数据 (1523 字符)
  PostgreSQL: 有数据 (更新时间: 2025-09-20 10:25:30)
  数据一致性: 100.00% (5/5 字段匹配)

检查 601727 - shareholders:
  Redis: 有数据 (892 字符)
  PostgreSQL: 有数据 (更新时间: 2025-09-20 10:25:30)
  数据一致性: 100.00% (3/3 字段匹配)
```

### 3.2 批处理数据质量验证

#### 测试用例 DATA-002: 批处理数据完整性检查
**目的**: 确保批处理生成的数据符合质量标准

**测试步骤**:
```sql
-- 数据完整性验证脚本
SELECT
    '数据完整性报告' as report_type,
    '2025-09-20' as test_date;

-- 1. 检查测试股票数据覆盖率
SELECT
    '股票数据覆盖率' as metric,
    stock_code,
    CASE WHEN financial_count > 0 THEN '✓' ELSE '✗' END as financial,
    CASE WHEN announcements_count > 0 THEN '✓' ELSE '✗' END as announcements,
    CASE WHEN shareholders_count > 0 THEN '✓' ELSE '✗' END as shareholders,
    CASE WHEN longhubang_count > 0 THEN '✓' ELSE '✗' END as longhubang
FROM (
    SELECT
        codes.stock_code,
        COALESCE(f.cnt, 0) as financial_count,
        COALESCE(a.cnt, 0) as announcements_count,
        COALESCE(s.cnt, 0) as shareholders_count,
        COALESCE(l.cnt, 0) as longhubang_count
    FROM (VALUES ('603993'), ('000630'), ('300085'), ('601727')) AS codes(stock_code)
    LEFT JOIN (SELECT stock_code, COUNT(*) as cnt FROM stock_financial GROUP BY stock_code) f ON codes.stock_code = f.stock_code
    LEFT JOIN (SELECT stock_code, COUNT(*) as cnt FROM stock_announcements GROUP BY stock_code) a ON codes.stock_code = a.stock_code
    LEFT JOIN (SELECT stock_code, COUNT(*) as cnt FROM stock_shareholders GROUP BY stock_code) s ON codes.stock_code = s.stock_code
    LEFT JOIN (SELECT stock_code, COUNT(*) as cnt FROM stock_longhubang GROUP BY stock_code) l ON codes.stock_code = l.stock_code
) coverage_data;

-- 2. 检查RAG版本数据
SELECT
    'RAG版本状态' as metric,
    stock_code,
    data_type,
    vector_status,
    chunk_count,
    DATE(activated_at) as activated_date
FROM rag_data_versions
WHERE stock_code IN ('603993', '000630', '300085', '601727')
ORDER BY stock_code, data_type;

-- 3. 检查批处理任务状态
SELECT
    '批处理任务状态' as metric,
    job_type,
    status,
    COUNT(*) as job_count,
    AVG(duration_seconds) as avg_duration,
    SUM(success_count) as total_success,
    SUM(failed_count) as total_failed
FROM batch_jobs
WHERE created_at >= CURRENT_DATE
GROUP BY job_type, status
ORDER BY job_type, status;

-- 4. 检查缓存性能指标
SELECT
    '系统性能指标' as metric,
    metric_type,
    metric_value,
    additional_data
FROM batch_performance_metrics
WHERE date = CURRENT_DATE
ORDER BY metric_type;
```

**预期结果**:
```
数据完整性报告 | 2025-09-20

股票数据覆盖率:
  603993 | ✓ | ✓ | ✓ | ✓
  000630 | ✓ | ✓ | ✓ | ✓
  300085 | ✓ | ✓ | ✓ | ✓
  601727 | ✓ | ✓ | ✓ | ✓

RAG版本状态:
  603993 | financial | active | 5 | 2025-09-20
  603993 | announcements | active | 3 | 2025-09-20
  000630 | financial | active | 4 | 2025-09-20
  ...

批处理任务状态:
  watchlist_warm | success | 1 | 45.6 | 3 | 0
  rag_sync | success | 1 | 12.5 | 6 | 0

系统性能指标:
  cache_hit_rate | 0.85 | {"description": "缓存命中率"}
  avg_response_time | 1.2 | {"description": "平均API响应时间(秒)"}
```

---

## 🚀 Part 4: 性能与压力测试

### 4.1 API性能测试

#### 测试用例 PERF-001: API响应时间基准测试
**目的**: 验证API性能指标符合要求

**测试步骤**:
```bash
# API性能测试脚本
echo "=== API性能基准测试 ==="

# 测试1: 冷启动性能（清空缓存）
echo "1. 冷启动测试 (601727)"
redis-cli FLUSHDB
time curl -s -X POST "http://localhost:8000/api/v1/stocks/dashboard" \
     -H "Content-Type: application/json" \
     -d '{"stock_code": "601727", "data_types": ["realtime", "kline", "basic_info"]}' \
     > /dev/null

# 测试2: 热缓存性能
echo "2. 热缓存测试 (601727)"
time curl -s -X POST "http://localhost:8000/api/v1/stocks/dashboard" \
     -H "Content-Type: application/json" \
     -d '{"stock_code": "601727", "data_types": ["realtime", "kline", "basic_info"]}' \
     > /dev/null

# 测试3: 批量并发测试
echo "3. 并发测试 (5个并发请求)"
for i in {1..5}; do
  (time curl -s -X POST "http://localhost:8000/api/v1/stocks/dashboard" \
       -H "Content-Type: application/json" \
       -d '{"stock_code": "60172'$i'", "data_types": ["realtime"]}' \
       > /dev/null) &
done
wait

echo "性能测试完成"
```

**预期结果**:
```
=== API性能基准测试 ===
1. 冷启动测试 (601727)
real    0m3.245s  # 预期: < 5秒
user    0m0.012s
sys     0m0.004s

2. 热缓存测试 (601727)
real    0m0.456s  # 预期: < 1秒
user    0m0.008s
sys     0m0.003s

3. 并发测试 (5个并发请求)
# 预期: 所有请求在10秒内完成
性能测试完成
```

### 4.2 批处理性能测试

#### 测试用例 PERF-002: 批处理吞吐量测试
**目的**: 验证批处理系统处理能力

**测试步骤**:
```python
# 批处理性能测试
python -c "
import asyncio
import time
from batch_processor.processors.watchlist_processor import WatchlistProcessor

async def performance_test():
    processor = WatchlistProcessor()

    # 创建多个测试自选股列表
    test_stocks_groups = [
        ['603993', '000630'],
        ['300085', '601727'],
        ['000001', '600519'],
        ['600036', '000002']
    ]

    print('=== 批处理性能测试 ===')

    start_time = time.time()

    # 并行处理多个股票组
    tasks = []
    for i, stocks in enumerate(test_stocks_groups):
        task = processor.process_stock_group(
            stock_codes=stocks,
            data_types=['financial', 'announcements'],
            group_id=f'perf_test_{i}'
        )
        tasks.append(task)

    # 等待所有任务完成
    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = time.time()
    total_time = end_time - start_time

    # 统计结果
    total_stocks = sum(len(group) for group in test_stocks_groups)
    total_data_types = 2
    total_operations = total_stocks * total_data_types

    print(f'处理完成: {total_stocks} 只股票, {total_operations} 个数据操作')
    print(f'总耗时: {total_time:.2f} 秒')
    print(f'吞吐量: {total_operations/total_time:.2f} 操作/秒')
    print(f'平均每股处理时间: {total_time/total_stocks:.2f} 秒')

    # 详细结果
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    print(f'成功率: {success_count}/{len(results)} = {success_count/len(results):.1%}')

# 注意: 这个函数需要在实际的processor中实现
# asyncio.run(performance_test())
print('性能测试框架已准备就绪')
"
```

**预期结果**:
```
=== 批处理性能测试 ===
处理完成: 8 只股票, 16 个数据操作
总耗时: 25.67 秒
吞吐量: 0.62 操作/秒
平均每股处理时间: 3.21 秒
成功率: 4/4 = 100%
```

---

## 📋 Part 5: 综合集成测试

### 5.1 端到端系统测试

#### 测试用例 E2E-001: 完整业务流程测试
**目的**: 验证从API调用到RAG集成的完整数据流

**测试场景**:
1. 用户通过API查询股票数据 →
2. 触发批处理预热 →
3. 数据同步到RAG →
4. 再次API查询验证缓存效果

**测试步骤**:
```bash
#!/bin/bash
echo "=== 端到端系统测试 ==="

# 步骤1: 清空环境
echo "1. 环境清理"
redis-cli FLUSHDB
psql -h localhost -d prism2 -U prism2 -c "DELETE FROM rag_data_versions WHERE stock_code IN ('603993', '000630', '300085');"

# 步骤2: API首次调用（冷启动）
echo "2. API冷启动调用"
curl -s -X POST "http://localhost:8000/api/v1/stocks/dashboard" \
     -H "Content-Type: application/json" \
     -d '{"stock_code": "603993", "data_types": ["financial", "announcements"]}' \
     -w "API响应时间: %{time_total}s\n" > api_response_1.json

# 步骤3: 执行批处理
echo "3. 执行批处理预热"
python -c "
import asyncio
from batch_processor.processors.watchlist_processor import WatchlistProcessor

async def run_batch():
    processor = WatchlistProcessor()
    result = await processor.process_stock_batch(['603993', '000630', '300085'])
    print(f'批处理结果: {result}')

asyncio.run(run_batch())
"

# 步骤4: 执行RAG同步
echo "4. 执行RAG同步"
python -c "
import asyncio
from batch_processor.processors.rag_sync_processor import RAGSyncProcessor

async def run_rag_sync():
    processor = RAGSyncProcessor()
    result = await processor.sync_batch_data_to_rag(
        stock_codes=['603993', '000630', '300085'],
        data_types=['financial', 'announcements']
    )
    print(f'RAG同步结果: {result}')

asyncio.run(run_rag_sync())
"

# 步骤5: API再次调用（热缓存）
echo "5. API热缓存调用"
curl -s -X POST "http://localhost:8000/api/v1/stocks/dashboard" \
     -H "Content-Type: application/json" \
     -d '{"stock_code": "603993", "data_types": ["financial", "announcements"]}' \
     -w "API响应时间: %{time_total}s\n" > api_response_2.json

# 步骤6: 结果验证
echo "6. 结果验证"
echo "   - API响应文件: api_response_1.json, api_response_2.json"
echo "   - 缓存命中率对比:"
jq '.cache_info' api_response_1.json
jq '.cache_info' api_response_2.json

echo "端到端测试完成"
```

**预期结果**:
```
=== 端到端系统测试 ===
1. 环境清理
OK

2. API冷启动调用
API响应时间: 3.245s

3. 执行批处理预热
批处理结果: {"processed_stocks": 3, "successful_stocks": 3, "failed_stocks": 0}

4. 执行RAG同步
RAG同步结果: {"successful_syncs": 6, "failed_syncs": 0}

5. API热缓存调用
API响应时间: 0.456s

6. 结果验证
   - 缓存命中率对比:
{
  "redis_hits": "0",
  "postgres_hits": "0",
  "akshare_calls": "2"
}
{
  "redis_hits": "2",
  "postgres_hits": "0",
  "akshare_calls": "0"
}

端到端测试完成
```

### 5.2 系统故障恢复测试

#### 测试用例 RECOVERY-001: 数据库连接故障恢复
**目的**: 验证系统在数据库故障时的恢复能力

**测试步骤**:
```python
# 故障恢复测试
python -c "
import time
import asyncio
from batch_processor.services.version_manager import VersionManager

async def test_recovery():
    vm = VersionManager()

    print('=== 故障恢复测试 ===')

    # 1. 正常操作
    try:
        version_id = await vm.create_new_version('603993', 'financial', {'test': 'data'})
        print(f'✓ 正常创建版本: {version_id}')
    except Exception as e:
        print(f'✗ 正常操作失败: {e}')

    # 2. 模拟数据库故障（通过修改连接参数）
    original_config = vm.db_config.copy()
    vm.db_config['host'] = 'invalid_host'

    try:
        version_id = await vm.create_new_version('603993', 'financial', {'test': 'data'})
        print(f'✗ 应该失败但成功了: {version_id}')
    except Exception as e:
        print(f'✓ 故障检测正常: {type(e).__name__}')

    # 3. 恢复配置
    vm.db_config = original_config
    time.sleep(1)

    try:
        version_id = await vm.create_new_version('603993', 'financial', {'test': 'recovery_data'})
        print(f'✓ 故障恢复成功: {version_id}')
    except Exception as e:
        print(f'✗ 恢复失败: {e}')

asyncio.run(test_recovery())
"
```

**预期结果**:
```
=== 故障恢复测试 ===
✓ 正常创建版本: 12345678-abcd-ef01-2345-678901234567
✓ 故障检测正常: OperationalError
✓ 故障恢复成功: 23456789-bcde-f012-3456-789012345678
```

---

## 📊 Part 6: 测试报告和验收标准

### 6.1 测试执行检查清单

| 测试分类 | 测试用例 | 执行状态 | 通过状态 | 备注 |
|---------|---------|---------|---------|------|
| **Online API** | API-001: 主要仪表板接口 | ⬜ | ⬜ | 601727股票数据 |
| | API-002: 缓存命中测试 | ⬜ | ⬜ | 三层架构验证 |
| | API-003: 根路径测试 | ⬜ | ⬜ | 基础健康检查 |
| **批处理系统** | BATCH-001: 自选股列表创建 | ⬜ | ⬜ | 603993,000630,300085 |
| | BATCH-002: 自选股批处理执行 | ⬜ | ⬜ | 高优先级处理 |
| | RAG-001: RAG批量同步 | ⬜ | ⬜ | 版本管理验证 |
| | RAG-002: 版本生命周期 | ⬜ | ⬜ | 非活性/活性切换 |
| **数据一致性** | DATA-001: 三层架构数据流 | ⬜ | ⬜ | Redis→PG→AKShare |
| | DATA-002: 数据完整性检查 | ⬜ | ⬜ | 质量标准验证 |
| **性能测试** | PERF-001: API响应时间 | ⬜ | ⬜ | <2秒标准 |
| | PERF-002: 批处理吞吐量 | ⬜ | ⬜ | 并发处理能力 |
| **集成测试** | E2E-001: 端到端流程 | ⬜ | ⬜ | 完整业务流程 |
| | RECOVERY-001: 故障恢复 | ⬜ | ⬜ | 系统健壮性 |

### 6.2 验收标准

#### 功能性标准
- ✅ 所有API endpoints正常响应
- ✅ 批处理jobs成功执行并生成预期结果
- ✅ RAG集成功能完整，版本管理正确
- ✅ 数据在三层架构中正确流转和存储

#### 性能标准
- ✅ API冷启动响应时间 < 5秒
- ✅ API热缓存响应时间 < 1秒
- ✅ 缓存命中率 > 80%
- ✅ 批处理平均每股处理时间 < 5秒

#### 可靠性标准
- ✅ 数据一致性 > 95%
- ✅ 批处理成功率 > 98%
- ✅ 系统故障后可自动恢复
- ✅ 无数据丢失或损坏

#### 数据质量标准
- ✅ 测试股票(601727, 603993, 000630, 300085)数据完整
- ✅ RAG版本管理功能正确（前一版本非活性，新版信息活性）
- ✅ 向量化数据质量合格（文本块数量、内容完整性）

### 6.3 测试环境配置

#### 环境要求
```yaml
测试环境:
  操作系统: Linux/WSL2
  Python版本: 3.12+
  数据库: PostgreSQL 15 + Redis 7
  依赖服务:
    - Redis (localhost:6379)
    - PostgreSQL (localhost:5432)
    - FastAPI服务 (localhost:8000)

配置文件:
  - batch_processor/config/batch_config.yaml
  - enhanced_dashboard_api.py数据库配置

测试数据:
  Online测试: 601727 (上海电气)
  批处理测试: 603993 (洛阳钼业), 000630 (铜陵有色), 300085 (银之杰)
```

#### 执行前准备
```bash
# 1. 启动必要服务
sudo systemctl start redis
sudo systemctl start postgresql

# 2. 激活Python环境
source test_venv/bin/activate

# 3. 启动API服务
python enhanced_dashboard_api.py &

# 4. 清理测试环境(可选)
redis-cli FLUSHDB
psql -h localhost -d prism2 -U prism2 -c "DELETE FROM batch_jobs WHERE created_at >= CURRENT_DATE;"
```

---

## 🎯 总结

这个全面测试计划涵盖了Prism2 Backend系统的所有核心功能：

1. **Online API系统**: 验证Dashboard API的完整性和性能
2. **批处理系统**: 测试自选股处理、RAG同步和版本管理
3. **数据一致性**: 确保三层架构数据流的正确性
4. **性能验证**: 满足响应时间和吞吐量要求
5. **集成测试**: 端到端业务流程和故障恢复能力

通过执行这个测试计划，可以全面验证Backend系统的功能完整性、性能指标和系统稳定性，确保系统达到生产环境的质量标准。

**下一步行动**: 按照测试用例逐项执行，记录测试结果，对于失败的测试用例进行问题分析和修复。