#!/bin/bash

# 停止RAG Service FastAPI主程序

echo "🛑 停止RAG Service..."

WORK_DIR="/home/wyatt/prism2/rag-service"
cd "$WORK_DIR" || {
    echo "❌ 无法进入工作目录: $WORK_DIR"
    exit 1
}

# 从PID文件读取进程ID
if [[ -f "rag_service.pid" ]]; then
    RAG_PID=$(cat rag_service.pid)
    echo "📄 找到PID文件: $RAG_PID"

    # 检查进程是否还在运行
    if ps -p "$RAG_PID" > /dev/null 2>&1; then
        echo "🔄 停止进程 $RAG_PID..."
        kill "$RAG_PID"

        # 等待进程结束
        for i in {1..10}; do
            if ! ps -p "$RAG_PID" > /dev/null 2>&1; then
                echo "✅ 进程已成功停止"
                break
            fi
            echo "⏳ 等待进程结束... ($i/10)"
            sleep 1
        done

        # 如果进程仍在运行，强制结束
        if ps -p "$RAG_PID" > /dev/null 2>&1; then
            echo "⚠️ 强制结束进程..."
            kill -9 "$RAG_PID"
            sleep 1
            if ps -p "$RAG_PID" > /dev/null 2>&1; then
                echo "❌ 无法停止进程 $RAG_PID"
                exit 1
            else
                echo "✅ 进程已强制停止"
            fi
        fi
    else
        echo "⚠️ 进程 $RAG_PID 已不存在"
    fi

    # 删除PID文件
    rm -f rag_service.pid
    echo "🗑️ 已清理PID文件"
else
    echo "⚠️ 未找到PID文件"
fi

# 查找所有可能的RAG Service进程并停止
echo "🔍 查找其他RAG Service进程..."
RAG_PROCS=$(pgrep -f "uvicorn.*app.main:app.*8001")

if [[ -n "$RAG_PROCS" ]]; then
    echo "📋 找到RAG进程: $RAG_PROCS"
    echo "$RAG_PROCS" | while read -r pid; do
        echo "🛑 停止进程: $pid"
        kill "$pid" 2>/dev/null
    done

    sleep 2

    # 检查是否还有残留进程
    REMAINING_PROCS=$(pgrep -f "uvicorn.*app.main:app.*8001")
    if [[ -n "$REMAINING_PROCS" ]]; then
        echo "⚠️ 强制停止残留进程: $REMAINING_PROCS"
        echo "$REMAINING_PROCS" | while read -r pid; do
            kill -9 "$pid" 2>/dev/null
        done
    fi
fi

# 检查端口8001是否释放
echo "🔍 检查端口8001状态..."
if netstat -tuln | grep ":8001" >/dev/null 2>&1; then
    echo "⚠️ 端口8001仍被占用"
    echo "可能需要等待几秒钟端口完全释放"
else
    echo "✅ 端口8001已释放"
fi

# 显示当前状态
CURRENT_PROCS=$(pgrep -f "uvicorn.*app.main:app.*8001")
if [[ -z "$CURRENT_PROCS" ]]; then
    echo "✅ 所有RAG Service进程已停止"
else
    echo "⚠️ 仍有进程在运行: $CURRENT_PROCS"
    exit 1
fi

echo ""
echo "📊 最新日志文件:"
if [[ -d "logs" ]]; then
    ls -la logs/rag_service_*.log | tail -3
else
    echo "   无日志目录"
fi

echo ""
echo "🎯 RAG Service已完全停止"