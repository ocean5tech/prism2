import numpy as np
from typing import List
import logging

logger = logging.getLogger(__name__)


def cosine_similarity(vector1: List[float], vector2: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    try:
        # 转换为numpy数组
        v1 = np.array(vector1)
        v2 = np.array(vector2)

        # 计算余弦相似度
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    except Exception as e:
        logger.error(f"余弦相似度计算失败: {str(e)}")
        return 0.0


def euclidean_distance(vector1: List[float], vector2: List[float]) -> float:
    """计算两个向量的欧几里得距离"""
    try:
        v1 = np.array(vector1)
        v2 = np.array(vector2)

        distance = np.linalg.norm(v1 - v2)
        return float(distance)

    except Exception as e:
        logger.error(f"欧几里得距离计算失败: {str(e)}")
        return float('inf')


def manhattan_distance(vector1: List[float], vector2: List[float]) -> float:
    """计算两个向量的曼哈顿距离"""
    try:
        v1 = np.array(vector1)
        v2 = np.array(vector2)

        distance = np.sum(np.abs(v1 - v2))
        return float(distance)

    except Exception as e:
        logger.error(f"曼哈顿距离计算失败: {str(e)}")
        return float('inf')


def batch_cosine_similarity(
    query_vector: List[float],
    document_vectors: List[List[float]]
) -> List[float]:
    """批量计算查询向量与文档向量的余弦相似度"""
    try:
        query = np.array(query_vector)
        docs = np.array(document_vectors)

        # 计算点积
        dot_products = np.dot(docs, query)

        # 计算范数
        query_norm = np.linalg.norm(query)
        doc_norms = np.linalg.norm(docs, axis=1)

        # 避免除零
        valid_indices = (doc_norms != 0) & (query_norm != 0)
        similarities = np.zeros(len(document_vectors))

        if query_norm != 0:
            similarities[valid_indices] = dot_products[valid_indices] / (doc_norms[valid_indices] * query_norm)

        return similarities.tolist()

    except Exception as e:
        logger.error(f"批量相似度计算失败: {str(e)}")
        return [0.0] * len(document_vectors)


def find_most_similar(
    query_vector: List[float],
    document_vectors: List[List[float]],
    top_k: int = 5
) -> List[tuple]:
    """找到最相似的K个文档"""
    try:
        similarities = batch_cosine_similarity(query_vector, document_vectors)

        # 创建(相似度, 索引)对并排序
        similarity_pairs = [(sim, idx) for idx, sim in enumerate(similarities)]
        similarity_pairs.sort(reverse=True, key=lambda x: x[0])

        # 返回top-k结果
        return similarity_pairs[:top_k]

    except Exception as e:
        logger.error(f"查找最相似文档失败: {str(e)}")
        return []


def semantic_similarity_score(text1: str, text2: str) -> float:
    """基于语义的文本相似度计算（简化版本）"""
    try:
        # 这里应该使用embedding模型计算，暂时用简单方法
        # 实际应该调用embedding_service

        # 简单的词汇重叠相似度
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        jaccard_similarity = len(intersection) / len(union)
        return jaccard_similarity

    except Exception as e:
        logger.error(f"语义相似度计算失败: {str(e)}")
        return 0.0