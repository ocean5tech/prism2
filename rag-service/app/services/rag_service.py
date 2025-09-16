import logging
import time
from typing import List, Optional, Dict, Any
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.models.requests import RAGSearchRequest, ContextEnhancementRequest
from app.models.responses import RAGSearchResponse, RAGContextResponse, DocumentMatch

logger = logging.getLogger(__name__)


class RAGService:
    """RAG核心服务 - 检索增强生成核心逻辑"""

    def __init__(self):
        self.embedding_service = embedding_service
        self.vector_service = vector_service

    async def semantic_search(self, request: RAGSearchRequest) -> RAGSearchResponse:
        """语义搜索"""
        try:
            logger.info(f"执行语义搜索: {request.query[:50]}...")
            start_time = time.time()

            # 1. 生成查询向量
            query_embedding = self.embedding_service.embed_text(request.query)
            embed_time = time.time() - start_time

            # 2. 构建过滤条件
            filters = self._build_filters(request.stock_code, request.filters)

            # 3. 执行向量搜索
            search_start = time.time()
            matches = self.vector_service.search_similar_documents(
                query_embedding=query_embedding,
                limit=request.limit,
                similarity_threshold=request.similarity_threshold,
                filters=filters
            )
            search_time = time.time() - search_start

            total_time = time.time() - start_time

            logger.info(f"语义搜索完成，总耗时: {total_time:.3f}秒 (embedding: {embed_time:.3f}s, search: {search_time:.3f}s)")

            # 4. 获取集合统计信息
            stats = self.vector_service.get_collection_stats()
            total_documents = stats.get("document_count", 0)

            return RAGSearchResponse(
                results=matches,
                query_embedding=query_embedding,
                search_time=total_time,
                total_documents=total_documents
            )

        except Exception as e:
            logger.error(f"语义搜索失败: {str(e)}")
            raise

    async def hybrid_search(self, request: RAGSearchRequest) -> RAGSearchResponse:
        """混合搜索 (语义 + 关键词)"""
        try:
            logger.info(f"执行混合搜索: {request.query[:50]}...")

            # 先执行语义搜索
            semantic_results = await self.semantic_search(request)

            # TODO: 添加关键词搜索逻辑
            # 目前返回语义搜索结果，后续可扩展关键词匹配

            return semantic_results

        except Exception as e:
            logger.error(f"混合搜索失败: {str(e)}")
            raise

    async def enhance_context(self, request: ContextEnhancementRequest) -> RAGContextResponse:
        """生成增强上下文"""
        try:
            logger.info(f"生成增强上下文: {request.query[:50]}...")
            start_time = time.time()

            # 1. 执行语义搜索获取相关文档
            search_request = RAGSearchRequest(
                query=request.query,
                stock_code=request.stock_code,
                search_type="semantic",
                limit=10,  # 获取更多文档用于上下文组装
                similarity_threshold=0.6  # 降低阈值获取更多候选
            )

            search_results = await self.semantic_search(search_request)

            # 2. 智能组装上下文
            context, sources, relevance_score = self._assemble_context(
                search_results.results,
                request.max_context_length,
                request.context_type
            )

            # 3. 计算token数量（简单估算）
            token_count = len(context.split())

            total_time = time.time() - start_time
            logger.info(f"上下文增强完成，耗时: {total_time:.3f}秒, 上下文长度: {len(context)}字符")

            return RAGContextResponse(
                context=context,
                sources=sources,
                relevance_score=relevance_score,
                token_count=token_count
            )

        except Exception as e:
            logger.error(f"上下文增强失败: {str(e)}")
            raise

    def _build_filters(self, stock_code: Optional[str], custom_filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """构建搜索过滤条件"""
        filters = {}

        # 添加股票代码过滤
        if stock_code:
            filters["stock_code"] = stock_code

        # 合并自定义过滤条件
        if custom_filters:
            filters.update(custom_filters)

        return filters if filters else None

    def _assemble_context(
        self,
        matches: List[DocumentMatch],
        max_length: int,
        context_type: str
    ) -> tuple[str, List[str], float]:
        """智能组装上下文"""
        try:
            if not matches:
                return "", [], 0.0

            # 按相似度排序
            sorted_matches = sorted(matches, key=lambda x: x.similarity_score, reverse=True)

            context_parts = []
            sources = []
            current_length = 0
            total_relevance = 0.0

            for match in sorted_matches:
                # 估算添加这个文档片段后的长度
                content_preview = self._format_document_content(match, context_type)
                estimated_length = current_length + len(content_preview) + 50  # 额外50字符用于格式化

                # 检查是否超过长度限制
                if estimated_length > max_length and context_parts:
                    break

                context_parts.append(content_preview)
                sources.append(match.document_id)
                current_length = estimated_length
                total_relevance += match.similarity_score

            # 组装最终上下文
            context = self._format_final_context(context_parts, context_type)

            # 计算平均相关性
            avg_relevance = total_relevance / len(sources) if sources else 0.0

            return context, sources, avg_relevance

        except Exception as e:
            logger.error(f"上下文组装失败: {str(e)}")
            return "", [], 0.0

    def _format_document_content(self, match: DocumentMatch, context_type: str) -> str:
        """格式化文档内容"""
        try:
            metadata = match.metadata
            content = match.content

            # 根据上下文类型格式化
            if context_type == "investment":
                # 投资分析上下文
                doc_type = metadata.get("doc_type", "未知")
                source = metadata.get("source", "未知来源")
                publish_time = metadata.get("publish_time", "")

                formatted = f"【{doc_type}】"
                if publish_time:
                    formatted += f"({publish_time}) "
                formatted += f"{content} (来源: {source})"

            else:
                # 通用格式
                formatted = content

            return formatted

        except Exception as e:
            logger.warning(f"文档内容格式化失败: {str(e)}")
            return match.content

    def _format_final_context(self, context_parts: List[str], context_type: str) -> str:
        """格式化最终上下文"""
        if not context_parts:
            return ""

        if context_type == "investment":
            # 投资分析上下文格式
            header = "以下是相关的市场信息和分析资料：\n\n"
            content = "\n\n".join(context_parts)
            footer = "\n\n以上信息可用于投资分析参考。"

            return header + content + footer

        else:
            # 通用格式
            return "\n\n".join(context_parts)


# 创建全局实例
rag_service = RAGService()