#!/bin/bash

# 启动隔离的RSS监控服务（带翻译功能）
# 新架构：RSS收集 -> 翻译服务 -> JSON存储 -> RAG消费

echo "🚀 启动隔离RSS监控服务..."

# 检查工作目录
WORK_DIR="/home/wyatt/prism2/rag-service"
cd "$WORK_DIR" || {
    echo "❌ 无法进入工作目录: $WORK_DIR"
    exit 1
}

echo "📁 工作目录: $WORK_DIR"

# 检查必要文件
REQUIRED_FILES=(
    "translation_service.py"
    "isolated_rss_monitor.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ 缺少必要文件: $file"
        exit 1
    fi
done

echo "📄 必要文件检查通过"

# 创建数据目录
mkdir -p rss_data logs
echo "📂 数据目录已创建"

# 检查Python依赖
echo "🔍 检查Python依赖..."
python3 -c "
import sys
try:
    import aiohttp, feedparser, beautifulsoup4, langdetect
    print('✅ 核心依赖OK')
except ImportError as e:
    print(f'❌ 缺少依赖: {e}')
    sys.exit(1)
"

if [[ $? -ne 0 ]]; then
    echo "📦 安装缺少的依赖..."
    pip install aiohttp feedparser beautifulsoup4 langdetect --break-system-packages
fi

# 启动服务
echo "⏰ 监控间隔: ${1:-15}分钟"
echo "🌐 翻译服务: 内置隔离模式"
echo "💾 数据存储: JSON格式 -> rss_data/"

LOG_FILE="logs/isolated_rss_$(date +%Y%m%d_%H%M%S).log"

if [[ "$1" == "once" ]]; then
    echo "🔄 运行单次收集..."
    python3 isolated_rss_monitor.py once 2>&1 | tee "$LOG_FILE"
    echo "✅ 单次收集完成"
elif [[ "$1" == "test" ]]; then
    echo "🧪 运行测试数据生成..."
    python3 test_rss_data.py 2>&1 | tee "$LOG_FILE"
    echo "✅ 测试数据生成完成"
else
    echo "🔄 启动连续监控..."
    INTERVAL=${1:-15}

    # 后台运行
    nohup python3 isolated_rss_monitor.py continuous "$INTERVAL" > "$LOG_FILE" 2>&1 &
    RSS_PID=$!

    echo "✅ RSS监控已启动"
    echo "📄 进程ID: $RSS_PID"
    echo "📋 日志文件: $LOG_FILE"
    echo "🛑 停止命令: kill $RSS_PID"

    # 保存PID
    echo "$RSS_PID" > rss_monitor.pid

    echo ""
    echo "🔍 查看实时日志: tail -f $LOG_FILE"
    echo "📊 查看数据目录: ls -la rss_data/"
    echo "🛑 停止服务: ./stop_isolated_rss.sh"

    # 显示初始几行日志
    echo ""
    echo "📋 初始日志输出:"
    sleep 2
    tail -n 10 "$LOG_FILE" 2>/dev/null || echo "日志文件暂未生成"
fi

echo ""
echo "🎯 新架构优势:"
echo "   ✅ 翻译服务完全隔离"
echo "   ✅ 不依赖ChromaDB连接"
echo "   ✅ JSON格式便于调试"
echo "   ✅ 支持单次和连续模式"
echo "   ✅ 独立的错误处理"