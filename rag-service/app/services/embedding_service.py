import logging
import time
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
import os

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """文档嵌入服务 - 使用bge-large-zh-v1.5模型进行中文文本向量化"""

    def __init__(self):
        self.model = None
        self.model_path = settings.embedding_model_path
        self.device = settings.model_device
        self.max_length = settings.model_max_length
        self._model_loaded = False

    def load_model(self) -> bool:
        """加载bge-large-zh-v1.5模型"""
        try:
            logger.info(f"开始加载embedding模型: {self.model_path}")
            start_time = time.time()

            # 检查模型文件是否存在
            if not os.path.exists(self.model_path):
                logger.warning(f"本地模型路径不存在: {self.model_path}")
                logger.info("尝试从Hugging Face下载bge-large-zh-v1.5模型...")
                model_name = "BAAI/bge-large-zh-v1.5"
            else:
                model_name = self.model_path

            # 加载模型
            self.model = SentenceTransformer(
                model_name,
                device=self.device
            )

            # 设置最大序列长度
            self.model.max_seq_length = self.max_length

            load_time = time.time() - start_time
            logger.info(f"模型加载成功，耗时: {load_time:.2f}秒")
            logger.info(f"模型设备: {self.device}, 最大长度: {self.max_length}")

            self._model_loaded = True
            return True

        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            self._model_loaded = False
            return False

    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._model_loaded and self.model is not None

    def embed_text(self, text: str) -> List[float]:
        """单个文本向量化"""
        if not self.is_model_loaded():
            if not self.load_model():
                raise RuntimeError("无法加载embedding模型")

        try:
            # 文本预处理
            processed_text = self._preprocess_text(text)

            # 生成向量
            start_time = time.time()
            embedding = self.model.encode(
                processed_text,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            embed_time = time.time() - start_time

            logger.debug(f"文本向量化完成，耗时: {embed_time:.3f}秒, 向量维度: {len(embedding)}")

            return embedding.tolist()

        except Exception as e:
            logger.error(f"文本向量化失败: {str(e)}")
            raise

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """批量文本向量化"""
        if not self.is_model_loaded():
            if not self.load_model():
                raise RuntimeError("无法加载embedding模型")

        try:
            logger.info(f"开始批量向量化，文本数量: {len(texts)}, 批次大小: {batch_size}")
            start_time = time.time()

            # 预处理所有文本
            processed_texts = [self._preprocess_text(text) for text in texts]

            # 批量生成向量
            embeddings = self.model.encode(
                processed_texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=True,
                convert_to_tensor=False
            )

            total_time = time.time() - start_time
            avg_time_per_text = total_time / len(texts)

            logger.info(f"批量向量化完成，总耗时: {total_time:.2f}秒, 平均每文本: {avg_time_per_text:.3f}秒")

            return embeddings.tolist()

        except Exception as e:
            logger.error(f"批量向量化失败: {str(e)}")
            raise

    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        if not text or not text.strip():
            return ""

        # 移除多余空白字符
        processed = " ".join(text.strip().split())

        # 截断过长文本
        if len(processed) > self.max_length:
            processed = processed[:self.max_length]
            logger.debug(f"文本被截断至{self.max_length}字符")

        return processed

    def get_model_info(self) -> dict:
        """获取模型信息"""
        if not self.is_model_loaded():
            return {"status": "not_loaded"}

        try:
            # 获取模型配置信息
            model_config = self.model._modules.get('0', None)

            return {
                "status": "loaded",
                "model_path": self.model_path,
                "device": self.device,
                "max_length": self.max_length,
                "embedding_dim": self.model.get_sentence_embedding_dimension(),
                "model_name": getattr(model_config, 'name_or_path', 'unknown') if model_config else 'unknown'
            }
        except Exception as e:
            logger.error(f"获取模型信息失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        try:
            # 转换为numpy数组
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # 计算余弦相似度
            similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

            return float(similarity)

        except Exception as e:
            logger.error(f"相似度计算失败: {str(e)}")
            raise


# 创建全局实例
embedding_service = EmbeddingService()