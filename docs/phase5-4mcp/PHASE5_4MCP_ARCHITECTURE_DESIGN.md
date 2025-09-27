# 🏗️ Prism2 Phase5: 4MCP架构设计与开发计划

## 📊 项目概览

**项目名称**: Prism2 Phase5 - Claude API + 4MCP服务器架构
**开发周期**: 预计15-20天
**核心目标**: 实现基于Claude API的智能股票分析平台，通过4个专门的MCP服务器提供全面的金融数据支持

## 🎯 核心架构设计

### 系统架构图
```
用户界面 (React前端)
        ↓
Claude API集成层 (端口: 9000)
        ↓
┌─────────────────────────────────────────┐
│            4MCP服务器集群                  │
├─────────────────────────────────────────┤
│ 实时数据MCP     │ 结构化数据MCP            │
│ (端口: 8006)    │ (端口: 8007)            │
│ ├─ AKShare直连   │ ├─ Redis缓存             │
│ ├─ 实时价格      │ ├─ PostgreSQL存储        │
│ └─ 技术指标      │ └─ 历史财务数据           │
├─────────────────────────────────────────┤
│ RAG增强MCP     │ 任务协调MCP              │
│ (端口: 8008)    │ (端口: 8009)            │
│ ├─ ChromaDB     │ ├─ 多MCP任务调度         │
│ ├─ 新闻背景     │ ├─ 数据源优先级管理        │
│ └─ 行业分析     │ └─ 响应聚合与优化         │
└─────────────────────────────────────────┘
        ↓
现有Enhanced Dashboard API (端口: 8081)
现有RAG Service (端口: 8003)
```

### 设计原则
- **API数据为主，RAG为辅**: 优先使用权威的实时数据源
- **智能数据展示**: Claude分析复杂JSON，提供精炼的投资洞察
- **服务解耦**: 每个MCP服务器专注特定功能领域
- **容错设计**: 单个MCP服务器故障不影响整体系统运行

## 📋 详细开发计划

### Phase 1: 基础设施准备 (2天)
**目标**: 清理现有代码，准备4MCP开发环境

#### Task 1.1: 清理现有MCP代码
- **文件清理**:
  - 删除: `/home/wyatt/prism2/prism2_mcp_server.py`
  - 删除: `/home/wyatt/prism2/mcpo_config.json`
  - 删除: `/home/wyatt/prism2/test_mcp_integration.py`
  - 删除: `/home/wyatt/prism2/verify_mcp_complete.py`
  - 删除: `/home/wyatt/prism2/openwebui_config_guide.md`
- **保留项目**: Ollama + Qwen (作为Open WebUI测试功能)
- **状态**: 🔄 进行中

#### Task 1.2: 创建4MCP项目结构
- **目录结构**:
  ```
  /home/wyatt/prism2/mcp_servers/
  ├── realtime_data_mcp/     (端口8006)
  ├── structured_data_mcp/   (端口8007)
  ├── rag_mcp/              (端口8008)
  ├── coordination_mcp/      (端口8009)
  ├── claude_integration/    (端口9000)
  └── shared/               (共享工具库)
  ```
- **环境准备**: Python虚拟环境，依赖包安装
- **状态**: ⏳ 待开始

#### Task 1.3: 基础MCP框架搭建
- **技术栈**: Python + MCP SDK + FastAPI
- **通用工具**: 日志系统、配置管理、错误处理
- **测试框架**: pytest + 单元测试基础设施
- **状态**: ⏳ 待开始

### Phase 2: 核心数据MCP开发 (4天)

#### Task 2.1: 实时数据MCP (端口8006)
**职责**: 直连AKShare获取最新股价和技术指标
- **功能实现**:
  - `get_realtime_price`: 实时股价查询
  - `get_technical_indicators`: 技术分析指标
  - `get_market_snapshot`: 市场全景快照
  - `get_sector_performance`: 板块表现
- **性能要求**: 响应时间 < 2秒，支持并发查询
- **错误处理**: AKShare限流和网络异常处理
- **状态**: ⏳ 待开始

#### Task 2.2: 结构化数据MCP (端口8007)
**职责**: 通过Redis和PostgreSQL获取历史和财务数据
- **功能实现**:
  - `get_historical_data`: 历史价格数据
  - `get_financial_reports`: 财务报表数据
  - `get_company_profile`: 公司基础信息
  - `get_dividend_history`: 分红历史
- **集成方式**:
  - 优先从Redis缓存获取
  - 缓存未命中时查询PostgreSQL
  - PostgreSQL无数据时调用Enhanced Dashboard API
- **缓存策略**: 财务数据24小时缓存，价格数据5分钟缓存
- **状态**: ⏳ 待开始

#### Task 2.3: 数据MCP集成测试
- **测试用例**: 600519(茅台), 000001(平安), 688469(科创板)
- **性能验证**: 并发测试，响应时间测试
- **数据一致性**: 对比Enhanced Dashboard API结果
- **状态**: ⏳ 待开始

### Phase 3: RAG增强MCP开发 (3天)

#### Task 3.1: RAG-MCP (端口8008)
**职责**: 基于ChromaDB提供背景信息增强
- **功能实现**:
  - `get_news_context`: 相关新闻背景
  - `get_industry_analysis`: 行业分析报告
  - `get_peer_comparison`: 同行业对比
  - `get_risk_factors`: 风险因素分析
- **集成方式**:
  - 直连现有ChromaDB (端口8003)
  - 向量检索优化
  - 结果相关性排序
- **状态**: ⏳ 待开始

#### Task 3.2: RAG数据质量优化
- **内容筛选**: 过滤低质量信息
- **时效性验证**: 确保信息新鲜度
- **准确性检查**: 交叉验证机制
- **状态**: ⏳ 待开始

### Phase 4: 任务协调MCP开发 (4天)

#### Task 4.1: 协调MCP (端口8009)
**职责**: 管理多MCP任务调度和数据聚合
- **核心功能**:
  - `orchestrate_stock_analysis`: 综合分析调度
  - `prioritize_data_sources`: 数据源优先级管理
  - `aggregate_responses`: 多源数据聚合
  - `handle_failures`: 级联故障处理
- **智能调度**:
  - 根据用户查询类型选择合适的MCP组合
  - 并行调用优化响应时间
  - 数据源失效时的降级策略
- **状态**: ⏳ 待开始

#### Task 4.2: 复杂查询处理
- **多维度分析**: 技术面+基本面+资金面+消息面
- **批量查询**: 支持多只股票对比分析
- **历史回测**: 策略验证功能
- **状态**: ⏳ 待开始

### Phase 5: Claude API集成层 (3天)

#### Task 5.1: Claude API集成服务 (端口9000)
**职责**: Claude API与4MCP服务器的桥接层
- **核心功能**:
  - `claude_mcp_connector`: Claude API连接器
  - `intent_analysis`: 用户意图分析
  - `response_synthesis`: 智能响应合成
  - `context_management`: 对话上下文管理
- **技术实现**:
  - Anthropic Python SDK集成
  - MCP服务器发现和路由
  - 响应格式化和优化
- **状态**: ⏳ 待开始

#### Task 5.2: 智能响应优化
- **数据精炼**: 复杂JSON转换为用户友好格式
- **投资洞察**: 基于数据生成专业分析
- **风险提示**: 自动风险评估和提醒
- **状态**: ⏳ 待开始

### Phase 6: 前端集成与测试 (4天)

#### Task 6.1: React前端适配
- **MCP集成**: 前端调用Claude API集成层
- **数据可视化**: K线图表、财务报表展示
- **用户交互**: 自然语言查询界面
- **状态**: ⏳ 待开始

#### Task 6.2: 端到端测试
- **功能测试**: 完整用户场景测试
- **性能测试**: 并发负载测试
- **稳定性测试**: 长时间运行测试
- **状态**: ⏳ 待开始

## 🚀 启动方式

### 开发环境启动
```bash
# 1. 启动现有基础服务
cd /home/wyatt/prism2
source test_venv/bin/activate
python enhanced_dashboard_api.py &
python -m rag_service.main &

# 2. 启动4MCP服务器集群
cd mcp_servers
source mcp_venv/bin/activate
python realtime_data_mcp/server.py &      # 端口8006
python structured_data_mcp/server.py &    # 端口8007
python rag_mcp/server.py &                # 端口8008
python coordination_mcp/server.py &       # 端口8009

# 3. 启动Claude API集成层
python claude_integration/server.py &     # 端口9000

# 4. 启动前端
cd frontend
npm run dev                               # 端口3000
```

### 生产环境启动
```bash
# Docker Compose方式
docker-compose up -d prism2-4mcp-cluster
```

## 🔗 系统集成方式

### 与现有系统的集成
- **Enhanced Dashboard API**: 作为结构化数据MCP的后备数据源
- **RAG Service**: 直接集成到RAG-MCP中
- **PostgreSQL**: 继续作为主要数据存储
- **Redis**: 作为缓存层提升性能
- **Ollama + Qwen**: 保留在Open WebUI中作为测试功能

### 数据流向
1. **用户查询** → React前端 → Claude API集成层
2. **意图分析** → 路由到相应MCP服务器
3. **数据获取** → 多源并行获取 → 协调MCP聚合
4. **智能分析** → Claude API分析 → 精炼输出
5. **结果展示** → React前端可视化 → 用户

## 📊 质量保证

### 测试策略
- **单元测试**: 每个MCP服务器95%覆盖率
- **集成测试**: 4MCP协同工作验证
- **性能测试**: 响应时间 < 3秒
- **稳定性测试**: 24小时无故障运行

### 监控指标
- **响应时间**: 各MCP服务器响应时间监控
- **可用性**: 服务健康状态实时监控
- **数据质量**: 数据准确性和完整性检查
- **用户体验**: 查询成功率和满意度

## 🎯 成功标准

### 技术指标
- ✅ 4个MCP服务器正常运行
- ✅ Claude API集成成功
- ✅ 响应时间 < 3秒
- ✅ 系统可用性 > 99%

### 功能指标
- ✅ 支持完整的股票分析功能
- ✅ 智能意图理解和响应
- ✅ 多数据源无缝集成
- ✅ 用户友好的数据展示

### 用户体验
- ✅ 自然语言查询支持
- ✅ 精准的投资洞察
- ✅ 快速响应体验
- ✅ 专业的分析报告

---

**开发负责人**: Claude Code
**文档版本**: v1.0
**最后更新**: 2025-09-25
**下一步行动**: 开始Phase 1清理和基础设施准备