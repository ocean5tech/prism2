#!/bin/bash
set -e

echo "🚀 启动RAG Service Docker容器..."

# 等待数据库连接
echo "⏳ 等待PostgreSQL连接..."
until pg_isready -h postgres -p 5432 -U raguser; do
  echo "PostgreSQL未就绪，等待5秒..."
  sleep 5
done
echo "✅ PostgreSQL连接成功"

# 等待Redis连接
echo "⏳ 等待Redis连接..."
until nc -z redis 6379; do
  echo "Redis未就绪，等待5秒..."
  sleep 5
done
echo "✅ Redis连接成功"

# 等待ChromaDB连接
echo "⏳ 等待ChromaDB连接..."
until curl -f http://chromadb:8000/api/v1/heartbeat; do
  echo "ChromaDB未就绪，等待5秒..."
  sleep 5
done
echo "✅ ChromaDB连接成功"

# 创建必要目录
mkdir -p /app/logs /app/rss_data /app/data

echo "🎯 所有依赖服务就绪，启动RAG Service..."

# 执行传入的命令
exec "$@"