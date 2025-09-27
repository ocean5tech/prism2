#!/bin/bash
# Claude Code 标准系统验证脚本
# 基于经验教训文档创建，避免历史验证错误

echo "🔍 Claude Code 系统状态检查"
echo "========================================"

# 1. 读取历史记录
echo "📋 1. 检查安装历史记录"
if [ -f "/home/wyatt/prism2/docs/基础设施.log" ]; then
    echo "✅ 基础设施安装日志存在"
    tail -3 /home/wyatt/prism2/docs/基础设施.log
else
    echo "⚠️ 基础设施日志未找到"
fi

# 2. 清除代理环境 (关键步骤)
echo ""
echo "🌐 2. 清除代理环境"
export http_proxy="" https_proxy="" HTTP_PROXY="" HTTPS_PROXY=""
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
echo "✅ 代理环境已清除"

# 3. 检查容器状态 (正确方法)
echo ""
echo "🐳 3. 检查容器服务状态"
echo "容器运行状态:"
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep prism2

# 4. 检查端口监听
echo ""
echo "🔌 4. 检查端口监听状态"
echo "关键端口监听:"
ss -tlnp | grep -E "(5432|6379|8000|8080|11434)" | sed 's/.*://' | awk '{print $1 " - " $2}'

# 5. 检查Python进程
echo ""
echo "🐍 5. 检查Python服务进程"
python_procs=$(ps aux | grep python | grep -v grep | grep -E "(main|uvicorn|test)" | wc -l)
if [ $python_procs -gt 0 ]; then
    echo "✅ 发现 $python_procs 个Python服务进程:"
    ps aux | grep python | grep -v grep | grep -E "(main|uvicorn|test)" | awk '{print "  - " $11 " " $12}'
else
    echo "❌ 未发现Python服务进程"
fi

# 6. API功能验证 (绕过代理)
echo ""
echo "🌐 6. API功能验证"

# 测试Backend API
if curl -s http://127.0.0.1:8080/api/v1/health > /dev/null 2>&1; then
    echo "✅ Backend测试版API (8080) 可用"
else
    echo "❌ Backend测试版API (8080) 不可用"
fi

if curl -s http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1; then
    echo "✅ Backend完整版API (8000) 可用"
else
    echo "❌ Backend完整版API (8000) 不可用"
fi

# 测试Ollama (如果端口开放)
if ss -tln | grep -q ":11434"; then
    if curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama API (11434) 可用"
        model_count=$(curl -s http://127.0.0.1:11434/api/tags | grep -o '"name"' | wc -l)
        echo "   - 已安装模型数量: $model_count"
    else
        echo "❌ Ollama API (11434) 不响应"
    fi
else
    echo "⏭️ Ollama端口未开放，跳过检查"
fi

# 7. 数据库连接验证
echo ""
echo "💾 7. 数据库连接验证"
if podman exec prism2-postgres psql -U prism2 -d prism2 -c "SELECT 1" > /dev/null 2>&1; then
    echo "✅ PostgreSQL连接正常"
    table_count=$(podman exec prism2-postgres psql -U prism2 -d prism2 -c "\dt" 2>/dev/null | grep "table" | wc -l)
    echo "   - 数据表数量: $table_count"
else
    echo "❌ PostgreSQL连接失败"
fi

if podman exec prism2-redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis连接正常"
    key_count=$(podman exec prism2-redis redis-cli KEYS "*" | wc -l)
    echo "   - 缓存键数量: $key_count"
else
    echo "❌ Redis连接失败"
fi

# 8. 总结建议
echo ""
echo "💡 8. 系统状态总结"
echo "========================================"

container_count=$(podman ps | grep prism2 | wc -l)
if [ $container_count -ge 2 ]; then
    echo "✅ 容器服务: 正常 ($container_count/3+ 运行)"
else
    echo "⚠️ 容器服务: 需要启动更多服务"
fi

if [ $python_procs -gt 0 ]; then
    echo "✅ Backend服务: 正常"
else
    echo "⚠️ Backend服务: 需要启动"
    echo "   建议: cd /home/wyatt/prism2/backend && source test_venv/bin/activate && python test_main.py &"
fi

echo ""
echo "📚 相关文档:"
echo "   - 操作手册: /home/wyatt/prism2/CLAUDE_OPERATIONS.md"
echo "   - 经验教训: /home/wyatt/prism2/docs_archive/LessonsLearned.md"
echo "   - 会话模板: /home/wyatt/prism2/CLAUDE_SESSION_TEMPLATE.md"