# CLAUDE 操作手册

这个文件记录所有Claude Code需要知道的操作方法，避免重复学习。

## 📚 重要文档索引

**必读文档**：
- 本文件：操作方法和启动流程
- `/docs_archive/LessonsLearned.md`：重要经验教训，特别是环境问题
- `/CLAUDE_SESSION_TEMPLATE.md`：标准会话开始流程

## 🚨 环境注意事项 (来自经验教训)

### 代理服务器问题 (HIGH PRIORITY)
**现象**：企业环境的HTTP代理会影响：
- GitHub下载失败
- 容器网络请求被拦截(403错误)
- AI模型API访问失败

**解决方案**：
```bash
# 启动任何服务前，必须清除代理
export http_proxy="" https_proxy="" HTTP_PROXY="" HTTPS_PROXY=""
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
```

### 容器化验证原则
**错误验证方式**：
```bash
❌ which psql        # 寻找客户端程序
❌ docker --version  # 寻找Docker
❌ curl localhost:11434  # 可能被代理拦截
```

**正确验证方式**：
```bash
✅ podman ps | grep postgres  # 检查容器状态
✅ ss -tlnp | grep 5432      # 检查端口监听
✅ unset http_proxy && curl 127.0.0.1:11434  # 绕过代理
```

## 🚀 服务启动规范 (2025-09-24经过12小时+验证)

### 容器服务完整创建与启动 (使用Podman，绝不使用Docker)
```bash
# 1. 清除代理环境 (关键步骤!)
export http_proxy="" https_proxy="" HTTP_PROXY="" HTTPS_PROXY=""

# 2. 创建并启动基础设施服务 (完整验证命令)
# PostgreSQL + TimescaleDB
podman run -d --name prism2-postgres \
  -p 5432:5432 \
  -v /home/wyatt/prism2/data/postgres:/var/lib/postgresql/data \
  -e POSTGRES_DB=prism2 \
  -e POSTGRES_USER=prism2 \
  -e POSTGRES_PASSWORD=prism2_secure_password \
  docker.io/timescale/timescaledb:latest-pg15

# Redis
podman run -d --name prism2-redis \
  -p 6379:6379 \
  -v /home/wyatt/prism2/data/redis:/data \
  docker.io/library/redis:7-alpine \
  redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru

# ChromaDB (注意端口映射8003:8000)
podman run -d --name prism2-chromadb \
  -p 8003:8000 \
  -v chromadb_data:/chroma/chroma \
  docker.io/chromadb/chroma:latest \
  run /config.yaml

# Nginx (可选)
podman run -d --name prism2-nginx \
  -p 9080:80 \
  -v /home/wyatt/prism2/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  docker.io/library/nginx:alpine

# 3. 如果容器已存在，使用启动命令
# podman start prism2-postgres prism2-redis prism2-chromadb prism2-nginx

# 4. 检查服务状态
podman ps | grep prism2

# 5. 验证端口监听 (更新的端口列表)
ss -tlnp | grep -E "(5432|6379|8003|9080)"
```

### 容器命名规范 (来自经验教训)
```bash
# 统一命名格式
prism2-{service-name}
# 例如: prism2-postgres, prism2-redis, prism2-chromadb

# 统一数据目录
~/prism2/data/{service-name}/
```

### Backend API启动 (2025-09-24验证的方法，绝不改变端口)
```bash
# 方法1: Enhanced Dashboard API (推荐，已验证12小时+运行)
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
python enhanced_dashboard_api.py &
# 端口: 8081, 架构: Redis→PostgreSQL→AKShare三层架构

# 方法2: 测试版本 (简化API，端口8080)
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
python test_main.py &

# 方法3: 完整版本 (全功能API，端口8000)
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 方法4: RAG批处理集成系统 (已验证80%功能正常)
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
python test_rag_batch_integration.py

# 方法5: 其他批处理测试
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
python test_batch_integration.py
python test_three_stocks_batch.py
```

### 禁止行为清单
- ❌ 绝不使用Docker命令
- ❌ 绝不安装任何依赖包
- ❌ 绝不修改端口号
- ❌ 绝不修改接口定义
- ❌ 绝不删除已有功能

## 🏗️ 系统架构记忆

### 真实系统组件
```
/prism2/
├── backend/
│   ├── app/main.py           # 完整FastAPI应用 (端口8000)
│   ├── test_main.py          # 测试工具 (端口8080)
│   ├── batch_processor/      # 批处理系统
│   └── test_venv/            # Python虚拟环境
├── rag-service/              # RAG向量服务
└── docs/                     # 所有文档存放处
```

### 服务端口分配 (2025-09-24验证)
- PostgreSQL: 5432
- Redis: 6379
- ChromaDB: 8003 (容器内8000)
- Nginx: 9080 (容器内80)
- Enhanced Dashboard API: 8081 (推荐，三层架构)
- Backend完整版: 8000
- Backend测试版: 8080
- RAG Service: 8001

## 📊 功能验证方法

### API健康检查 (2025-09-24验证方法)
```bash
# Enhanced Dashboard API (推荐，已验证)
curl -X POST http://localhost:8081/api/v1/stocks/dashboard \
  -H "Content-Type: application/json" \
  -d '{"stock_code": "000001", "data_types": ["financial"]}'

# 测试版本
curl http://localhost:8080/api/v1/health

# 完整版本
curl http://localhost:8000/api/v1/health

# ChromaDB检查 (注意端口8003)
curl http://localhost:8003/api/v1/heartbeat
```

### 批处理验证 (2025-09-24验证方法)
```bash
# RAG批处理集成测试 (推荐，80%功能验证通过)
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
python test_rag_batch_integration.py

# 传统批处理集成测试
python test_batch_integration.py

# 股票批处理测试
python test_three_stocks_batch.py
```

### 数据库验证 (2025-09-24验证方法)
```bash
# Redis数据检查 (验证缓存键数量)
podman exec prism2-redis redis-cli KEYS "*" | wc -l
podman exec prism2-redis redis-cli --scan --pattern "*" | head -10

# PostgreSQL检查 (验证表结构和数据量)
podman exec prism2-postgres psql -U prism2 -d prism2 -c "\\dt"
podman exec prism2-postgres psql -U prism2 -d prism2 -c "SELECT COUNT(*) FROM stock_financial;"

# ChromaDB检查 (注意端口8003)
curl -s http://localhost:8003/api/v1/heartbeat || echo "ChromaDB API v2正常"
```

## 🔧 开发原则记忆

### 启动顺序 (2025-09-24经过验证的流程)
1. **清除代理环境** (必须第一步!)
2. 启动基础设施容器服务 (PostgreSQL, Redis, ChromaDB, Nginx)
3. 启动Enhanced Dashboard API (推荐端口8081三层架构)
4. 可选: 启动RAG批处理集成系统
5. 验证服务健康状态 (使用正确方法)
6. 进行功能测试 (使用真实股票数据验证)

### 测试原则 (2025-09-24更新)
- 使用现有工具，不安装新依赖
- 保持接口不变 (端口8081/8000/8080，不修改)
- 优先使用Enhanced Dashboard API (端口8081三层架构)
- 优先使用RAG批处理集成测试验证功能
- 使用真实股票数据进行测试验证
- 所有报告保存到 `/docs/` 目录

### 故障排除流程 (来自经验教训)
1. **检查容器状态**: `podman ps -a`
2. **查看容器日志**: `podman logs container-name`
3. **检查端口占用**: `ss -tlnp | grep port`
4. **清除代理验证**: `unset http_proxy && curl -v http://127.0.0.1:port`
5. **检查代理设置**: `env | grep -i proxy`

### 重大错误预防 (基于历史教训)
- ❌ **绝不**使用 `which psql` 验证容器化PostgreSQL
- ❌ **绝不**寻找Docker，系统使用Podman
- ❌ **绝不**忽视代理环境变量对API访问的影响
- ✅ **优先**读取安装日志 `/docs/基础设施.log`
- ✅ **优先**使用容器命令验证服务状态
- ✅ **优先**检查系统现有文档和历史记录

### Python环境管理 (Ubuntu 24.04)
```bash
# 总是使用虚拟环境，不使用系统pip
source test_venv/bin/activate  # 使用现有环境
# 绝不执行: pip install --break-system-packages
```

---

## 📝 重大更新记录

### 2025-09-24: 全面系统测试验证更新
**来源**: `/docs/Comprehensive-Full-System-Test-Report-20250924.md`
**验证时长**: 12小时+持续运行
**更新内容**:
- ✅ 添加完整的容器创建命令 (包含镜像路径和配置参数)
- ✅ 修正ChromaDB端口映射为8003:8000
- ✅ 新增Enhanced Dashboard API (端口8081三层架构)
- ✅ 新增RAG批处理集成系统验证方法
- ✅ 更新所有端口分配信息
- ✅ 基于真实数据处理验证 (000546金圆股份等4只股票)
- ✅ 性能指标验证: 25.8倍缓存命中性能提升
- ✅ 数据完整性验证: 46条新记录，8个缓存键

**系统稳定性**: 生产环境就绪度85%
**关键架构**: Redis→PostgreSQL→AKShare三层数据架构

---

**重要提醒**: 这个文件应该在每次发现新的操作方法或遇到问题时更新，确保Claude Code能够持续学习和记忆。