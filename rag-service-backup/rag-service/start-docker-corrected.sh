#!/bin/bash

echo "🚀 RAG Service Docker 正确启动脚本"
echo "使用现有共享基础设施 (prism2-postgres, prism2-redis, prism2-chromadb)"
echo "======================================================================="

# 检查Docker是否运行
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

echo "📋 Docker环境检查通过"

# 检查现有共享基础设施
echo "🔍 检查现有共享基础设施..."

# 检查ChromaDB
if ! podman ps --filter name=prism2-chromadb --filter status=running | grep -q chromadb; then
    echo "❌ prism2-chromadb容器未运行，请先启动"
    echo "启动命令: podman start prism2-chromadb"
    exit 1
fi

# 检查Redis
if ! podman exec prism2-redis redis-cli ping >/dev/null 2>&1; then
    echo "❌ prism2-redis容器未运行，请先启动"
    echo "启动命令: podman start prism2-redis"
    exit 1
fi

echo "✅ 现有共享基础设施检查通过"

# 停止现有RAG Service容器（如果有）
echo "🛑 停止现有RAG Service容器..."
docker stop rag-service-corrected 2>/dev/null || true
docker rm rag-service-corrected 2>/dev/null || true

# 构建并启动RAG Service容器
echo "🔄 构建并启动RAG Service..."
docker build -f Dockerfile.corrected -t rag-service-corrected .

# 启动容器，连接到现有基础设施
docker run -d \
  --name rag-service-corrected \
  --add-host host.docker.internal:host-gateway \
  -p 8001:8001 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/rss_data:/app/rss_data \
  -v $(pwd)/data:/app/data \
  rag-service-corrected

# 等待服务启动
echo "⏳ 等待服务启动（最多120秒）..."
timeout 120 bash -c '
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
    echo ""
    echo "🏗️ 使用现有共享基础设施:"
    echo "  - ChromaDB: http://localhost:8000 (prism2-chromadb)"
    echo "  - Redis: localhost:6379 (prism2-redis)"
    echo "  - PostgreSQL: localhost:5432 (prism2-postgres)"
    echo ""
    echo "📊 查看日志: docker logs -f rag-service-corrected"
    echo "🛑 停止服务: docker stop rag-service-corrected"
else
    echo "❌ RAG Service启动失败"
    echo "📋 查看日志:"
    docker logs rag-service-corrected
    exit 1
fi