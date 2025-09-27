# 📋 Phase5 4MCP架构文档索引

## 📚 文档结构

```
/home/wyatt/prism2/docs/phase5-4mcp/
├── README.md                           ← 本文档 (文档索引)
├── PHASE5_4MCP_ARCHITECTURE_DESIGN.md  ← 总体架构设计
├── development-progress.md             ← 开发进度追踪
├── api-specifications/                 ← API规范文档
├── deployment-guides/                  ← 部署指南
└── testing-reports/                    ← 测试报告
```

## 🎯 核心文档说明

### 1. 架构设计文档
**文件**: `PHASE5_4MCP_ARCHITECTURE_DESIGN.md`
**内容**:
- 系统整体架构设计
- 4MCP服务器详细功能规划
- 开发计划和时间安排
- 技术栈选择和集成策略

### 2. 开发进度文档
**文件**: `development-progress.md`
**内容**:
- 实时开发进度追踪
- 各阶段完成状态
- 当前任务和下一步计划
- 风险识别和问题解决

## 🏗️ 4MCP架构概览

### 系统组件
```
Claude API集成层 (端口9000)
        ↓
┌─────────────────────────────────────────┐
│            4MCP服务器集群                  │
├─────────────────────────────────────────┤
│ 实时数据MCP         │ 结构化数据MCP            │
│ (端口8006) ✅       │ (端口8007) ⏳           │
├─────────────────────────────────────────┤
│ RAG增强MCP         │ 任务协调MCP              │
│ (端口8008) ⏳       │ (端口8009) ⏳           │
└─────────────────────────────────────────┘
        ↓
现有基础服务 (Enhanced Dashboard API + RAG Service)
```

### 设计原则
- **API数据为主，RAG为辅** - 确保数据权威性
- **智能数据展示** - Claude分析JSON，返回用户友好格式
- **服务解耦** - 每个MCP专注特定领域
- **容错设计** - 单点故障不影响整体系统

## 📊 开发状态

| Phase | 服务 | 端口 | 状态 | 完成度 |
|-------|------|------|------|--------|
| 1 | 基础设施 | - | ✅ 完成 | 100% |
| 2a | 实时数据MCP | 8006 | ✅ 完成 | 100% |
| 2b | 结构化数据MCP | 8007 | ⏳ 开发中 | 0% |
| 3 | RAG增强MCP | 8008 | ⏳ 待开始 | 0% |
| 4 | 任务协调MCP | 8009 | ⏳ 待开始 | 0% |
| 5 | Claude集成层 | 9000 | ⏳ 待开始 | 0% |
| 6 | 前端集成测试 | - | ⏳ 待开始 | 0% |

**总体进度**: 20% 完成

## 🚀 快速启动指南

### 开发环境启动
```bash
# 1. 启动现有基础服务
cd /home/wyatt/prism2
source test_venv/bin/activate
python enhanced_dashboard_api.py &  # 端口8081
python -m rag_service.main &        # 端口8003

# 2. 启动4MCP服务器集群
cd mcp_servers && source mcp4_venv/bin/activate
python realtime_data_mcp/server.py &      # 端口8006 ✅
python structured_data_mcp/server.py &    # 端口8007 ⏳
python rag_mcp/server.py &               # 端口8008 ⏳
python coordination_mcp/server.py &       # 端口8009 ⏳

# 3. 启动Claude API集成层
python claude_integration/server.py &     # 端口9000 ⏳
```

### 测试验证
```bash
# 测试实时数据MCP
curl http://localhost:8006/health

# 测试具体股票查询功能 (开发完成后)
# MCP工具调用测试脚本位于 mcp_servers/tests/
```

## 🔧 开发工具和依赖

### 核心技术栈
- **Python 3.12** - 主要开发语言
- **MCP SDK 1.14.1** - Model Context Protocol
- **Anthropic SDK** - Claude API集成
- **AKShare** - 股票数据获取
- **FastAPI + Uvicorn** - Web服务框架
- **Redis + PostgreSQL** - 数据存储
- **ChromaDB** - 向量数据库

### 开发环境配置
```bash
# 创建虚拟环境
cd /home/wyatt/prism2/mcp_servers
python3 -m venv mcp4_venv
source mcp4_venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 📝 贡献指南

### 开发流程
1. **查看开发进度** - 阅读 `development-progress.md`
2. **选择任务** - 根据待开发清单选择任务
3. **更新文档** - 开发前后更新相关文档
4. **代码提交** - 提交时包含测试和文档更新

### 代码规范
- 遵循Python PEP8标准
- 使用类型提示 (Type Hints)
- 完善的错误处理和日志记录
- 单元测试覆盖率 > 90%

## 📞 联系方式

**项目负责人**: Claude Code
**文档维护**: 自动更新 (每日开发结束后)
**问题反馈**: 通过开发进度文档跟踪

---

**最后更新**: 2025-09-25 15:40
**文档版本**: v1.0