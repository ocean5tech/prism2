#!/bin/bash
# 停止RSS监控服务的脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="$SCRIPT_DIR/rss_monitor.pid"

if [ -f "$PID_FILE" ]; then
    RSS_PID=$(cat "$PID_FILE")

    if ps -p $RSS_PID > /dev/null 2>&1; then
        echo "🛑 停止RSS监控服务 (PID: $RSS_PID)"
        kill $RSS_PID

        # 等待进程结束
        sleep 2

        if ps -p $RSS_PID > /dev/null 2>&1; then
            echo "⚠️ 进程未正常结束，强制终止"
            kill -9 $RSS_PID
        fi

        echo "✅ RSS监控已停止"
    else
        echo "⚠️ RSS监控进程不存在 (PID: $RSS_PID)"
    fi

    # 删除PID文件
    rm -f "$PID_FILE"
else
    echo "❌ 未找到PID文件，RSS监控可能未运行"
fi

# 检查是否还有遗留进程
RSS_PROCESSES=$(ps aux | grep real_rss_monitor.py | grep -v grep | wc -l)
if [ $RSS_PROCESSES -gt 0 ]; then
    echo "⚠️ 发现 $RSS_PROCESSES 个RSS监控进程，是否全部终止? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        pkill -f real_rss_monitor.py
        echo "✅ 所有RSS监控进程已终止"
    fi
fi