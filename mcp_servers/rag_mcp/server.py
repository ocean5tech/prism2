#!/usr/bin/env python3
"""
RAG Enhanced MCP Server (Port 8008)

Provides intelligent document retrieval and context enhancement for financial analysis.
Integrates ChromaDB vector database and news data sources.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Sequence, Union
from datetime import datetime, timedelta

# MCP SDK imports
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
    CallToolRequest,
    ListToolsRequest,
    ListResourcesRequest,
    ReadResourceRequest
)

# Shared modules imports
import sys
import os
sys.path.append('/home/wyatt/prism2/mcp_servers/shared')

from config import config
from logger import get_logger, log_mcp_call
from database import data_manager

logger = get_logger("RAG-MCP")

# Initialize MCP server
server = Server("rag-mcp")

class RAGService:
    """RAG服务核心类 - 向量检索和上下文增强"""

    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.embedding_model = "all-MiniLM-L6-v2"  # 轻量级嵌入模型
        self._initialize_vector_db()

    def _initialize_vector_db(self):
        """初始化ChromaDB向量数据库"""
        try:
            import chromadb

            # 使用新的PersistentClient
            self.chroma_client = chromadb.PersistentClient(
                path="./chroma_data"
            )

            # 获取或创建集合
            self.collection = self.chroma_client.get_or_create_collection(
                name="financial_documents",
                metadata={"hnsw:space": "cosine"}
            )

            logger.info("ChromaDB向量数据库初始化成功")
            self._populate_sample_data()

        except Exception as e:
            logger.error(f"ChromaDB初始化失败: {e}")
            self.chroma_client = None
            self.collection = None

    def _populate_sample_data(self):
        """填充示例数据到向量数据库"""
        try:
            # 检查是否已有数据
            if self.collection.count() > 0:
                logger.info(f"向量数据库已有 {self.collection.count()} 条记录")
                return

            # 添加示例财经新闻和分析文档
            sample_documents = [
                {
                    "id": "news_001",
                    "content": "科创板公司688469最新财报显示营收同比增长15%，净利润实现扭亏为盈，主要受益于新产品市场表现强劲",
                    "metadata": {"type": "news", "stock_code": "688469", "date": "2024-09-20", "source": "财经日报"},
                },
                {
                    "id": "analysis_001",
                    "content": "从技术分析角度看，688469股价突破重要阻力位，成交量放大，显示多头力量增强，建议关注回调买入机会",
                    "metadata": {"type": "analysis", "stock_code": "688469", "analyst": "技术分析师", "date": "2024-09-21"},
                },
                {
                    "id": "industry_001",
                    "content": "新能源行业整体向好，政策支持力度加大，相关概念股有望受益，投资者可关注行业龙头企业",
                    "metadata": {"type": "industry", "industry": "新能源", "date": "2024-09-19", "source": "行业研究"},
                },
                {
                    "id": "market_001",
                    "content": "A股市场整体表现平稳，科创板活跃度较高，资金流向科技股，建议关注业绩确定性强的优质标的",
                    "metadata": {"type": "market", "market": "A股", "date": "2024-09-22", "source": "市场分析"},
                }
            ]

            # 批量添加文档到向量数据库
            documents = [doc["content"] for doc in sample_documents]
            metadatas = [doc["metadata"] for doc in sample_documents]
            ids = [doc["id"] for doc in sample_documents]

            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"成功添加 {len(sample_documents)} 条示例文档到向量数据库")

        except Exception as e:
            logger.error(f"填充示例数据失败: {e}")

    async def search_relevant_documents(self, query: str, n_results: int = 5, stock_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """搜索相关文档"""
        try:
            if not self.collection:
                return []

            # 构建查询条件
            where_conditions = {}
            if stock_code:
                where_conditions["stock_code"] = stock_code

            # 执行向量搜索
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_conditions if where_conditions else None,
                include=["documents", "metadatas", "distances"]
            )

            # 格式化结果
            documents = []
            if results["documents"] and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    documents.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "similarity": 1 - results["distances"][0][i] if results["distances"] else 0
                    })

            logger.info(f"RAG搜索找到 {len(documents)} 个相关文档")
            return documents

        except Exception as e:
            logger.error(f"RAG文档搜索失败: {e}")
            return []

    async def add_document(self, document_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """添加新文档到向量数据库"""
        try:
            if not self.collection:
                return False

            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[document_id]
            )

            logger.info(f"成功添加文档到RAG数据库: {document_id}")
            return True

        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False

# 初始化RAG服务
rag_service = RAGService()

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="search_financial_context",
            description="搜索与股票或财经主题相关的背景信息和上下文。当需要了解市场观点、行业动态、分析师观点时调用。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询，支持自然语言描述，如'688469最新动态'、'新能源行业前景'等"
                    },
                    "stock_code": {
                        "type": "string",
                        "description": "可选的股票代码，用于筛选特定股票相关的内容"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回结果数量，默认5个",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_news_sentiment",
            description="获取特定股票的新闻情感分析。分析最近的新闻报道情感倾向，为投资决策提供参考。",
            inputSchema={
                "type": "object",
                "properties": {
                    "stock_code": {
                        "type": "string",
                        "description": "股票代码，如'688469'"
                    },
                    "days": {
                        "type": "integer",
                        "description": "分析最近多少天的新闻，默认7天",
                        "default": 7
                    }
                },
                "required": ["stock_code"]
            }
        ),
        Tool(
            name="generate_market_insight",
            description="基于RAG检索结果生成市场洞察报告。结合多个数据源提供综合性的市场分析和投资建议。",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "分析主题，如'科创板投资机会'、'新能源板块展望'等"
                    },
                    "stock_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "相关股票代码列表，可选"
                    },
                    "analysis_depth": {
                        "type": "string",
                        "enum": ["brief", "detailed", "comprehensive"],
                        "description": "分析深度：简要、详细、全面",
                        "default": "detailed"
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="add_knowledge_document",
            description="添加新的知识文档到RAG系统。用于扩充知识库内容，支持新闻、研报、分析文章等。",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "文档标题"
                    },
                    "content": {
                        "type": "string",
                        "description": "文档内容"
                    },
                    "doc_type": {
                        "type": "string",
                        "enum": ["news", "analysis", "research", "industry", "market"],
                        "description": "文档类型"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "文档元数据，如股票代码、日期、来源等",
                        "properties": {
                            "stock_code": {"type": "string"},
                            "date": {"type": "string"},
                            "source": {"type": "string"},
                            "industry": {"type": "string"}
                        }
                    }
                },
                "required": ["title", "content", "doc_type"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> Sequence[TextContent]:
    """处理工具调用请求"""

    log_mcp_call(logger, name, arguments)

    try:
        if name == "search_financial_context":
            return await _handle_search_financial_context(arguments)
        elif name == "get_news_sentiment":
            return await _handle_get_news_sentiment(arguments)
        elif name == "generate_market_insight":
            return await _handle_generate_market_insight(arguments)
        elif name == "add_knowledge_document":
            return await _handle_add_knowledge_document(arguments)
        else:
            error_msg = f"未知的工具: {name}"
            log_mcp_call(logger, name, arguments, error=error_msg)
            return [TextContent(type="text", text=f"❌ 错误: {error_msg}")]

    except Exception as e:
        error_msg = f"工具调用异常: {str(e)}"
        log_mcp_call(logger, name, arguments, error=error_msg)
        return [TextContent(type="text", text=f"❌ 错误: {error_msg}")]

async def _handle_search_financial_context(arguments: dict) -> Sequence[TextContent]:
    """处理财经上下文搜索"""

    query = arguments.get("query", "")
    stock_code = arguments.get("stock_code")
    max_results = arguments.get("max_results", 5)

    if not query.strip():
        return [TextContent(type="text", text="❌ 搜索查询不能为空")]

    # 执行RAG搜索
    documents = await rag_service.search_relevant_documents(
        query=query,
        n_results=max_results,
        stock_code=stock_code
    )

    if not documents:
        return [TextContent(type="text", text=f"🔍 未找到与'{query}'相关的背景信息")]

    # 格式化搜索结果
    result_text = f"🔍 财经背景搜索: '{query}'\n"
    if stock_code:
        result_text += f"📊 股票筛选: {stock_code}\n"
    result_text += f"📝 找到 {len(documents)} 个相关结果:\n\n"

    for i, doc in enumerate(documents, 1):
        metadata = doc.get("metadata", {})
        similarity = doc.get("similarity", 0)

        result_text += f"### 📄 结果 {i} (相关度: {similarity:.3f})\n"
        result_text += f"**内容**: {doc['content']}\n"

        if metadata.get("type"):
            result_text += f"**类型**: {metadata['type']}\n"
        if metadata.get("date"):
            result_text += f"**日期**: {metadata['date']}\n"
        if metadata.get("source"):
            result_text += f"**来源**: {metadata['source']}\n"
        if metadata.get("stock_code"):
            result_text += f"**相关股票**: {metadata['stock_code']}\n"

        result_text += "\n---\n\n"

    result_text += f"💡 **使用建议**: 以上信息可为投资分析提供背景支持，请结合实时数据综合判断。"

    log_mcp_call(logger, "search_financial_context", arguments, {"results": len(documents)})
    return [TextContent(type="text", text=result_text)]

async def _handle_get_news_sentiment(arguments: dict) -> Sequence[TextContent]:
    """处理新闻情感分析"""

    stock_code = arguments.get("stock_code", "")
    days = arguments.get("days", 7)

    if not stock_code:
        return [TextContent(type="text", text="❌ 股票代码不能为空")]

    # 搜索相关新闻
    news_query = f"{stock_code} 新闻 财报 业绩"
    documents = await rag_service.search_relevant_documents(
        query=news_query,
        n_results=10,
        stock_code=stock_code
    )

    # 模拟情感分析（实际应用中可集成专业的情感分析API）
    positive_count = 0
    negative_count = 0
    neutral_count = 0

    sentiment_details = []

    for doc in documents:
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})

        # 简单的情感分析逻辑
        positive_words = ["增长", "盈利", "突破", "强劲", "利好", "上涨", "买入", "推荐"]
        negative_words = ["下跌", "亏损", "下滑", "风险", "调整", "卖出", "谨慎", "压力"]

        pos_score = sum(1 for word in positive_words if word in content)
        neg_score = sum(1 for word in negative_words if word in content)

        if pos_score > neg_score:
            sentiment = "积极"
            positive_count += 1
        elif neg_score > pos_score:
            sentiment = "消极"
            negative_count += 1
        else:
            sentiment = "中性"
            neutral_count += 1

        sentiment_details.append({
            "content": content[:100] + "..." if len(content) > 100 else content,
            "sentiment": sentiment,
            "date": metadata.get("date", "未知"),
            "source": metadata.get("source", "未知")
        })

    # 计算总体情感
    total = len(documents)
    if total == 0:
        return [TextContent(type="text", text=f"📰 {stock_code} 暂无相关新闻数据")]

    positive_pct = (positive_count / total) * 100
    negative_pct = (negative_count / total) * 100
    neutral_pct = (neutral_count / total) * 100

    # 生成情感分析报告
    result_text = f"📰 {stock_code} 新闻情感分析报告\n"
    result_text += f"🗓️ 分析期间: 最近{days}天\n"
    result_text += f"📊 分析样本: {total}条相关信息\n\n"

    result_text += f"### 📈 总体情感倾向\n"
    result_text += f"🟢 积极: {positive_count}条 ({positive_pct:.1f}%)\n"
    result_text += f"🔴 消极: {negative_count}条 ({negative_pct:.1f}%)\n"
    result_text += f"🟡 中性: {neutral_count}条 ({neutral_pct:.1f}%)\n\n"

    # 判断总体情感
    if positive_pct > 50:
        overall_sentiment = "总体积极 📈"
    elif negative_pct > 50:
        overall_sentiment = "总体消极 📉"
    else:
        overall_sentiment = "总体中性 ➡️"

    result_text += f"**市场情感**: {overall_sentiment}\n\n"

    # 详细情感分析
    result_text += f"### 📝 主要信息摘要\n"
    for i, item in enumerate(sentiment_details[:5], 1):
        emoji = "🟢" if item["sentiment"] == "积极" else "🔴" if item["sentiment"] == "消极" else "🟡"
        result_text += f"{i}. {emoji} **{item['sentiment']}** | {item['date']} | {item['source']}\n"
        result_text += f"   {item['content']}\n\n"

    result_text += f"💡 **投资参考**: 情感分析仅供参考，请结合基本面和技术面综合判断。"

    log_mcp_call(logger, "get_news_sentiment", arguments, {
        "total_news": total,
        "positive_pct": positive_pct,
        "negative_pct": negative_pct
    })

    return [TextContent(type="text", text=result_text)]

async def _handle_generate_market_insight(arguments: dict) -> Sequence[TextContent]:
    """生成市场洞察报告"""

    topic = arguments.get("topic", "")
    stock_codes = arguments.get("stock_codes", [])
    analysis_depth = arguments.get("analysis_depth", "detailed")

    if not topic.strip():
        return [TextContent(type="text", text="❌ 分析主题不能为空")]

    # 基于主题搜索相关文档
    documents = await rag_service.search_relevant_documents(
        query=topic,
        n_results=10
    )

    # 如果指定了股票代码，也搜索相关信息
    stock_documents = []
    if stock_codes:
        for stock_code in stock_codes:
            stock_docs = await rag_service.search_relevant_documents(
                query=f"{stock_code} 分析 投资",
                n_results=5,
                stock_code=stock_code
            )
            stock_documents.extend(stock_docs)

    # 合并所有相关文档
    all_documents = documents + stock_documents

    if not all_documents:
        return [TextContent(type="text", text=f"📊 未找到与'{topic}'相关的市场信息")]

    # 生成洞察报告
    result_text = f"📊 市场洞察报告: {topic}\n"
    result_text += f"🗓️ 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    result_text += f"📝 分析深度: {analysis_depth}\n"
    if stock_codes:
        result_text += f"🎯 关注股票: {', '.join(stock_codes)}\n"
    result_text += f"📚 数据来源: {len(all_documents)}条相关信息\n\n"

    # 分析不同类型的信息
    news_docs = [d for d in all_documents if d.get("metadata", {}).get("type") == "news"]
    analysis_docs = [d for d in all_documents if d.get("metadata", {}).get("type") == "analysis"]
    industry_docs = [d for d in all_documents if d.get("metadata", {}).get("type") == "industry"]
    market_docs = [d for d in all_documents if d.get("metadata", {}).get("type") == "market"]

    if analysis_depth in ["detailed", "comprehensive"]:
        # 详细分析
        if news_docs:
            result_text += f"### 📰 新闻动态 ({len(news_docs)}条)\n"
            for doc in news_docs[:3]:
                result_text += f"• {doc['content'][:80]}...\n"
            result_text += "\n"

        if analysis_docs:
            result_text += f"### 📈 分析观点 ({len(analysis_docs)}条)\n"
            for doc in analysis_docs[:3]:
                result_text += f"• {doc['content'][:80]}...\n"
            result_text += "\n"

        if industry_docs:
            result_text += f"### 🏭 行业前景 ({len(industry_docs)}条)\n"
            for doc in industry_docs[:2]:
                result_text += f"• {doc['content'][:80]}...\n"
            result_text += "\n"

        if market_docs:
            result_text += f"### 🌐 市场环境 ({len(market_docs)}条)\n"
            for doc in market_docs[:2]:
                result_text += f"• {doc['content'][:80]}...\n"
            result_text += "\n"

    # 生成综合洞察
    result_text += f"### 💡 综合洞察\n"

    # 简单的关键词分析
    all_content = " ".join([doc.get("content", "") for doc in all_documents])
    positive_indicators = ["增长", "利好", "机会", "突破", "强劲", "上涨"]
    negative_indicators = ["下跌", "风险", "压力", "调整", "谨慎", "挑战"]

    positive_signals = sum(1 for indicator in positive_indicators if indicator in all_content)
    negative_signals = sum(1 for indicator in negative_indicators if indicator in all_content)

    if positive_signals > negative_signals:
        market_outlook = "偏向乐观 📈"
        suggestion = "可关注相关投资机会，但需注意风险控制"
    elif negative_signals > positive_signals:
        market_outlook = "偏向谨慎 📉"
        suggestion = "建议保持谨慎，等待更明确的信号"
    else:
        market_outlook = "中性观点 ➡️"
        suggestion = "建议持续关注市场变化，灵活应对"

    result_text += f"**市场展望**: {market_outlook}\n"
    result_text += f"**投资建议**: {suggestion}\n\n"

    if analysis_depth == "comprehensive":
        # 全面分析 - 添加更多细节
        result_text += f"### 📊 数据统计\n"
        result_text += f"• 积极信号数量: {positive_signals}\n"
        result_text += f"• 消极信号数量: {negative_signals}\n"
        result_text += f"• 信息覆盖范围: 新闻({len(news_docs)})、分析({len(analysis_docs)})、行业({len(industry_docs)})、市场({len(market_docs)})\n\n"

    result_text += f"⚠️ **免责声明**: 本报告基于RAG检索的信息生成，仅供参考，投资有风险，决策需谨慎。"

    log_mcp_call(logger, "generate_market_insight", arguments, {
        "documents_analyzed": len(all_documents),
        "market_outlook": market_outlook
    })

    return [TextContent(type="text", text=result_text)]

async def _handle_add_knowledge_document(arguments: dict) -> Sequence[TextContent]:
    """添加知识文档到RAG系统"""

    title = arguments.get("title", "")
    content = arguments.get("content", "")
    doc_type = arguments.get("doc_type", "")
    metadata = arguments.get("metadata", {})

    if not all([title, content, doc_type]):
        return [TextContent(type="text", text="❌ 标题、内容和文档类型都不能为空")]

    # 生成文档ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    document_id = f"{doc_type}_{timestamp}"

    # 准备元数据
    doc_metadata = {
        "title": title,
        "type": doc_type,
        "created_at": datetime.now().isoformat(),
        **metadata
    }

    # 添加到RAG系统
    success = await rag_service.add_document(
        document_id=document_id,
        content=content,
        metadata=doc_metadata
    )

    if success:
        result_text = f"✅ 成功添加知识文档到RAG系统\n\n"
        result_text += f"📄 **文档标题**: {title}\n"
        result_text += f"🏷️ **文档类型**: {doc_type}\n"
        result_text += f"🆔 **文档ID**: {document_id}\n"
        result_text += f"📝 **内容长度**: {len(content)} 字符\n"

        if metadata:
            result_text += f"📋 **附加信息**:\n"
            for key, value in metadata.items():
                result_text += f"   • {key}: {value}\n"

        result_text += f"\n💡 文档已索引，可通过搜索功能检索使用。"

        log_mcp_call(logger, "add_knowledge_document", arguments, {"document_id": document_id})
    else:
        result_text = f"❌ 添加文档失败，请检查系统状态或稍后重试。"
        log_mcp_call(logger, "add_knowledge_document", arguments, error="添加文档失败")

    return [TextContent(type="text", text=result_text)]

async def main():
    """主函数 - 启动MCP服务器"""
    logger.info("启动 RAG Enhanced MCP Server (端口8008)")

    # 运行MCP服务器
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="rag-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())