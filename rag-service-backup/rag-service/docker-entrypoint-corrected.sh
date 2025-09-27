#!/bin/bash
set -e

echo "🚀 启动RAG Service Docker容器（使用现有共享基础设施）..."

# 等待现有ChromaDB连接
echo "⏳ 等待现有ChromaDB连接..."
until curl -f http://host.docker.internal:8000/api/v1/heartbeat; do
  echo "ChromaDB未就绪，等待5秒..."
  sleep 5
done
echo "✅ ChromaDB连接成功"

# 等待现有Redis连接
echo "⏳ 等待现有Redis连接..."
until nc -z host.docker.internal 6379; do
  echo "Redis未就绪，等待5秒..."
  sleep 5
done
echo "✅ Redis连接成功"

# 创建必要目录
mkdir -p /app/logs /app/rss_data /app/data

echo "🎯 所有共享基础设施就绪，启动RAG Service..."

# 执行传入的命令
exec "$@"