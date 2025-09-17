#!/usr/bin/env python3
"""
时间性 + 相关性RAG搜索系统
针对股票投资场景，优先返回最新+最相关的结果
"""

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import chromadb
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import jieba

class TimeRelevanceRAGSearch:
    def __init__(self):
        # Clear proxy variables
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        self.client = None
        self.connected = False
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words=None  # 中文分词处理
        )

    def connect(self):
        """连接到ChromaDB"""
        try:
            self.client = chromadb.HttpClient(host='localhost', port=8000)
            self.client.heartbeat()
            self.connected = True
            print("✅ 连接到RAG数据库成功")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False

    def chinese_tokenize(self, text: str) -> str:
        """中文分词处理"""
        return ' '.join(jieba.cut(text))

    def parse_date_from_metadata(self, metadata: Dict) -> datetime:
        """从元数据中解析日期"""
        # 尝试多种日期字段
        date_fields = ['timestamp', 'date', 'created_at', 'publish_time', 'time']

        for field in date_fields:
            if field in metadata:
                date_str = str(metadata[field])
                try:
                    # 支持多种日期格式
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y%m%d', '%Y-%m-%d %H:%M:%S.%f']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue

                    # 尝试ISO格式
                    if 'T' in date_str:
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))

                except Exception:
                    continue

        # 如果没有找到日期，返回一个默认值（很久以前的日期）
        return datetime(2020, 1, 1)

    def calculate_time_score(self, doc_date: datetime) -> float:
        """计算时间分数（越新分数越高）"""
        now = datetime.now()
        days_diff = (now - doc_date).days

        # 时间衰减函数：24小时内=1.0，1周内=0.8，1月内=0.6，3月内=0.4，更久=0.2
        if days_diff <= 1:
            return 1.0
        elif days_diff <= 7:
            return 0.8
        elif days_diff <= 30:
            return 0.6
        elif days_diff <= 90:
            return 0.4
        else:
            return 0.2

    def calculate_relevance_score(self, query: str, documents: List[str]) -> List[float]:
        """计算相关性分数"""
        if not documents:
            return []

        # 中文分词处理
        query_processed = self.chinese_tokenize(query)
        docs_processed = [self.chinese_tokenize(doc) for doc in documents]

        try:
            # 构建TF-IDF矩阵
            all_texts = [query_processed] + docs_processed
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)

            # 计算查询与文档的余弦相似度
            query_vector = tfidf_matrix[0:1]
            doc_vectors = tfidf_matrix[1:]

            similarities = cosine_similarity(query_vector, doc_vectors)[0]
            return similarities.tolist()

        except Exception as e:
            print(f"⚠️ 相关性计算失败: {e}")
            # 回退到简单的关键词匹配
            scores = []
            query_words = set(jieba.cut(query.lower()))

            for doc in documents:
                doc_words = set(jieba.cut(doc.lower()))
                overlap = len(query_words & doc_words)
                score = overlap / max(len(query_words), 1)
                scores.append(score)

            return scores

    def search_with_time_relevance(
        self,
        collection_name: str,
        query: str,
        limit: int = 10,
        time_weight: float = 0.3,
        relevance_weight: float = 0.7
    ) -> List[Dict]:
        """
        基于时间性和相关性的混合搜索

        Args:
            collection_name: 集合名称
            query: 搜索查询
            limit: 返回结果数量
            time_weight: 时间权重 (0-1)
            relevance_weight: 相关性权重 (0-1)
        """
        if not self.connected:
            print("❌ 未连接到数据库")
            return []

        try:
            collection = self.client.get_collection(collection_name)

            # 获取所有文档
            results = collection.get(include=['documents', 'metadatas'])

            if not results['ids']:
                print("📊 集合为空")
                return []

            documents = results['documents']
            metadatas = results['metadatas']
            ids = results['ids']

            print(f"🔍 在 {len(documents)} 个文档中搜索: '{query}'")

            # 计算相关性分数
            relevance_scores = self.calculate_relevance_score(query, documents)

            # 计算综合分数
            scored_docs = []
            for i, doc_id in enumerate(ids):
                doc_date = self.parse_date_from_metadata(metadatas[i] if metadatas else {})
                time_score = self.calculate_time_score(doc_date)
                relevance_score = relevance_scores[i] if i < len(relevance_scores) else 0.0

                # 综合分数 = 时间权重 * 时间分数 + 相关性权重 * 相关性分数
                final_score = time_weight * time_score + relevance_weight * relevance_score

                scored_docs.append({
                    'id': doc_id,
                    'content': documents[i],
                    'metadata': metadatas[i] if metadatas else {},
                    'doc_date': doc_date,
                    'time_score': time_score,
                    'relevance_score': relevance_score,
                    'final_score': final_score
                })

            # 按综合分数降序排序
            scored_docs.sort(key=lambda x: x['final_score'], reverse=True)

            # 返回前N个结果
            return scored_docs[:limit]

        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            return []

    def display_search_results(self, results: List[Dict], query: str):
        """显示搜索结果"""
        if not results:
            print("📊 没有找到相关结果")
            return

        print(f"\n{'='*80}")
        print(f"🎯 搜索结果: '{query}'")
        print(f"📊 找到 {len(results)} 个结果（按时间性+相关性排序）")
        print("="*80)

        for i, result in enumerate(results):
            print(f"\n{i+1}. 📄 {result['id']}")
            print(f"   📅 时间: {result['doc_date'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   ⏰ 时间分数: {result['time_score']:.3f}")
            print(f"   🎯 相关性分数: {result['relevance_score']:.3f}")
            print(f"   📊 综合分数: {result['final_score']:.3f}")
            print(f"   📝 内容: {result['content'][:200]}{'...' if len(result['content']) > 200 else ''}")

            # 显示关键元数据
            metadata = result['metadata']
            key_fields = ['source_type', 'importance', 'stock_code', 'category']
            meta_info = []
            for field in key_fields:
                if field in metadata:
                    meta_info.append(f"{field}: {metadata[field]}")

            if meta_info:
                print(f"   🏷️  {' | '.join(meta_info)}")

            print("-" * 80)

    def interactive_search(self):
        """交互式搜索"""
        if not self.connect():
            return

        # 获取可用集合
        try:
            collections = self.client.list_collections()
            collection_names = [col.name for col in collections]

            if not collection_names:
                print("❌ 没有找到集合")
                return

            print(f"📁 可用集合: {collection_names}")
            collection_name = collection_names[0]  # 使用第一个集合

        except Exception as e:
            print(f"❌ 获取集合失败: {e}")
            return

        print(f"\n🎛️  时间性+相关性RAG搜索")
        print(f"📁 使用集合: {collection_name}")
        print("="*60)

        while True:
            try:
                print(f"\n请输入搜索查询 (输入 'quit' 退出):")
                query = input("🔍 > ").strip()

                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见!")
                    break

                if not query:
                    continue

                # 搜索参数
                print(f"\n搜索参数配置:")
                print(f"1. 使用默认权重 (时间30%, 相关性70%)")
                print(f"2. 自定义权重")

                weight_choice = input("选择 (1/2): ").strip()

                if weight_choice == '2':
                    try:
                        time_weight = float(input("时间权重 (0-1): "))
                        relevance_weight = float(input("相关性权重 (0-1): "))

                        # 标准化权重
                        total = time_weight + relevance_weight
                        if total > 0:
                            time_weight /= total
                            relevance_weight /= total
                        else:
                            time_weight, relevance_weight = 0.3, 0.7

                    except ValueError:
                        time_weight, relevance_weight = 0.3, 0.7
                        print("⚠️ 使用默认权重")
                else:
                    time_weight, relevance_weight = 0.3, 0.7

                limit = 10
                try:
                    limit_input = input(f"返回结果数量 (默认{limit}): ").strip()
                    if limit_input:
                        limit = int(limit_input)
                except ValueError:
                    pass

                print(f"\n🔍 搜索中... (时间权重: {time_weight:.1%}, 相关性权重: {relevance_weight:.1%})")

                # 执行搜索
                results = self.search_with_time_relevance(
                    collection_name,
                    query,
                    limit=limit,
                    time_weight=time_weight,
                    relevance_weight=relevance_weight
                )

                # 显示结果
                self.display_search_results(results, query)

            except KeyboardInterrupt:
                print("\n\n👋 再见!")
                break
            except Exception as e:
                print(f"❌ 搜索错误: {e}")

def main():
    """命令行工具"""
    print("🎯 时间性+相关性RAG搜索系统")
    print("专为股票投资场景优化，优先返回最新+最相关的结果")
    print("="*80)

    search_engine = TimeRelevanceRAGSearch()

    if len(sys.argv) > 1:
        # 命令行模式
        if not search_engine.connect():
            return

        query = ' '.join(sys.argv[1:])

        # 获取真实RSS新闻集合
        try:
            collections = search_engine.client.list_collections()
            collection_name = "real_financial_news"  # 指定真实RSS新闻集合
            if collections:
                results = search_engine.search_with_time_relevance(collection_name, query)
                search_engine.display_search_results(results, query)
            else:
                print("❌ 没有找到集合")
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
    else:
        # 交互模式
        search_engine.interactive_search()

if __name__ == "__main__":
    main()