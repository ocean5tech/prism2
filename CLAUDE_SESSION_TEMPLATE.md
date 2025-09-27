# Claude 会话开始模板

每次开始新的Claude Code会话时，必须执行此检查清单。

## 🔍 第一步：读取操作手册
```bash
# 必须首先读取
cat /home/wyatt/prism2/CLAUDE_OPERATIONS.md
```

## 🚀 第二步：环境检查
```bash
# 1. 检查Podman容器状态
podman ps

# 2. 检查当前运行的Python服务
ps aux | grep python | grep -v grep

# 3. 确认当前工作目录
pwd
```

## 📋 第三步：服务启动决策树

### 如果需要启动Backend服务：

**情况A: 需要完整功能测试**
```bash
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

**情况B: 需要快速API验证**
```bash
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
python test_main.py &
```

**情况C: 需要批处理测试**
```bash
cd /home/wyatt/prism2/backend
source test_venv/bin/activate
python test_batch_integration.py
```

### 如果需要启动数据库服务：
```bash
podman start prism2-postgres
podman start prism2-redis
```

## 🎯 第四步：功能验证
```bash
# API健康检查
curl http://localhost:8080/api/v1/health  # 测试版
curl http://localhost:8000/api/v1/health  # 完整版

# 数据库连接检查
podman exec prism2-redis redis-cli ping
podman exec prism2-postgres psql -U prism2 -d prism2 -c "SELECT 1"
```

## 📝 第五步：会话记录更新

### 如果发现新方法或遇到问题：
1. 立即更新 `CLAUDE_OPERATIONS.md`
2. 记录解决方案到相应的 `.md` 文件
3. 确保知识可以传承到下次会话

### 模板更新：
- 添加新的启动方法
- 记录新的验证流程
- 更新故障排除步骤

---

**使用说明**:
- 每次会话开始时按顺序执行此模板
- 根据具体需求选择相应的分支
- 会话结束时更新相关文档