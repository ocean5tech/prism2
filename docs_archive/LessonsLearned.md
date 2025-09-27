# Prism2 项目经验教训文档

## 📚 文档目的

这个文档记录了在Prism2项目开发过程中遇到的问题、解决方案和重要经验教训。目的是避免重复犯错，提高后续开发效率。

## 🎯 更新原则

**⚠️ 重要原则**:
- **每当遇到新问题或学到新经验时，必须主动更新此文档**
- **所有团队成员都有责任维护此文档的完整性和时效性**
- **在开始新的技术实施前，必须先阅读此文档相关章节**

---

## 🚨 环境配置与安装问题

### 1. 代理服务器问题 (❗ 高优先级)

#### 问题描述
在企业环境中，系统配置了HTTP代理服务器(如IBM代理)，这会严重影响多个安装和配置过程。

#### 影响范围
- **GitHub下载**: Ollama安装脚本无法下载
- **容器网络**: ChromaDB API访问被拦截(403错误)
- **模型下载**: AI模型下载速度极慢或失败
- **Python包安装**: pip安装超时或失败

#### 代理环境变量示例
```bash
# 这些环境变量会影响安装过程
HTTP_PROXY=http://proxy.emea.ibm.com:8080
HTTPS_PROXY=http://proxy.emea.ibm.com:8080
http_proxy=http://proxy.emea.ibm.com:8080
https_proxy=http://proxy.emea.ibm.com:8080
NO_PROXY=<local>
no_proxy=<local>
```

#### 解决方案
1. **临时清除代理** (推荐用于安装过程):
   ```bash
   export http_proxy="" https_proxy="" HTTP_PROXY="" HTTPS_PROXY=""
   ```

2. **容器启动时清除代理**:
   ```bash
   # 正确的启动方式
   export http_proxy="" https_proxy="" && podman run -d container_name
   ```

3. **检查代理设置**:
   ```bash
   env | grep -i proxy  # 查看当前代理设置
   ```

#### 预防措施
- 安装任何网络相关服务前，先检查并清除代理设置
- 容器启动脚本中明确设置空代理变量
- 在安装脚本开头添加代理清除命令

---

### 2. Ollama安装问题

#### 问题描述
GitHub连接超时，无法下载Ollama安装脚本

#### 错误信息
```
curl: (28) Failed to connect to github.com port 443 after 123957 ms
```

#### 根本原因
企业代理服务器阻止或延迟GitHub API访问

#### 解决方案
```bash
# 1. 清除代理设置
export http_proxy="" https_proxy="" HTTP_PROXY="" HTTPS_PROXY=""

# 2. 重新安装
curl -fsSL https://ollama.ai/install.sh | sh
```

#### 经验教训
- 任何从GitHub下载的工具都可能遇到此问题
- 优先考虑清除代理，而不是配置代理绕过

---

### 3. ChromaDB API访问问题

#### 问题描述
ChromaDB容器启动后API返回403 Forbidden错误

#### 错误现象
```bash
curl http://localhost:8000/api/v1/heartbeat
# 返回: HTTP/1.0 403 Forbidden
```

#### 根本原因
容器启动时继承了宿主机的代理环境变量，导致容器内部网络请求被代理服务器拦截

#### 解决方案
```bash
# 1. 停止并删除问题容器
podman stop prism2-chromadb && podman rm prism2-chromadb

# 2. 清除代理后重新启动
export http_proxy="" https_proxy="" HTTP_PROXY="" HTTPS_PROXY=""
podman run -d --name prism2-chromadb \
    --restart unless-stopped \
    -p 8000:8000 \
    -v ~/prism2/data/chromadb:/chroma/chroma \
    -e CHROMA_SERVER_HOST=0.0.0.0 \
    -e CHROMA_SERVER_HTTP_PORT=8000 \
    docker.io/chromadb/chroma:latest
```

#### 预防措施
- 所有容器启动前都要清除代理环境变量
- 添加显式的服务器配置环境变量
- 创建测试脚本验证容器API功能

---

### 4. Python环境管理问题

#### 问题描述
Ubuntu 24.04使用externally-managed-environment，不能直接用pip安装包

#### 错误信息
```
error: externally-managed-environment
× This environment is externally managed
```

#### 解决方案
```bash
# 1. 使用虚拟环境 (推荐)
python3 -m venv ~/prism2/venv
source ~/prism2/venv/bin/activate
pip install package_name

# 2. 或者使用系统包管理器
sudo apt install python3-package-name

# 3. 强制安装 (不推荐)
pip install --break-system-packages package_name
```

#### 最佳实践
- 总是使用虚拟环境进行Python开发
- 项目根目录创建venv目录
- 在激活脚本中添加环境变量设置

---

## 🔧 技术实施经验

### 1. 容器管理最佳实践

#### 命名规范
```bash
# 统一的容器命名格式
prism2-{service-name}
# 例如: prism2-postgres, prism2-redis, prism2-chromadb
```

#### 重启策略
```bash
# 总是使用unless-stopped重启策略
--restart unless-stopped
```

#### 数据持久化
```bash
# 统一的数据目录结构
~/prism2/data/{service-name}/
# 例如: ~/prism2/data/postgres/, ~/prism2/data/redis/
```

### 2. 网络端口规划

| 服务 | 端口 | 用途 | 状态 |
|------|------|------|------|
| PostgreSQL + TimescaleDB | 5432 | 主数据库 | ✅ |
| Redis | 6379 | 缓存 | ✅ |
| ChromaDB | 8000 | 向量数据库 | ✅ |
| Ollama | 11434 | LLM API | ✅ |
| Open WebUI | 3000 | AI管理界面 | 🔄 |

### 3. 资源监控要点

#### 内存使用
- Ollama + 7B模型: ~6GB
- 总系统内存需求: 8GB+ (推荐16GB)
- 监控命令: `free -h`, `htop`

#### 磁盘使用
- AI模型文件: ~5.5GB
- 容器镜像: ~3.5GB
- 监控命令: `df -h`, `du -sh /path`

---

## 🚀 开发流程经验

### 1. 安装验证标准

每个服务安装后必须进行功能验证:

#### 数据库验证
```bash
# PostgreSQL
echo "SELECT version();" | psql -h localhost -U postgres -d postgres

# Redis
redis-cli ping

# ChromaDB
curl http://localhost:8000/api/v1/heartbeat
```

#### AI模型验证
```bash
# 测试模型响应
echo "hello" | ollama run model-name
```

### 2. 问题排查流程

1. **检查容器状态**: `podman ps -a`
2. **查看容器日志**: `podman logs container-name`
3. **检查端口占用**: `netstat -tlnp | grep port`
4. **验证网络连接**: `curl -v http://localhost:port`
5. **检查代理设置**: `env | grep -i proxy`

### 3. 回滚策略

#### 容器服务回滚
```bash
# 停止问题容器
podman stop container-name

# 删除容器(保留数据)
podman rm container-name

# 使用之前的工作配置重新创建
podman run [previous-working-config]
```

#### 数据备份策略
```bash
# 定期备份数据目录
tar -czf backup-$(date +%Y%m%d).tar.gz ~/prism2/data/
```

---

## 📝 文档维护指南

### 更新触发条件
- ✅ 遇到新的技术问题或错误
- ✅ 发现更好的解决方案或工具
- ✅ 安装新的服务或组件
- ✅ 修改现有配置或架构
- ✅ 团队成员反馈新的经验

### 更新格式要求
1. **问题描述**: 清晰描述遇到的问题
2. **错误信息**: 提供具体的错误输出
3. **根本原因**: 分析问题的本质原因
4. **解决方案**: 提供可执行的解决步骤
5. **预防措施**: 如何避免再次发生

### 文档审查周期
- **每个月**: 审查并更新过时信息
- **项目里程碑**: 总结阶段性经验教训
- **新团队成员**: 协助完善文档内容

---

---

## ❌ **重大错误记录: 依赖验证失败事件** (2025-09-16 15:30)

### 🚨 **严重程度**: 高 - 影响项目进度和决策

#### 问题描述
Claude Code在进行外部依赖验证时，错误地得出多个已安装组件"不可用"的结论，导致：
1. 错误的技术决策 (建议降级到SQLite等)
2. 不必要的架构修改计划
3. 对项目现状的误判
4. 浪费大量时间重新验证

#### 错误验证结果对比

| 组件 | 错误结论❌ | 实际状态✅ | 验证命令错误 |
|------|----------|----------|------------|
| PostgreSQL | 客户端未安装 | 容器运行5小时 (5432端口) | `which psql` → 应该用 `podman ps` |
| Redis | 客户端未安装 | 容器运行5小时 (6379端口) | `which redis-cli` → 应该检查容器 |
| Docker | 未安装 | Podman 4.9.3正常运行 | `docker --version` → 应该用 `podman` |
| Ollama | 服务不可用 | 正常运行+2个模型 | 代理阻塞了API访问 |
| ChromaDB | 未验证 | 容器运行4小时 (8000端口) | 同样被代理影响 |

#### 🎯 **根本原因分析**

**1. 概念性错误 - 容器化vs传统安装**
```bash
# ❌ 错误的验证思路
which psql || echo "PostgreSQL未安装"
which docker || echo "Docker未安装"

# ✅ 正确的验证方法
podman ps | grep postgres  # 检查容器状态
ss -tlnp | grep 5432      # 检查端口监听
```

**2. 网络环境影响 - 企业代理问题**
```bash
# 问题环境变量
http_proxy=http://proxy.emea.ibm.com:8080
https_proxy=http://proxy.emea.ibm.com:8080
no_proxy=<local>  # 配置不完整！

# 导致问题
curl localhost:11434  # 被代理拦截
curl 127.0.0.1:11434  # 同样失败

# ✅ 正确验证方式
unset http_proxy https_proxy
curl -s http://127.0.0.1:11434/api/tags  # 成功返回模型列表
```

**3. 验证流程缺陷**
- ❌ 没有优先读取安装日志 `/home/wyatt/prism2/docs/基础设施.log`
- ❌ 孤立验证每个组件，未考虑整体架构
- ❌ 使用传统命令验证容器化服务
- ❌ 忽视网络环境对验证的影响

#### 📊 **实际系统状态** (2025-09-16 15:30验证)

**容器服务状态**:
```bash
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
NAMES            STATUS      PORTS
prism2-postgres  Up 5 hours  0.0.0.0:5432->5432/tcp
prism2-redis     Up 5 hours  0.0.0.0:6379->6379/tcp
prism2-chromadb  Up 4 hours  0.0.0.0:8000->8000/tcp
```

**AI服务状态**:
```bash
# Ollama进程正常
ps aux | grep ollama
wyatt  24666  1.4  0.9 2964244 75416 ?  Sl  11:28  3:50 ollama serve

# 已安装模型 (绕过代理验证)
unset http_proxy https_proxy && curl -s http://127.0.0.1:11434/api/tags
{
  "models": [
    {"name": "deepseek-coder:1.3b", "size": 776080839},
    {"name": "qwen2.5:7b", "size": 4683087332}
  ]
}
```

#### 🛠️ **立即纠正措施**

1. **✅ 更新外部依赖报告** - 标记所有组件为可用
2. **✅ 修正内部设计文档** - 移除错误的"需要替代方案"建议
3. **✅ 创建标准验证脚本** - 避免再次发生类似错误
4. **✅ 记录此次经验教训** - 永久保存教训

#### 💡 **预防措施**

**建立标准验证流程**:
```bash
#!/bin/bash
# 标准基础设施验证脚本
echo "📋 1. 读取安装日志"
tail -10 ~/prism2/docs/基础设施.log

echo "🐳 2. 检查容器状态"
podman ps

echo "🌐 3. 检查端口监听(清除代理)"
unset http_proxy https_proxy
ss -tlnp | grep -E "(5432|6379|8000|11434)"

echo "🔧 4. API功能验证"
curl -s http://127.0.0.1:11434/api/tags > /dev/null && echo "✅ Ollama" || echo "❌ Ollama"
```

**文档要求**:
- 每个内部设计文档必须包含"环境要求"部分
- 验证前必须先读取项目现有文档和日志
- 容器化服务优先使用容器命令验证

#### 🎓 **核心教训**

1. **📖 先读文档，再验证** - 避免重复不必要的工作
2. **🏗️ 理解架构** - 容器化vs传统安装需要不同验证方法
3. **🌐 考虑环境** - 网络代理等环境因素会影响验证
4. **🔍 系统思考** - 整体验证比单点验证更可靠
5. **⚠️ 错误验证比无验证更危险** - 会导致错误决策

**最重要的教训**: 在对系统现状做出任何结论前，必须先充分了解系统的实际架构和历史记录！

## 🎯 待解决的已知问题

### 1. RSS源替代方案研究
- **状态**: 主要财经RSS源确实不可访问
- **影响**: News Service需要替代数据源
- **方案**: 使用AKShare新闻接口或直接爬取
- **优先级**: 中等

### 2. Open WebUI容器下载缓慢
- **状态**: 镜像下载中
- **影响**: 管理界面暂时不可用
- **临时方案**: 直接使用Ollama CLI
- **跟踪**: 等待下载完成并验证功能

---

## 📞 问题上报流程

如果遇到本文档未涵盖的新问题:

1. **立即记录**: 截图保存错误信息
2. **尝试解决**: 按照一般排查流程操作
3. **更新文档**: 解决后立即更新此文档
4. **团队分享**: 通知团队成员新的经验教训

---

*最后更新: 2025-09-16*
*维护者: Prism2开发团队*
*版本: v1.0*