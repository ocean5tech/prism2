#!/bin/bash
# 启动真实RSS监控服务的脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 激活虚拟环境
source rag_env/bin/activate

# 启动RSS监控（后台运行）
echo "🚀 启动真实RSS监控服务..."
echo "📁 工作目录: $SCRIPT_DIR"
echo "⏰ 监控间隔: 15分钟"
echo "📡 数据源: Bloomberg, Thomson Reuters, 和讯等"

# 创建日志文件
LOG_FILE="$SCRIPT_DIR/logs/rss_monitor.log"
mkdir -p "$SCRIPT_DIR/logs"

# 后台启动监控
nohup python3 real_rss_monitor.py >> "$LOG_FILE" 2>&1 &

# 获取进程ID
RSS_PID=$!
echo "✅ RSS监控已启动"
echo "📄 进程ID: $RSS_PID"
echo "📋 日志文件: $LOG_FILE"
echo "🛑 停止命令: kill $RSS_PID"

# 保存PID到文件
echo $RSS_PID > "$SCRIPT_DIR/rss_monitor.pid"

echo ""
echo "🔍 查看实时日志: tail -f $LOG_FILE"
echo "📊 查看进程状态: ps aux | grep $RSS_PID"