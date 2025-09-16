# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Prism2 is a comprehensive stock analysis platform built with a modern microservices architecture. The project integrates RAG-enhanced AI analysis, real-time data processing, and professional financial visualizations.

## Project Structure

This is currently an early-stage project with architectural documentation in place. The codebase contains:
- `/docs/architecture-design.md` - Comprehensive technical architecture document
- `/docs/LessonsLearned.md` - **⚠️ MUST READ** - Critical lessons learned and troubleshooting guide
- `/docs/基础设施.log` - Infrastructure installation log with detailed progress
- `README.md` - Setup instructions for VS Code integration with WSL
- `open-vscode.sh` - Script to launch VS Code from WSL environment

## ❗ IMPORTANT: Read Before Starting

**🚨 MANDATORY READING**: Before working on this project or encountering any technical issues, you MUST read `/docs/LessonsLearned.md`. This document contains:

- Critical proxy configuration issues that will block installations
- Known environment-specific problems and solutions
- Container configuration best practices
- Troubleshooting workflows for common errors

**Failure to read the LessonsLearned document will likely result in encountering already-solved problems and wasted time.**

## Development Environment

This project is designed to run in a WSL (Windows Subsystem for Linux) environment with VS Code integration. The architecture calls for Docker Compose orchestration with multiple microservices.

## Planned Architecture

The system is designed with these key components:

### Frontend Layer
- React 18 + TypeScript PWA (Port 3000)
- Vite build system
- Tailwind CSS styling
- Lightweight Charts for K-line data, ECharts for statistics

### API Gateway
- Nginx reverse proxy (Port 80/443)
- Routes `/api/stock/` → Stock Analysis Service (8000)
- Routes `/api/rag/` → RAG Service (8001)
- Routes `/api/data/` → Data Service (8003)
- Routes `/ollama/` → Ollama (11434)

### Business Services
- **Stock Analysis Service** (Port 8000): FastAPI, main business logic
- **RAG Service** (Port 8001): FastAPI + LangChain for enhanced AI context
- **Data Collection Service** (Port 8002): Scrapy + Kafka for data ingestion

### AI Model Layer
- **Ollama** (Port 11434): Local LLM with Qwen2.5-7B-Instruct
- **Open WebUI** (Port 3000): LLM management interface
- **bge-large-zh-v1.5**: Chinese-optimized text vectorization

### Data Processing (Learning-oriented)
- **Apache Kafka** (Port 9092): Message queuing system
- **Apache Spark**: Batch and stream processing
- **APScheduler**: Task scheduling

### Storage Layer
- **PostgreSQL + TimescaleDB** (Port 5432): Primary database with time-series optimization
- **ChromaDB/Qdrant**: Vector database for semantic search
- **Redis** (Port 6379): Caching layer
- **MinIO**: Object storage (optional)

## Technology Stack

### Languages & Frameworks
- **Frontend**: React 18, TypeScript, Vite
- **Backend**: Python 3.12, FastAPI
- **Database**: PostgreSQL 15 with TimescaleDB extension
- **AI/ML**: Ollama, LangChain, bge-large-zh-v1.5

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Message Queue**: Apache Kafka
- **Big Data**: Apache Spark (for learning purposes)
- **Caching**: Redis 7
- **Reverse Proxy**: Nginx

## Development Commands

Since this is an early-stage project, specific build/test commands are not yet established. Based on the architecture:

### Expected Docker Commands
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f [service-name]

# Stop services
docker-compose down
```

### Expected Frontend Commands (when implemented)
```bash
# Development server
npm run dev

# Build for production
npm run build

# Type checking
npm run typecheck

# Linting
npm run lint
```

### Expected Backend Commands (when implemented)
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload

# Run tests
pytest

# Code formatting
black .
```

## Key Implementation Notes

- The project emphasizes Chinese language support (中文优化)
- Designed for both web and mobile access via PWA
- Uses TimescaleDB for optimized time-series data handling
- Implements professional financial charting with K-line support
- Integrates local LLM for offline AI capabilities
- Includes big data components (Spark/Kafka) for learning purposes

## Resource Requirements

- **CPU**: 8 cores recommended
- **Memory**: 16GB (for Spark + Ollama + databases)
- **Storage**: 50GB (including models and data)
- **Network**: Gigabit networking recommended

## Development Workflow

The project follows a phased development approach:
1. **Phase 1**: Basic infrastructure and Docker setup
2. **Phase 2**: Core stock data integration and React frontend
3. **Phase 3**: RAG integration with vector database
4. **Phase 4**: Big data pipeline (Kafka + Spark)
5. **Phase 5**: Production optimization and deployment

## 📝 Documentation-Driven Development Rules

### 🚨 MANDATORY DEVELOPMENT WORKFLOW

**❗ CRITICAL PRINCIPLE**: This project follows **strict documentation-first development**. You MUST adhere to this workflow:

#### **1. Documentation-First Development Process**

**🔄 REQUIRED WORKFLOW**:
```
External Design → Internal Design → Documentation Updates → Code Implementation
```

**⚠️ FORBIDDEN WORKFLOW**:
```
❌ Code Implementation → Document Updates (NEVER DO THIS)
```

#### **2. Development Process Rules**

**BEFORE writing any code**:
1. **Read External Design** (`/docs/external-design.md`) - Understand the requirements
2. **Read Internal Design** (`/docs/internal-design/{module-name}.md`) - Check implementation specs
3. **Verify Documentation Consistency** - Ensure internal matches external design
4. **Update Documentation First** - If any design needs modification

**IF you find issues with design documents**:
1. **STOP coding immediately**
2. **Update the relevant documentation first**
3. **Verify consistency across all related documents**
4. **THEN proceed with code implementation**

#### **3. Development Log System**

**📋 MANDATORY LOGGING**: Each internal design document has a corresponding development log:

```
/docs/internal-design/
├── frontend-module.md
├── frontend-module.log          ← Development progress log
├── stock-analysis-service.md
├── stock-analysis-service.log   ← Development progress log
├── rag-service.md
├── rag-service.log             ← Development progress log
└── ...
```

**🔄 LOG UPDATE REQUIREMENTS**:

**When to update logs**:
- **Start development** on a module
- **Complete each major feature/API**
- **Encounter and solve problems**
- **Before ending each development session**
- **When resuming after interruption**

**Log format** (follow `/docs/基础设施.log` example):
```
# {Module Name} 开发日志

## 📋 模块基本信息
- **模块名称**: {Full module name and purpose}
- **技术栈**: {Technologies used}
- **部署端口**: {Port number}
- **依据文档**: `/docs/internal-design/{module-name}.md`
- **开发开始时间**: {YYYY-MM-DD HH:MM}
- **当前状态**: {Status description}

## 📋 开发前状态检查
### 依赖服务状态
- **Service A**: ✅ 运行中 / ❌ 未运行 / ⏳ 待启动
- **Service B**: 状态描述

### 设计文档状态
- ✅/❌/⏳ External design status
- ✅/❌/⏳ Internal design status
- ✅/❌/⏳ Interface consistency verified

---

## 🚀 开发阶段记录

### Phase 1: 项目初始化 (开始时间: YYYY-MM-DD HH:MM)

#### 步骤 1.1: {具体任务名称}
**时间**: YYYY-MM-DD HH:MM - HH:MM
**操作**: {详细操作描述}
**状态**: ✅ 完成 / ❌ 失败 / 🔄 进行中
**命令**: {具体执行的命令}
**结果**: {操作结果描述}
**验证**: {验证方法和结果}

#### ✅ Phase 1 完成总结
**完成时间**: YYYY-MM-DD HH:MM
**总耗时**: 约X小时
**状态**: 全部成功 / 部分完成 / 需要修复
**实现功能**:
- ✅ Feature A
- ✅ Feature B
- ❌ Feature C (原因)

#### 🛠️ 问题解决记录 (如有)
##### 问题描述
**时间**: YYYY-MM-DD HH:MM
**现象**: {具体问题现象}
**影响**: {问题影响范围}

##### 解决方案
**诊断步骤**: {诊断过程}
**解决方法**: {具体解决步骤}
**验证结果**: {修复验证}
```

#### **4. Checkpoint Recovery System**

**🔄 SESSION RESUMPTION**: When returning to development after interruption:

1. **Read the relevant `.log` file** to understand current status
2. **Verify last checkpoint** - what was completed vs. what's pending
3. **Check for any blockers** mentioned in the log
4. **Update documentation** if any design changes are needed
5. **Continue from documented checkpoint**

#### **5. Enforcement Rules**

**⚠️ VIOLATIONS**: The following are **STRICTLY PROHIBITED**:

- ❌ Writing code without reading documentation first
- ❌ Modifying code without updating documentation
- ❌ Skipping development log updates
- ❌ Implementing features not defined in internal design
- ❌ Changing APIs without updating external design first

**✅ REQUIRED PRACTICES**:

- ✅ Always start with documentation review
- ✅ Update documents before code changes
- ✅ Maintain detailed development logs
- ✅ Use logs as checkpoints for resuming work
- ✅ Ensure design consistency across all modules

### LessonsLearned.md Update Protocol

**🔄 MANDATORY UPDATES**: You MUST update `/docs/LessonsLearned.md` whenever you:

1. **Encounter a new technical problem** - Even if solved quickly
2. **Discover a better solution** - Replace outdated approaches
3. **Install new components** - Document configuration challenges
4. **Modify existing services** - Update best practices
5. **Experience environment-specific issues** - Especially proxy/network problems

### Update Requirements

**Format**: Follow the existing document structure:
- **Problem Description**: Clear issue statement
- **Error Information**: Exact error messages/codes
- **Root Cause**: Technical analysis of why it happened
- **Solution Steps**: Reproducible fix instructions
- **Prevention**: How to avoid in the future

**Timing**: Update immediately after resolving any issue - don't delay!

**Verification**: Test your documented solution works before committing

This documentation maintenance is not optional - it's a critical part of the development process that saves significant time for future work.