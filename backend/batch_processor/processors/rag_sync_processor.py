#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG同步处理器
将批处理获取的数据自动同步到RAG系统
"""
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import json

from ..config.batch_config import config
from ..services.version_manager import VersionManager
from ..services.data_vectorizer import DataVectorizer

logger = logging.getLogger(__name__)

class RAGSyncProcessor:
    """批处理数据RAG同步处理器"""

    def __init__(self):
        self.db_config = config.database_config
        self.version_manager = VersionManager()
        self.data_vectorizer = DataVectorizer()
        self.rag_service = None
        self.embedding_service = None
        self.vector_service = None

        # 初始化RAG服务
        self._init_rag_services()

        logger.info("RAG同步处理器初始化完成")

    def _init_rag_services(self):
        """初始化RAG相关服务"""
        try:
            # 尝试导入RAG服务
            import sys
            import os

            # 添加RAG服务路径
            rag_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app')
            if rag_path not in sys.path:
                sys.path.append(rag_path)

            from services.rag_service import RAGService
            from services.embedding_service import EmbeddingService
            from services.vector_service import VectorService

            self.rag_service = RAGService()
            self.embedding_service = EmbeddingService()
            self.vector_service = VectorService()

            logger.info("RAG服务初始化成功")

        except ImportError as e:
            logger.warning(f"RAG服务导入失败，将使用模拟模式: {e}")
            self.rag_service = None
            self.embedding_service = None
            self.vector_service = None

    def _get_connection(self):
        """获取数据库连接"""
        if 'url' in self.db_config:
            return psycopg2.connect(self.db_config['url'])
        else:
            return psycopg2.connect(**self.db_config)

    async def sync_batch_data_to_rag(self, stock_codes: List[str], data_types: List[str], force_refresh: bool = False) -> Dict[str, Any]:
        """
        批量同步数据到RAG

        Args:
            stock_codes: 股票代码列表
            data_types: 数据类型列表
            force_refresh: 是否强制刷新

        Returns:
            同步结果统计
        """
        start_time = time.time()
        result = {
            "total_stocks": len(stock_codes),
            "total_data_types": len(data_types),
            "processed_items": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "skipped_syncs": 0,
            "new_versions_created": 0,
            "versions_activated": 0,
            "failed_items": [],
            "processing_time": 0,
            "start_time": datetime.now()
        }

        try:
            logger.info(f"开始批量RAG同步: {len(stock_codes)}只股票, {len(data_types)}种数据类型")

            # 处理每个股票的每种数据类型
            for stock_code in stock_codes:
                for data_type in data_types:
                    try:
                        result["processed_items"] += 1

                        sync_result = await self.sync_single_stock_data(
                            stock_code, data_type, force_refresh
                        )

                        if sync_result["success"]:
                            result["successful_syncs"] += 1
                            if sync_result.get("new_version_created"):
                                result["new_versions_created"] += 1
                            if sync_result.get("version_activated"):
                                result["versions_activated"] += 1
                        elif sync_result.get("skipped"):
                            result["skipped_syncs"] += 1
                        else:
                            result["failed_syncs"] += 1
                            result["failed_items"].append({
                                "stock_code": stock_code,
                                "data_type": data_type,
                                "error": sync_result.get("error", "未知错误")
                            })

                        # 控制处理频率，避免过载
                        await asyncio.sleep(0.1)

                    except Exception as e:
                        result["failed_syncs"] += 1
                        result["failed_items"].append({
                            "stock_code": stock_code,
                            "data_type": data_type,
                            "error": str(e)
                        })
                        logger.error(f"RAG同步失败: {stock_code}-{data_type}, {e}")

        except Exception as e:
            logger.error(f"批量RAG同步过程失败: {e}")
            result["failed_syncs"] += 1

        finally:
            result["processing_time"] = time.time() - start_time
            result["end_time"] = datetime.now()

        logger.info(f"批量RAG同步完成: 成功{result['successful_syncs']}, 失败{result['failed_syncs']}, 跳过{result['skipped_syncs']}, 耗时{result['processing_time']:.2f}秒")
        return result

    async def sync_single_stock_data(self, stock_code: str, data_type: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        同步单个股票数据到RAG

        Args:
            stock_code: 股票代码
            data_type: 数据类型
            force_refresh: 是否强制刷新

        Returns:
            同步结果
        """
        result = {
            "success": False,
            "skipped": False,
            "new_version_created": False,
            "version_activated": False,
            "error": None,
            "version_id": None,
            "chunks_count": 0
        }

        try:
            logger.info(f"开始RAG同步: {stock_code}-{data_type}")

            # 1. 获取最新的结构化数据
            source_data = await self.get_latest_structured_data(stock_code, data_type)
            if not source_data:
                result["error"] = "无法获取结构化数据"
                logger.warning(f"无结构化数据: {stock_code}-{data_type}")
                return result

            # 2. 检查是否需要创建新版本
            if not force_refresh:
                # 检查是否已有相同数据的版本
                data_hash = self.version_manager.calculate_data_hash(source_data)
                existing_version = await self._check_existing_version(stock_code, data_type, data_hash)
                if existing_version:
                    result["skipped"] = True
                    result["version_id"] = existing_version["version_id"]
                    logger.info(f"数据未变化，跳过RAG同步: {stock_code}-{data_type}")
                    return result

            # 3. 创建新版本
            version_id = await self.version_manager.create_new_version(stock_code, data_type, source_data)
            result["version_id"] = version_id
            result["new_version_created"] = True

            # 4. 数据向量化
            vectorization_result = await self._vectorize_data(version_id, stock_code, data_type, source_data)
            if not vectorization_result["success"]:
                result["error"] = f"向量化失败: {vectorization_result['error']}"
                await self.version_manager.update_vector_status(version_id, 'failed')
                return result

            result["chunks_count"] = vectorization_result["chunks_count"]

            # 5. 同步向量到ChromaDB
            if self.vector_service:
                sync_result = await self._sync_vectors_to_chromadb(version_id, vectorization_result["vector_data"])
                if not sync_result["success"]:
                    result["error"] = f"向量同步失败: {sync_result['error']}"
                    await self.version_manager.update_vector_status(version_id, 'failed')
                    return result

            # 6. 激活新版本（这会自动停用旧版本）
            activation_success = await self.version_manager.activate_version(version_id)
            if activation_success:
                result["version_activated"] = True
                result["success"] = True
                logger.info(f"RAG同步成功: {stock_code}-{data_type}, version={version_id}")
            else:
                result["error"] = "版本激活失败"

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"RAG同步失败: {stock_code}-{data_type}, {e}")

        return result

    async def get_latest_structured_data(self, stock_code: str, data_type: str) -> Optional[Dict]:
        """从PostgreSQL获取最新结构化数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 根据数据类型选择对应的表和列
            data_queries = {
                "financial": {
                    "table": "stock_financial",
                    "query": "SELECT summary_data, detailed_data FROM stock_financial WHERE stock_code = %s ORDER BY updated_at DESC LIMIT 1"
                },
                "announcements": {
                    "table": "stock_announcements",
                    "query": "SELECT announcement_data FROM stock_announcements WHERE stock_code = %s ORDER BY updated_at DESC LIMIT 1"
                },
                "shareholders": {
                    "table": "stock_shareholders",
                    "query": "SELECT shareholders_data FROM stock_shareholders WHERE stock_code = %s ORDER BY updated_at DESC LIMIT 1"
                },
                "longhubang": {
                    "table": "stock_longhubang",
                    "query": "SELECT longhubang_data FROM stock_longhubang WHERE stock_code = %s ORDER BY updated_at DESC LIMIT 1"
                }
            }

            query_info = data_queries.get(data_type)
            if not query_info:
                logger.error(f"未知数据类型: {data_type}")
                return None

            # 查询最新数据
            cursor.execute(query_info["query"], (stock_code,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                if data_type == "financial":
                    # 财务数据需要合并summary_data和detailed_data
                    combined_data = {}
                    if result['summary_data']:
                        combined_data.update(result['summary_data'])
                    if result['detailed_data']:
                        combined_data.update(result['detailed_data'])
                    if combined_data:
                        return combined_data
                else:
                    # 其他数据类型直接返回对应的数据列
                    data_column_map = {
                        "announcements": "announcement_data",
                        "shareholders": "shareholders_data",
                        "longhubang": "longhubang_data"
                    }
                    column_name = data_column_map[data_type]
                    if result[column_name]:
                        return result[column_name]

            logger.warning(f"未找到结构化数据: {stock_code}-{data_type}")
            return None

        except Exception as e:
            logger.error(f"获取结构化数据失败: {stock_code}-{data_type}, {e}")
            return None

    async def _check_existing_version(self, stock_code: str, data_type: str, data_hash: str) -> Optional[Dict]:
        """检查是否已存在相同数据哈希的版本"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT version_id, vector_status FROM rag_data_versions
                WHERE stock_code = %s AND data_type = %s AND data_hash = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (stock_code, data_type, data_hash))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                return dict(result)
            return None

        except Exception as e:
            logger.error(f"检查版本失败: {e}")
            return None

    async def _vectorize_data(self, version_id: str, stock_code: str, data_type: str, source_data: Dict) -> Dict[str, Any]:
        """数据向量化"""
        try:
            logger.info(f"开始向量化: {stock_code}-{data_type}")

            # 1. 转换为文本块
            text_chunks = self.data_vectorizer.transform_to_text_chunks(stock_code, data_type, source_data)
            if not text_chunks:
                return {"success": False, "error": "文本转换失败，无有效文本块"}

            # 2. 计算向量（如果有embedding服务）
            vector_data = []
            if self.embedding_service:
                for i, chunk_text in enumerate(text_chunks):
                    try:
                        # 计算embedding
                        embedding = await self._compute_embedding(chunk_text)
                        if embedding:
                            # 创建向量数据
                            chunk_metadata = self.data_vectorizer.create_chunk_metadata(
                                stock_code, data_type, i, version_id, chunk_text
                            )

                            vector_data.append({
                                "vector_id": f"{version_id}_{i}",
                                "chunk_index": i,
                                "chunk_text": chunk_text,
                                "embedding": embedding,
                                "metadata": chunk_metadata
                            })

                    except Exception as e:
                        logger.error(f"计算embedding失败: {chunk_text[:50]}, {e}")
                        continue
            else:
                # 模拟模式：不计算实际向量
                for i, chunk_text in enumerate(text_chunks):
                    chunk_metadata = self.data_vectorizer.create_chunk_metadata(
                        stock_code, data_type, i, version_id, chunk_text
                    )
                    vector_data.append({
                        "vector_id": f"{version_id}_{i}",
                        "chunk_index": i,
                        "chunk_text": chunk_text,
                        "embedding": None,  # 模拟模式
                        "metadata": chunk_metadata
                    })

            # 3. 更新版本状态
            await self.version_manager.update_vector_status(
                version_id, 'vectorized', len(vector_data),
                {"chunks_count": len(vector_data), "vectorization_time": datetime.now().isoformat()}
            )

            logger.info(f"向量化完成: {stock_code}-{data_type}, {len(vector_data)}个文本块")

            return {
                "success": True,
                "chunks_count": len(vector_data),
                "vector_data": vector_data
            }

        except Exception as e:
            logger.error(f"向量化失败: {stock_code}-{data_type}, {e}")
            return {"success": False, "error": str(e)}

    async def _compute_embedding(self, text: str) -> Optional[List[float]]:
        """计算文本embedding"""
        try:
            if self.embedding_service and hasattr(self.embedding_service, 'encode'):
                # 调用embedding服务
                embedding = await self.embedding_service.encode(text)
                return embedding.tolist() if hasattr(embedding, 'tolist') else embedding
            else:
                logger.warning("Embedding服务不可用")
                return None

        except Exception as e:
            logger.error(f"计算embedding失败: {e}")
            return None

    async def _sync_vectors_to_chromadb(self, version_id: str, vector_data: List[Dict]) -> Dict[str, Any]:
        """同步向量到ChromaDB"""
        try:
            if not self.vector_service:
                logger.info("向量服务不可用，跳过ChromaDB同步")
                return {"success": True, "note": "模拟模式"}

            logger.info(f"开始同步向量到ChromaDB: {len(vector_data)}个向量")

            # 获取版本信息以确定集合名称
            version_info = await self.version_manager.get_version_by_id(version_id)
            if not version_info:
                return {"success": False, "error": "版本信息不存在"}

            stock_code = version_info["stock_code"]
            data_type = version_info["data_type"]
            collection_name = f"stock_{data_type}_{stock_code}"

            # 插入向量数据到ChromaDB
            vectors_inserted = 0
            for vector_item in vector_data:
                try:
                    # 准备ChromaDB格式的数据
                    documents = [vector_item["chunk_text"]]
                    metadatas = [vector_item["metadata"]]
                    ids = [vector_item["vector_id"]]

                    if vector_item["embedding"]:
                        embeddings = [vector_item["embedding"]]
                    else:
                        embeddings = None

                    # 插入到ChromaDB
                    if hasattr(self.vector_service, 'add_vectors'):
                        await self.vector_service.add_vectors(
                            collection_name=collection_name,
                            documents=documents,
                            metadatas=metadatas,
                            ids=ids,
                            embeddings=embeddings
                        )

                    vectors_inserted += 1

                    # 记录到rag_vector_mappings表
                    await self._record_vector_mapping(version_id, vector_item, collection_name)

                except Exception as e:
                    logger.error(f"向量插入失败: {vector_item['vector_id']}, {e}")
                    continue

            logger.info(f"ChromaDB同步完成: {vectors_inserted}/{len(vector_data)}个向量成功插入")

            return {
                "success": vectors_inserted > 0,
                "vectors_inserted": vectors_inserted,
                "collection_name": collection_name
            }

        except Exception as e:
            logger.error(f"ChromaDB同步失败: {e}")
            return {"success": False, "error": str(e)}

    async def _record_vector_mapping(self, version_id: str, vector_item: Dict, collection_name: str):
        """记录向量映射关系"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO rag_vector_mappings
                (version_id, vector_id, collection_name, chunk_index, chunk_text, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                version_id,
                vector_item["vector_id"],
                collection_name,
                vector_item["chunk_index"],
                vector_item["chunk_text"],
                json.dumps(vector_item["metadata"], ensure_ascii=False),
                datetime.now()
            ))

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(f"记录向量映射失败: {e}")

    async def get_rag_sync_status(self, stock_code: str = None, data_type: str = None) -> Dict[str, Any]:
        """获取RAG同步状态"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 构建查询条件
            where_conditions = []
            params = []

            if stock_code:
                where_conditions.append("stock_code = %s")
                params.append(stock_code)

            if data_type:
                where_conditions.append("data_type = %s")
                params.append(data_type)

            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)

            # 查询版本状态统计
            cursor.execute(f"""
                SELECT
                    vector_status,
                    COUNT(*) as count,
                    AVG(chunk_count) as avg_chunks
                FROM rag_data_versions
                {where_clause}
                GROUP BY vector_status
            """, params)

            status_stats = {}
            for row in cursor.fetchall():
                status_stats[row['vector_status']] = {
                    "count": row['count'],
                    "avg_chunks": float(row['avg_chunks']) if row['avg_chunks'] else 0
                }

            # 查询最近的版本
            cursor.execute(f"""
                SELECT stock_code, data_type, vector_status, chunk_count, created_at, activated_at
                FROM rag_data_versions
                {where_clause}
                ORDER BY created_at DESC
                LIMIT 10
            """, params)

            recent_versions = [dict(row) for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            return {
                "status_statistics": status_stats,
                "recent_versions": recent_versions,
                "query_time": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"获取RAG同步状态失败: {e}")
            return {"error": str(e)}

    async def cleanup_old_vectors(self, days_old: int = 30) -> Dict[str, Any]:
        """清理旧的向量数据"""
        try:
            logger.info(f"开始清理{days_old}天前的旧向量数据")

            # 获取需要清理的版本
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT version_id, stock_code, data_type
                FROM rag_data_versions
                WHERE vector_status = 'deprecated'
                  AND deprecated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            """, (days_old,))

            old_versions = cursor.fetchall()
            cursor.close()
            conn.close()

            cleanup_result = {
                "versions_processed": 0,
                "vectors_removed": 0,
                "db_records_deleted": 0,
                "errors": []
            }

            for version in old_versions:
                try:
                    version_id = version['version_id']
                    stock_code = version['stock_code']
                    data_type = version['data_type']

                    # 从ChromaDB删除向量
                    if self.vector_service:
                        collection_name = f"stock_{data_type}_{stock_code}"
                        removed_count = await self._remove_vectors_from_chromadb(version_id, collection_name)
                        cleanup_result["vectors_removed"] += removed_count

                    # 删除数据库记录
                    deleted_count = await self._delete_version_records(version_id)
                    cleanup_result["db_records_deleted"] += deleted_count

                    cleanup_result["versions_processed"] += 1

                except Exception as e:
                    cleanup_result["errors"].append({
                        "version_id": version_id,
                        "error": str(e)
                    })
                    logger.error(f"清理版本失败: {version_id}, {e}")

            logger.info(f"向量数据清理完成: 处理{cleanup_result['versions_processed']}个版本")
            return cleanup_result

        except Exception as e:
            logger.error(f"向量数据清理失败: {e}")
            return {"error": str(e)}

    async def _remove_vectors_from_chromadb(self, version_id: str, collection_name: str) -> int:
        """从ChromaDB删除指定版本的向量"""
        try:
            if not self.vector_service:
                return 0

            # 获取需要删除的向量ID
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT vector_id FROM rag_vector_mappings
                WHERE version_id = %s
            """, (version_id,))

            vector_ids = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()

            if not vector_ids:
                return 0

            # 从ChromaDB删除
            if hasattr(self.vector_service, 'delete_vectors'):
                await self.vector_service.delete_vectors(collection_name, vector_ids)

            logger.info(f"从ChromaDB删除向量: {len(vector_ids)}个")
            return len(vector_ids)

        except Exception as e:
            logger.error(f"从ChromaDB删除向量失败: {e}")
            return 0

    async def _delete_version_records(self, version_id: str) -> int:
        """删除版本相关的数据库记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 删除向量映射
            cursor.execute("DELETE FROM rag_vector_mappings WHERE version_id = %s", (version_id,))
            mapping_deleted = cursor.rowcount

            # 删除版本记录
            cursor.execute("DELETE FROM rag_data_versions WHERE version_id = %s", (version_id,))
            version_deleted = cursor.rowcount

            conn.commit()
            cursor.close()
            conn.close()

            total_deleted = mapping_deleted + version_deleted
            logger.info(f"删除数据库记录: {total_deleted}条")
            return total_deleted

        except Exception as e:
            logger.error(f"删除数据库记录失败: {e}")
            return 0