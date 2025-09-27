#!/bin/bash

echo "🚀 RAG Service Docker 一键启动脚本"
echo "=================================="

# 检查Docker是否运行
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 检查docker-compose是否可用
if ! command -v docker-compose >/dev/null 2>&1; then
    echo "❌ docker-compose未安装"
    exit 1
fi

echo "📋 Docker环境检查通过"

# 停止现有容器（如果有）
echo "🛑 停止现有RAG Service容器..."
docker-compose -f docker-compose.rag.yml down

# 构建并启动所有服务
echo "🔄 构建并启动RAG Service..."
docker-compose -f docker-compose.rag.yml up --build -d

# 等待服务启动
echo "⏳ 等待服务启动（最多180秒）..."
timeout 180 bash -c '
until curl -f http://localhost:8001/api/health >/dev/null 2>&1; do
  echo "等待RAG Service启动..."
  sleep 5
done
'

if curl -f http://localhost:8001/api/health >/dev/null 2>&1; then
    echo "✅ RAG Service启动成功！"
    echo ""
    echo "🎯 服务地址:"
    echo "  - RAG Service API: http://localhost:8001"
    echo "  - API文档: http://localhost:8001/docs"
    echo "  - ChromaDB: http://localhost:8000"
    echo "  - PostgreSQL: localhost:5432 (raguser/ragpass123)"
    echo "  - Redis: localhost:6379"
    echo ""
    echo "📊 查看日志: docker-compose -f docker-compose.rag.yml logs -f"
    echo "🛑 停止服务: docker-compose -f docker-compose.rag.yml down"
else
    echo "❌ RAG Service启动失败"
    echo "📋 查看日志:"
    docker-compose -f docker-compose.rag.yml logs rag-service
    exit 1
fi