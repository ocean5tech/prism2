# Prism2 股票分析平台 - 统一启动指南

## 🚀 快速开始

### 一键启动系统
```bash
cd /home/wyatt/prism2
./start_prism2_system.sh
```

### 一键验证系统
```bash
cd /home/wyatt/prism2
python3 verify_prism2_system.py
```

### 停止所有服务
```bash
./start_prism2_system.sh stop
```

### 查看服务状态
```bash
./start_prism2_system.sh status
```

## 📋 系统架构概览

### 服务分层架构
```
┌─────────────────────────────────────────┐
│          Claude集成层 (9000)            │
├─────────────────────────────────────────┤
│               4MCP服务层                 │
│  实时数据(8006) | 结构化数据(8007)       │
│  RAG增强(8008)  | 任务协调(8009)         │
├─────────────────────────────────────────┤
│           传统MCP层 (8005)              │
├─────────────────────────────────────────┤
│          后台服务层 (8081)              │
├─────────────────────────────────────────┤
│     基础设施层 (Redis, PostgreSQL)      │
└─────────────────────────────────────────┘
```

### 端口分配表
| 端口 | 服务名称 | 功能描述 | 状态 |
|------|----------|----------|------|
| 6379 | Redis | 缓存服务 | 基础设施 |
| 5432 | PostgreSQL | 主数据库 | 基础设施 |
| 8081 | Enhanced Dashboard API | 股票数据API | 后台服务 |
| 8005 | MCPO Agent | 传统MCP代理 | 兼容层 |
| 8006 | 实时数据MCP | 实时数据获取 | 4MCP架构 |
| 8007 | 结构化数据MCP | 历史数据分析 | 4MCP架构 |
| 8008 | RAG增强MCP | 向量搜索增强 | 4MCP架构 |
| 8009 | 任务协调MCP | 工作流编排 | 4MCP架构 |
| 9000 | Claude API集成 | 统一API接口 | 集成层 |

## 🔧 启动脚本详解

### start_prism2_system.sh 功能
- **智能检测**: 自动检测已运行的服务，避免重复启动
- **依赖检查**: 验证Redis、PostgreSQL等基础服务
- **按序启动**: 按照依赖关系顺序启动各层服务
- **健康验证**: 启动后自动进行健康检查和功能验证
- **日志管理**: 所有服务日志统一存放在 `/home/wyatt/prism2/logs/`
- **错误处理**: 启动失败时提供详细错误信息和解决建议

### 启动顺序
1. **基础设施检查**: Redis (6379), PostgreSQL (5432)
2. **后台服务启动**: Enhanced Dashboard API (8081)
3. **RAG服务检查**: ChromaDB相关服务
4. **传统MCP启动**: MCPO Agent (8005) [兼容性]
5. **4MCP服务启动**: 实时数据→结构化数据→RAG增强→任务协调
6. **Claude集成启动**: Claude API集成层 (9000)
7. **系统验证**: 端到端功能验证

## 🧪 验证脚本详解

### verify_prism2_system.py 功能
- **多层验证**: 从基础设施到业务功能的全栈验证
- **实际测试**: 使用真实股票代码(688469)进行功能测试
- **健康检查**: 对所有API端点进行健康状态检查
- **性能监控**: 测量API响应时间和数据获取效率
- **详细报告**: 生成彩色控制台报告，清晰展示系统状态

### 验证项目
1. **基础设施验证**:
   - Redis连接和读写测试
   - PostgreSQL连接和表统计

2. **后台服务验证**:
   - Enhanced Dashboard API健康检查
   - 股票数据获取功能测试

3. **传统MCP验证**:
   - MCPO Agent OpenAPI规范获取
   - 工具函数发现和调用

4. **4MCP服务验证**:
   - 四个MCP服务的健康检查
   - 服务间通信测试

5. **Claude集成验证**:
   - 基础API功能测试
   - 股票分析接口测试
   - 聊天接口功能测试

6. **功能集成验证**:
   - 端到端数据流测试
   - 服务编排功能测试

## 📁 日志管理

### 日志位置
```
/home/wyatt/prism2/logs/
├── enhanced_dashboard.log    # Enhanced Dashboard API日志
├── enhanced_dashboard.pid    # 进程ID文件
├── mcpo.log                  # MCPO代理日志
├── mcpo.pid                  # 进程ID文件
├── claude_integration.log   # Claude集成层日志
├── claude_integration.pid   # 进程ID文件
└── 4mcp/                    # 4MCP服务日志目录
    ├── realtime_data.log
    ├── realtime_data.pid
    ├── structured_data.log
    ├── structured_data.pid
    ├── rag_enhanced.log
    ├── rag_enhanced.pid
    ├── coordination.log
    └── coordination.pid
```

### 日志查看命令
```bash
# 查看Claude集成层日志
tail -f /home/wyatt/prism2/logs/claude_integration.log

# 查看4MCP协调服务日志
tail -f /home/wyatt/prism2/logs/4mcp/coordination.log

# 查看所有服务状态
ps aux | grep -E "(python|mcpo)" | grep -v grep
```

## 🌐 API访问地址

### 主要接口
- **Claude API统一接口**: http://localhost:9000
  - 健康检查: `GET /health`
  - 股票分析: `POST /api/v1/analysis`
  - 智能对话: `POST /api/v1/chat`
  - 服务状态: `GET /api/v1/services`

- **传统MCP接口**: http://localhost:8005
  - OpenAPI规范: `/prism2-stock-analysis/openapi.json`

- **股票数据API**: http://localhost:8081
  - 健康检查: `/health`
  - 实时数据: `/api/stock/realtime?symbol=688469`

### 4MCP服务接口
- **实时数据MCP**: http://localhost:8006/health
- **结构化数据MCP**: http://localhost:8007/health
- **RAG增强MCP**: http://localhost:8008/health
- **任务协调MCP**: http://localhost:8009/health

## 🧪 测试命令示例

### 基础功能测试
```bash
# Claude API集成 - 基础信息
curl http://localhost:9000

# Claude API集成 - 健康检查
curl http://localhost:9000/health

# Claude API集成 - 股票分析
curl 'http://localhost:9000/api/v1/analysis' \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"stock_code":"688469","analysis_type":"standard","include_claude_insights":true}'

# Claude API集成 - 聊天接口
curl 'http://localhost:9000/api/v1/chat' \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"message":"请分析688469这只股票的投资价值","include_mcp_data":true}'
```

### 服务状态检查
```bash
# 检查所有服务端口
netstat -tuln | grep -E "(6379|5432|8005|8006|8007|8008|8009|8081|9000)"

# 检查服务进程
ps aux | grep -E "(redis|postgres|python|mcpo)" | grep -v grep
```

## ⚠️ 常见问题和解决方案

### 1. 端口被占用
```bash
# 查找占用端口的进程
lsof -i :9000

# 杀死占用进程
kill -9 <PID>
```

### 2. 基础服务未启动
```bash
# 启动Redis
sudo systemctl start redis
sudo systemctl enable redis

# 启动PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3. 权限问题
```bash
# 确保脚本有执行权限
chmod +x /home/wyatt/prism2/start_prism2_system.sh
chmod +x /home/wyatt/prism2/verify_prism2_system.py

# 确保日志目录可写
mkdir -p /home/wyatt/prism2/logs
chmod 755 /home/wyatt/prism2/logs
```

### 4. 虚拟环境问题
```bash
# 重新创建虚拟环境（如果需要）
cd /home/wyatt/prism2/mcp_servers
python3 -m venv mcp4_venv
source mcp4_venv/bin/activate
pip install -r requirements.txt
```

### 5. 数据库连接问题
```bash
# 测试PostgreSQL连接
psql -h localhost -U postgres -d stock_data -c "SELECT version();"

# 测试Redis连接
redis-cli ping
```

## 🔄 系统重启后操作

服务器重启后，按以下步骤恢复服务：

1. **检查基础服务**:
   ```bash
   sudo systemctl status redis postgresql
   ```

2. **启动Prism2系统**:
   ```bash
   cd /home/wyatt/prism2
   ./start_prism2_system.sh
   ```

3. **验证系统状态**:
   ```bash
   python3 verify_prism2_system.py
   ```

4. **查看服务状态**:
   ```bash
   ./start_prism2_system.sh status
   ```

## 📊 监控和维护

### 系统监控
- 日志文件会自动轮转，但建议定期清理旧日志
- 监控各服务的内存和CPU使用情况
- 定期运行验证脚本确保系统健康

### 定期维护
```bash
# 每日系统验证（建议加入cron任务）
0 9 * * * cd /home/wyatt/prism2 && python3 verify_prism2_system.py >> logs/daily_check.log 2>&1

# 每周日志清理
0 0 * * 0 find /home/wyatt/prism2/logs -name "*.log" -mtime +7 -delete
```

---

## 📞 技术支持

如果遇到问题，请：
1. 首先查看相关日志文件
2. 运行系统验证脚本诊断问题
3. 检查系统资源使用情况
4. 确认网络连接和防火墙设置

**Happy Coding! 🚀**