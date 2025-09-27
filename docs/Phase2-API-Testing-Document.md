# Phase 2 Backend API测试文档

## 📋 测试概览

**测试目标**: 验证Phase 2实现的所有Backend API功能
**测试环境**: Development Environment with Podman containers
**测试股票**: 002222 (福晶科技)
**测试时间**: 2025-09-19
**测试标准**: 真实数据测试，禁止使用Mock数据

## 🎯 API测试规范

### 测试分类
- **🔍 API验证 (Validation)**: 检查API端点是否可达，返回HTTP 200状态码
- **🧪 API测试 (Testing)**: 验证API功能完整性和数据准确性

### 接受标准
- ✅ **验证通过**: HTTP 200 + 任何响应内容
- ✅ **测试通过**: HTTP 200 + 有意义的业务数据 + 格式正确
- ❌ **测试失败**: 非200状态码 或 空数据 或 格式错误

## 📡 API端点清单

### 1. 健康检查API

#### 1.1 基础健康检查
- **URL**: `GET /api/v1/health`
- **目的**: 验证API服务整体健康状态
- **参数**: 无
- **期望响应**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-19T10:30:00Z",
  "version": "1.0.0"
}
```

#### 1.2 数据库健康检查
- **URL**: `GET /api/v1/health/db`
- **目的**: 验证PostgreSQL数据库连接状态
- **参数**: 无
- **期望响应**:
```json
{
  "status": "healthy",
  "database_version": "PostgreSQL 15.13 on...",
  "timestamp": "2025-09-19T10:30:00Z"
}
```

#### 1.3 Redis健康检查
- **URL**: `GET /api/v1/health/redis`
- **目的**: 验证Redis缓存服务连接状态
- **参数**: 无
- **期望响应**:
```json
{
  "status": "healthy",
  "redis_databases": {
    "stock_db": true,
    "search_db": true,
    "system_db": true
  },
  "timestamp": "2025-09-19T10:30:00Z"
}
```

### 2. 股票搜索API

#### 2.1 股票代码搜索
- **URL**: `GET /api/v1/stocks/search`
- **目的**: 通过股票代码搜索股票
- **参数**:
  - `query`: "002222" (必填)
  - `limit`: 10 (可选，默认10)
- **完整URL**: `/api/v1/stocks/search?query=002222&limit=10`
- **期望响应**:
```json
{
  "success": true,
  "query": "002222",
  "results": [
    {
      "code": "002222",
      "name": "福晶科技",
      "market": "SZ",
      "industry": "电子"
    }
  ],
  "total": 1
}
```

#### 2.2 股票名称搜索
- **URL**: `GET /api/v1/stocks/search`
- **目的**: 通过股票名称搜索股票
- **参数**:
  - `query`: "福晶" (必填)
  - `limit`: 5 (可选)
- **完整URL**: `/api/v1/stocks/search?query=福晶&limit=5`

### 3. 股票基础信息API

#### 3.1 获取股票基础信息
- **URL**: `GET /api/v1/stocks/{stock_code}/info`
- **目的**: 获取指定股票的基础信息
- **参数**:
  - `stock_code`: "002222" (路径参数)
- **完整URL**: `/api/v1/stocks/002222/info`
- **期望响应**:
```json
{
  "code": "002222",
  "name": "福晶科技",
  "market": "SZ",
  "industry": "电子",
  "market_cap": 5000000000,
  "pe_ratio": 25.5,
  "pb_ratio": 2.1
}
```

### 4. 实时价格API

#### 4.1 获取实时价格数据
- **URL**: `GET /api/v1/stocks/{stock_code}/realtime`
- **目的**: 获取指定股票的实时价格数据
- **参数**:
  - `stock_code`: "002222" (路径参数)
- **完整URL**: `/api/v1/stocks/002222/realtime`
- **期望响应**:
```json
{
  "current_price": 12.45,
  "change_amount": 0.15,
  "change_percent": 1.22,
  "volume": 1500000,
  "turnover": 18500000.0,
  "high": 12.50,
  "low": 12.20,
  "open": 12.30,
  "timestamp": "2025-09-19T10:30:00Z"
}
```

### 5. K线数据API

#### 5.1 获取日K线数据
- **URL**: `GET /api/v1/stocks/{stock_code}/kline`
- **目的**: 获取指定股票的K线数据
- **参数**:
  - `stock_code`: "002222" (路径参数)
  - `period`: "daily" (可选，默认daily)
- **完整URL**: `/api/v1/stocks/002222/kline?period=daily`
- **期望响应**:
```json
{
  "period": "daily",
  "data": [
    {
      "timestamp": "2025-09-18",
      "open": 12.30,
      "high": 12.50,
      "low": 12.20,
      "close": 12.45,
      "volume": 1500000
    },
    // ... 更多K线数据
  ]
}
```

### 6. Dashboard综合数据API

#### 6.1 获取基础数据组合
- **URL**: `POST /api/v1/stocks/dashboard`
- **目的**: 获取Dashboard页面所需的综合数据
- **请求体**:
```json
{
  "stock_code": "002222",
  "data_types": ["basic_info", "realtime"]
}
```
- **期望响应**:
```json
{
  "success": true,
  "stock_code": "002222",
  "timestamp": "2025-09-19T10:30:00Z",
  "data": {
    "basic_info": {
      "code": "002222",
      "name": "福晶科技",
      "market": "SZ",
      "industry": "电子",
      "market_cap": 5000000000
    },
    "realtime": {
      "current_price": 12.45,
      "change_percent": 1.22,
      "volume": 1500000
    }
  }
}
```

#### 6.2 获取完整数据组合
- **URL**: `POST /api/v1/stocks/dashboard`
- **请求体**:
```json
{
  "stock_code": "002222",
  "data_types": ["basic_info", "realtime", "kline", "financial", "news", "announcements", "longhubang", "ai_analysis"]
}
```

## ⚙️ 测试环境准备

### 前置条件检查
1. **基础设施状态**:
   - [ ] PostgreSQL容器运行正常
   - [ ] Redis容器运行正常
   - [ ] ChromaDB容器运行正常
   - [ ] AKShare数据源可访问

2. **代理配置**:
   - [ ] no_proxy环境变量正确设置
   - [ ] localhost访问不经过代理

3. **应用状态**:
   - [ ] FastAPI应用可以启动
   - [ ] 端口8080可用（避免与ChromaDB的8000冲突）

## 🧪 测试执行步骤

### 步骤1: 启动测试环境
```bash
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
export no_proxy="localhost,127.0.0.1,::1,0.0.0.0"
export NO_PROXY="localhost,127.0.0.1,::1,0.0.0.0"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### 步骤2: 基础验证测试
```bash
# 检查应用启动
curl http://localhost:8080/

# 检查API文档
curl http://localhost:8080/docs
```

### 步骤3: 健康检查测试
```bash
# 基础健康检查
curl -X GET "http://localhost:8080/api/v1/health"

# 数据库健康检查
curl -X GET "http://localhost:8080/api/v1/health/db"

# Redis健康检查
curl -X GET "http://localhost:8080/api/v1/health/redis"
```

### 步骤4: 股票API功能测试
```bash
# 股票搜索测试
curl -X GET "http://localhost:8080/api/v1/stocks/search?query=002222&limit=10"

# 股票信息测试
curl -X GET "http://localhost:8080/api/v1/stocks/002222/info"

# 实时价格测试
curl -X GET "http://localhost:8080/api/v1/stocks/002222/realtime"

# K线数据测试
curl -X GET "http://localhost:8080/api/v1/stocks/002222/kline?period=daily"
```

### 步骤5: Dashboard API测试
```bash
# 基础Dashboard数据
curl -X POST "http://localhost:8080/api/v1/stocks/dashboard" \
     -H "Content-Type: application/json" \
     -d '{
       "stock_code": "002222",
       "data_types": ["basic_info", "realtime"]
     }'

# 完整Dashboard数据
curl -X POST "http://localhost:8080/api/v1/stocks/dashboard" \
     -H "Content-Type: application/json" \
     -d '{
       "stock_code": "002222",
       "data_types": ["basic_info", "realtime", "kline"]
     }'
```

## 📊 测试结果模板

### 测试结果记录格式
```markdown
## 测试结果 - [API名称]
**测试时间**: YYYY-MM-DD HH:MM:SS
**请求URL**: [完整URL]
**HTTP状态码**: [200/404/500等]
**响应时间**: [毫秒]
**测试结果**: ✅通过 / ❌失败

### 响应内容
```json
[实际返回的JSON数据]
```

### 数据验证
- [ ] 响应格式正确
- [ ] 必填字段存在
- [ ] 数据类型正确
- [ ] 业务逻辑合理

### 问题记录
[如有问题，记录具体错误信息和解决方案]
```

## 🎯 测试成功标准

### API验证标准
- ✅ 所有健康检查API返回200状态码
- ✅ 所有业务API返回200状态码
- ✅ 响应时间 < 5秒（考虑AKShare API延迟）

### 数据质量标准
- ✅ 股票002222的真实数据能正确获取
- ✅ 数据格式符合Schema定义
- ✅ 三级查询架构正常工作（Redis缓存生效）

### 性能标准
- ✅ 首次查询: 直接从AKShare获取，耗时2-5秒
- ✅ 缓存查询: 从Redis获取，耗时 < 100ms
- ✅ 并发处理: 支持至少5个并发请求

---

**📅 文档创建时间**: 2025-09-19
**📋 测试负责人**: Claude Code AI
**🎯 测试目标**: 验证Phase 2所有API功能的完整性和数据准确性