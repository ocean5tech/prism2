#!/bin/bash

# 启动RAG Service FastAPI主程序
# 端口8001 - 核心RAG服务API

echo "🚀 启动RAG Service..."

# 检查工作目录
WORK_DIR="/home/wyatt/prism2/rag-service"
cd "$WORK_DIR" || {
    echo "❌ 无法进入工作目录: $WORK_DIR"
    exit 1
}

echo "📁 工作目录: $WORK_DIR"

# 检查必要文件
REQUIRED_FILES=(
    "app/main.py"
    "requirements.txt"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ 缺少必要文件: $file"
        exit 1
    fi
done

echo "📄 必要文件检查通过"

# 创建日志目录
mkdir -p logs
echo "📂 日志目录已创建"

# 检查虚拟环境
if [[ ! -d "venv" ]] && [[ ! -d "rag_env" ]]; then
    echo "❌ 找不到虚拟环境目录"
    exit 1
fi

# 设置虚拟环境路径
if [[ -d "rag_env" ]]; then
    VENV_PATH="rag_env"
    echo "✅ 使用rag_env虚拟环境"
else
    VENV_PATH="venv"
    echo "✅ 使用venv虚拟环境"
fi

# 设置Python和uvicorn路径
PYTHON_PATH="$VENV_PATH/bin/python"
UVICORN_PATH="$VENV_PATH/bin/uvicorn"

# 检查Python依赖
echo "🔍 检查Python依赖..."
$PYTHON_PATH -c "
import sys
try:
    import fastapi, uvicorn
    print('✅ 核心依赖OK')
except ImportError as e:
    print(f'❌ 缺少依赖: {e}')
    sys.exit(1)
"

if [[ $? -ne 0 ]]; then
    echo "📦 安装缺少的依赖..."
    $VENV_PATH/bin/pip install -r requirements.txt
fi

# 检查uvicorn可执行文件
if [[ ! -f "$UVICORN_PATH" ]]; then
    echo "❌ uvicorn不在虚拟环境中，尝试安装..."
    $VENV_PATH/bin/pip install uvicorn
fi

# 检查依赖服务状态
echo "🔍 检查依赖服务..."

# 检查ChromaDB (容器运行但API可能暂时不可用)
if podman ps --filter name=prism2-chromadb --filter status=running | grep -q chromadb; then
    echo "✅ ChromaDB容器正在运行"
    if curl -s http://localhost:8000 >/dev/null 2>&1; then
        echo "✅ ChromaDB API可访问"
    else
        echo "⚠️ ChromaDB容器运行但API暂时不可访问 - 将继续启动但功能可能受限"
    fi
else
    echo "❌ ChromaDB容器未运行"
    echo "请先启动ChromaDB服务"
    exit 1
fi

# 检查PostgreSQL
if podman exec prism2-postgres pg_isready -U postgres >/dev/null 2>&1; then
    echo "✅ PostgreSQL (端口5432) 可访问"
else
    echo "❌ PostgreSQL (端口5432) 不可访问"
    echo "请先启动PostgreSQL服务"
    exit 1
fi

# 检查Redis
if podman exec prism2-redis redis-cli ping >/dev/null 2>&1; then
    echo "✅ Redis (端口6379) 可访问"
else
    echo "❌ Redis (端口6379) 不可访问"
    echo "请先启动Redis服务"
    exit 1
fi

# 启动RAG Service
echo "⏰ RAG Service启动参数:"
echo "  端口: 8001"
echo "  主机: 0.0.0.0"
echo "  工作进程: 1"
echo "  重载模式: ${RELOAD:-false}"

LOG_FILE="logs/rag_service_$(date +%Y%m%d_%H%M%S).log"

if [[ "$1" == "dev" ]]; then
    echo "🔄 开发模式启动 (带重载)..."
    $UVICORN_PATH app.main:app --host 0.0.0.0 --port 8001 --reload --log-level info
elif [[ "$1" == "test" ]]; then
    echo "🧪 测试模式启动..."
    $UVICORN_PATH app.main:app --host 0.0.0.0 --port 8001 --log-level debug
else
    echo "🔄 生产模式启动..."

    # 设置代理环境变量绕过localhost
    export no_proxy="localhost,127.0.0.1,::1,0.0.0.0"
    export NO_PROXY="localhost,127.0.0.1,::1,0.0.0.0"

    # 后台运行
    nohup env no_proxy="localhost,127.0.0.1,::1,0.0.0.0" NO_PROXY="localhost,127.0.0.1,::1,0.0.0.0" $UVICORN_PATH app.main:app --host 0.0.0.0 --port 8001 --workers 1 > "$LOG_FILE" 2>&1 &
    RAG_PID=$!

    echo "✅ RAG Service已启动"
    echo "📄 进程ID: $RAG_PID"
    echo "📋 日志文件: $LOG_FILE"
    echo "🌐 服务地址: http://localhost:8001"
    echo "🛑 停止命令: kill $RAG_PID"

    # 保存PID
    echo "$RAG_PID" > rag_service.pid

    echo ""
    echo "🔍 查看实时日志: tail -f $LOG_FILE"
    echo "📊 查看API文档: http://localhost:8001/docs"
    echo "🛑 停止服务: ./stop_rag_service.sh"

    # 等待服务启动
    echo ""
    echo "⏳ 等待服务启动..."
    sleep 3

    # 健康检查
    for i in {1..10}; do
        if curl -s http://localhost:8001/api/health >/dev/null 2>&1; then
            echo "✅ RAG Service健康检查通过!"
            echo "🎯 服务已就绪，可以处理请求"
            break
        fi
        echo "⏳ 等待服务就绪... ($i/10)"
        sleep 2
    done

    # 显示初始几行日志
    echo ""
    echo "📋 初始日志输出:"
    tail -n 10 "$LOG_FILE" 2>/dev/null || echo "日志文件暂未生成"
fi

echo ""
echo "🎯 RAG Service功能:"
echo "   ✅ 文档向量化和存储"
echo "   ✅ 语义搜索和检索"
echo "   ✅ 上下文增强和RAG查询"
echo "   ✅ 系统初始化和Bootstrap"
echo "   ✅ 健康检查和监控"