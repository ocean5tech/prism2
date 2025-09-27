#!/bin/bash

# 停止隔离的RSS监控服务

echo "🛑 停止隔离RSS监控服务..."

WORK_DIR="/home/wyatt/prism2/rag-service"
cd "$WORK_DIR" || {
    echo "❌ 无法进入工作目录: $WORK_DIR"
    exit 1
}

# 从PID文件读取进程ID
if [[ -f "rss_monitor.pid" ]]; then
    RSS_PID=$(cat rss_monitor.pid)
    echo "📄 找到PID文件: $RSS_PID"

    # 检查进程是否还在运行
    if ps -p "$RSS_PID" > /dev/null 2>&1; then
        echo "🔄 停止进程 $RSS_PID..."
        kill "$RSS_PID"

        # 等待进程结束
        for i in {1..10}; do
            if ! ps -p "$RSS_PID" > /dev/null 2>&1; then
                echo "✅ 进程已成功停止"
                break
            fi
            echo "⏳ 等待进程结束... ($i/10)"
            sleep 1
        done

        # 如果进程仍在运行，强制结束
        if ps -p "$RSS_PID" > /dev/null 2>&1; then
            echo "⚠️ 强制结束进程..."
            kill -9 "$RSS_PID"
            sleep 1
            if ps -p "$RSS_PID" > /dev/null 2>&1; then
                echo "❌ 无法停止进程 $RSS_PID"
                exit 1
            else
                echo "✅ 进程已强制停止"
            fi
        fi
    else
        echo "⚠️ 进程 $RSS_PID 已不存在"
    fi

    # 删除PID文件
    rm -f rss_monitor.pid
    echo "🗑️ 已清理PID文件"
else
    echo "⚠️ 未找到PID文件"
fi

# 查找所有可能的RSS监控进程并停止
echo "🔍 查找其他RSS监控进程..."
RSS_PROCS=$(pgrep -f "isolated_rss_monitor.py")

if [[ -n "$RSS_PROCS" ]]; then
    echo "📋 找到RSS进程: $RSS_PROCS"
    echo "$RSS_PROCS" | while read -r pid; do
        echo "🛑 停止进程: $pid"
        kill "$pid" 2>/dev/null
    done

    sleep 2

    # 检查是否还有残留进程
    REMAINING_PROCS=$(pgrep -f "isolated_rss_monitor.py")
    if [[ -n "$REMAINING_PROCS" ]]; then
        echo "⚠️ 强制停止残留进程: $REMAINING_PROCS"
        echo "$REMAINING_PROCS" | while read -r pid; do
            kill -9 "$pid" 2>/dev/null
        done
    fi
fi

# 显示当前状态
CURRENT_PROCS=$(pgrep -f "isolated_rss_monitor.py")
if [[ -z "$CURRENT_PROCS" ]]; then
    echo "✅ 所有RSS监控进程已停止"
else
    echo "⚠️ 仍有进程在运行: $CURRENT_PROCS"
    exit 1
fi

echo ""
echo "📊 最新数据文件:"
if [[ -d "rss_data" ]]; then
    ls -la rss_data/ | tail -5
else
    echo "   无数据目录"
fi

echo ""
echo "📋 最新日志文件:"
if [[ -d "logs" ]]; then
    ls -la logs/ | tail -3
else
    echo "   无日志目录"
fi

echo ""
echo "🎯 服务已完全停止"