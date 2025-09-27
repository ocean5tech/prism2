import logging
import time
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings
import uuid

from app.core.config import settings
from app.models.requests import DocumentInput
from app.models.responses import DocumentMatch

logger = logging.getLogger(__name__)


class VectorService:
    """向量检索服务 - ChromaDB向量数据库操作封装 (单例模式)"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.client = None
            self.collections = {}
            self._connected = False
            self.chroma_host = settings.chromadb_host
            self.chroma_port = settings.chromadb_port
            self.default_collection_name = settings.chromadb_collection
            VectorService._initialized = True

    def connect(self) -> bool:
        """连接ChromaDB数据库"""
        try:
            # 如果已连接且客户端有效，直接返回
            if self._connected and self.client is not None:
                try:
                    self.client.heartbeat()
                    return True
                except Exception:
                    logger.warning("现有连接已失效，重新连接")
                    self._connected = False

            logger.info(f"连接ChromaDB服务器: {self.chroma_host}:{self.chroma_port}")

            # 关闭现有连接（如果有）
            if self.client is not None:
                try:
                    self.client.reset()
                except Exception:
                    pass
                self.client = None

            # 创建新的ChromaDB客户端
            self.client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # 测试连接
            self.client.heartbeat()
            logger.info("ChromaDB连接成功")
            self._connected = True

            # 清空集合缓存，重新初始化
            self.collections.clear()
            self._initialize_default_collection()

            return True

        except Exception as e:
            logger.error(f"ChromaDB连接失败: {str(e)}")
            self._connected = False
            self.client = None
            return False

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.client is not None

    def _initialize_default_collection(self):
        """初始化默认的金融文档集合"""
        try:
            collection_name = self.default_collection_name

            # 检查集合是否存在
            try:
                collection = self.client.get_collection(name=collection_name)
                logger.info(f"集合 '{collection_name}' 已存在")
            except Exception:
                # 集合不存在，创建新集合
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata={
                        "description": "金融文档向量集合",
                        "embedding_function": "bge-large-zh-v1.5"
                    }
                )
                logger.info(f"创建新集合 '{collection_name}'")

            self.collections[collection_name] = collection

        except Exception as e:
            logger.error(f"初始化默认集合失败: {str(e)}")

    def get_collection(self, collection_name: Optional[str] = None):
        """获取指定集合"""
        if not self.is_connected():
            if not self.connect():
                raise RuntimeError("无法连接ChromaDB")

        collection_name = collection_name or self.default_collection_name

        if collection_name not in self.collections:
            try:
                collection = self.client.get_collection(name=collection_name)
                self.collections[collection_name] = collection
            except Exception as e:
                logger.error(f"获取集合 '{collection_name}' 失败: {str(e)}")
                raise

        return self.collections[collection_name]

    def add_documents(
        self,
        documents: List[DocumentInput],
        embeddings: List[List[float]],
        collection_name: Optional[str] = None
    ) -> Tuple[int, List[str]]:
        """批量添加文档到向量数据库"""
        try:
            collection = self.get_collection(collection_name)

            logger.info(f"开始添加 {len(documents)} 个文档到集合")
            start_time = time.time()

            # 准备数据
            ids = [doc.id for doc in documents]
            documents_text = [doc.content for doc in documents]
            metadatas = [doc.metadata for doc in documents]

            failed_docs = []

            try:
                # 批量添加文档
                collection.add(
                    embeddings=embeddings,
                    documents=documents_text,
                    metadatas=metadatas,
                    ids=ids
                )

                add_time = time.time() - start_time
                logger.info(f"文档添加成功，耗时: {add_time:.2f}秒")

                return len(documents), failed_docs

            except Exception as e:
                logger.error(f"批量添加失败: {str(e)}")
                # 尝试逐个添加以识别问题文档
                return self._add_documents_individually(documents, embeddings, collection)

        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            raise

    def _add_documents_individually(
        self,
        documents: List[DocumentInput],
        embeddings: List[List[float]],
        collection
    ) -> Tuple[int, List[str]]:
        """逐个添加文档（失败时的回退方案）"""
        successful_count = 0
        failed_docs = []

        for i, doc in enumerate(documents):
            try:
                collection.add(
                    embeddings=[embeddings[i]],
                    documents=[doc.content],
                    metadatas=[doc.metadata],
                    ids=[doc.id]
                )
                successful_count += 1

            except Exception as e:
                logger.warning(f"文档 {doc.id} 添加失败: {str(e)}")
                failed_docs.append(doc.id)

        logger.info(f"逐个添加完成，成功: {successful_count}, 失败: {len(failed_docs)}")
        return successful_count, failed_docs

    def search_similar_documents(
        self,
        query_embedding: List[float],
        limit: int = 5,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ) -> List[DocumentMatch]:
        """搜索相似文档"""
        try:
            collection = self.get_collection(collection_name)

            logger.debug(f"开始向量搜索，limit: {limit}, threshold: {similarity_threshold}")
            start_time = time.time()

            # 构建查询参数
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": limit
            }

            # 添加元数据过滤
            if filters:
                query_params["where"] = filters

            # 执行搜索
            results = collection.query(**query_params)

            search_time = time.time() - start_time

            # 处理结果
            matches = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    similarity_score = 1 - results["distances"][0][i]  # ChromaDB返回距离，转换为相似度

                    # 应用相似度阈值过滤
                    if similarity_score >= similarity_threshold:
                        match = DocumentMatch(
                            document_id=results["ids"][0][i],
                            content=results["documents"][0][i],
                            similarity_score=similarity_score,
                            metadata=results["metadatas"][0][i] if results["metadatas"][0] else {}
                        )
                        matches.append(match)

            logger.debug(f"搜索完成，耗时: {search_time:.3f}秒, 结果数量: {len(matches)}")

            return matches

        except Exception as e:
            logger.error(f"向量搜索失败: {str(e)}")
            raise

    def get_document_by_id(self, document_id: str, collection_name: Optional[str] = None) -> Optional[DocumentMatch]:
        """根据ID获取文档"""
        try:
            collection = self.get_collection(collection_name)

            results = collection.get(
                ids=[document_id],
                include=["documents", "metadatas", "embeddings"]
            )

            if results["documents"] and results["documents"][0]:
                return DocumentMatch(
                    document_id=document_id,
                    content=results["documents"][0],
                    similarity_score=1.0,  # 完全匹配
                    metadata=results["metadatas"][0] if results["metadatas"] else {}
                )

            return None

        except Exception as e:
            logger.error(f"获取文档失败: {str(e)}")
            return None

    def delete_document(self, document_id: str, collection_name: Optional[str] = None) -> bool:
        """删除文档"""
        try:
            collection = self.get_collection(collection_name)

            collection.delete(ids=[document_id])
            logger.info(f"文档 {document_id} 删除成功")
            return True

        except Exception as e:
            logger.error(f"删除文档 {document_id} 失败: {str(e)}")
            return False

    def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            collection = self.get_collection(collection_name)
            collection_name = collection_name or self.default_collection_name

            count = collection.count()

            return {
                "collection_name": collection_name,
                "document_count": count,
                "status": "active"
            }

        except Exception as e:
            logger.error(f"获取集合统计信息失败: {str(e)}")
            return {"error": str(e)}

    def create_collection(self, collection_name: str, metadata: Dict[str, Any] = None) -> bool:
        """创建新集合"""
        try:
            if not self.is_connected():
                if not self.connect():
                    raise RuntimeError("无法连接ChromaDB")

            collection = self.client.create_collection(
                name=collection_name,
                metadata=metadata or {}
            )

            self.collections[collection_name] = collection
            logger.info(f"集合 '{collection_name}' 创建成功")
            return True

        except Exception as e:
            logger.error(f"创建集合 '{collection_name}' 失败: {str(e)}")
            return False


# 创建全局实例
vector_service = VectorService()