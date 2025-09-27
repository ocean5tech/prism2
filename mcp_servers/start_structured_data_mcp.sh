#!/bin/bash
# Structured Data MCP Server 启动脚本 (端口8007)

echo "🚀 启动 Structured Data MCP Server (端口8007)"
echo "================================================"

# 切换到项目目录
cd /home/wyatt/prism2/mcp_servers

# 激活虚拟环境
echo "📦 激活虚拟环境..."
source mcp4_venv/bin/activate

# 设置Python路径
echo "🔧 配置Python路径..."
export PYTHONPATH=/home/wyatt/prism2/mcp_servers/shared:$PYTHONPATH

# 检查依赖服务
echo "🔍 检查依赖服务状态..."

# 检查Redis
echo "检查Redis连接..."
python -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
    print('✅ Redis 连接正常')
except Exception as e:
    print(f'❌ Redis 连接失败: {e}')
"

# 检查Enhanced Dashboard API
echo "检查Enhanced Dashboard API..."
python -c "
import requests
try:
    response = requests.get('http://localhost:8003/health', timeout=5)
    if response.status_code == 200:
        print('✅ Enhanced Dashboard API 运行正常')
    else:
        print(f'⚠️  Enhanced Dashboard API 状态: {response.status_code}')
except Exception as e:
    print(f'❌ Enhanced Dashboard API 不可用: {e}')
"

# 运行预检测试
echo "🧪 运行预检测试..."
python test_structured_data.py | grep -E "(✅|❌|🎉)"

# 启动MCP服务器
echo "🌟 启动MCP服务器..."
echo "服务地址: http://localhost:8007"
echo "按 Ctrl+C 停止服务"
echo "================================================"

# 启动服务器
mcpo --config structured_data_mcp/mcpo_config.json --host 0.0.0.0 --port 8007