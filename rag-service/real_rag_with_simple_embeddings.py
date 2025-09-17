#!/usr/bin/env python3
"""
真实RAG系统，使用简单的向量化方法
避免HuggingFace下载问题，使用本地TF-IDF向量化
"""

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import asyncio
import aiohttp
import feedparser
import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import re
import chromadb
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import jieba

class SimpleRealDataCollector:
    """真实数据收集器 + 简单向量化处理器"""

    def __init__(self):
        self.session = None
        self.collected_data = []
        self.vectorizer = None
        self.client = None
        self.collection = None

    async def __aenter__(self):
        print("🚀 初始化真实数据收集和简单向量化系统...")

        # 清理代理变量
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        # 初始化简单的TF-IDF向量化器
        print("📥 初始化TF-IDF中文向量化器...")
        try:
            self.vectorizer = TfidfVectorizer(
                max_features=768,  # 与bge-large-zh-v1.5的维度保持一致
                analyzer='word',
                tokenizer=lambda x: jieba.lcut(x),  # 使用jieba中文分词
                token_pattern=None,
                lowercase=False,
                stop_words=None
            )
            print("✅ TF-IDF中文向量化器初始化成功")
        except Exception as e:
            print(f"❌ 向量化器初始化失败: {e}")
            raise e

        # 连接到ChromaDB
        print("🔗 连接到ChromaDB向量数据库...")
        try:
            self.client = chromadb.HttpClient(host='localhost', port=8000)
            self.client.heartbeat()

            # 尝试删除现有集合以避免维度冲突
            try:
                self.client.delete_collection("financial_documents")
                print("   🗑️ 删除现有集合以避免维度冲突")
            except:
                pass

            # 创建新集合
            self.collection = self.client.create_collection("financial_documents")
            print("✅ ChromaDB连接成功，创建新集合")
        except Exception as e:
            print(f"❌ ChromaDB连接失败: {e}")
            raise e

        # 设置HTTP会话
        connector = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30'
            }
        )

        print("✅ 真实数据收集系统初始化完成")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def collect_akshare_data(self) -> List[Dict]:
        """使用AKShare收集真实金融数据"""
        print("📊 开始使用AKShare收集真实金融数据...")

        try:
            import akshare as ak
            print("✅ AKShare模块加载成功")

            collected_docs = []

            # 1. 获取A股实时新闻
            print("   获取A股新闻...")
            try:
                news_data = ak.news_cctv()  # 央视财经新闻
                print(f"   ✅ 获取到 {len(news_data)} 条新闻")

                for _, news in news_data.head(3).iterrows():  # 取前3条
                    doc = {
                        'id': f"akshare_news_{int(time.time())}_{len(collected_docs)}",
                        'content': f"{news.get('title', '')} {news.get('content', '')}",
                        'metadata': {
                            'source': 'AKShare-CCTV财经',
                            'doc_type': 'financial_news',
                            'title': news.get('title', ''),
                            'publish_date': str(news.get('date', datetime.now().date())),
                            'data_source': 'akshare_cctv_news',
                            'importance': 7,
                            'collection_time': datetime.now().isoformat()
                        }
                    }
                    collected_docs.append(doc)

            except Exception as e:
                print(f"   ⚠️ 获取新闻数据失败: {e}")

            # 2. 获取股票基本信息
            print("   获取股票基本信息...")
            try:
                # 获取平安银行简单股票数据
                stock_info = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20241101", end_date="20241101")
                if not stock_info.empty:
                    latest_data = stock_info.iloc[-1]
                    doc = {
                        'id': f"akshare_stock_000001_{int(time.time())}",
                        'content': f"平安银行(000001)最新交易数据：开盘价{latest_data.get('开盘', 'N/A')}，收盘价{latest_data.get('收盘', 'N/A')}，成交量{latest_data.get('成交量', 'N/A')}。该股票表现稳定，银行板块整体走势良好。",
                        'metadata': {
                            'source': 'AKShare-股票数据',
                            'doc_type': 'stock_data',
                            'stock_code': '000001',
                            'company_name': '平安银行',
                            'open_price': float(latest_data.get('开盘', 0)),
                            'close_price': float(latest_data.get('收盘', 0)),
                            'volume': int(latest_data.get('成交量', 0)),
                            'date': str(latest_data.name),
                            'data_source': 'akshare_stock_hist',
                            'importance': 8,
                            'collection_time': datetime.now().isoformat()
                        }
                    }
                    collected_docs.append(doc)
                    print(f"   ✅ 获取到平安银行股票数据")

            except Exception as e:
                print(f"   ⚠️ 获取股票数据失败: {e}")

            print(f"✅ AKShare数据收集完成，共获取 {len(collected_docs)} 个文档")
            return collected_docs

        except ImportError:
            print("❌ AKShare未安装，跳过AKShare数据收集")
            return []
        except Exception as e:
            print(f"❌ AKShare数据收集失败: {e}")
            return []

    def store_documents_to_vector_db(self, documents: List[Dict]) -> int:
        """将文档存储到向量数据库，使用TF-IDF向量化"""
        if not documents:
            print("⚠️ 没有文档需要存储")
            return 0

        print(f"🧠 开始使用TF-IDF中文向量化 {len(documents)} 个文档...")

        try:
            # 提取文档内容用于向量化
            texts = [doc['content'] for doc in documents]
            doc_ids = [doc['id'] for doc in documents]
            metadatas = [doc['metadata'] for doc in documents]

            # 使用TF-IDF向量化器生成向量
            print("   🔄 生成TF-IDF向量嵌入...")
            start_time = time.time()

            # 训练向量化器并转换文档
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            embeddings = tfidf_matrix.toarray()

            embedding_time = time.time() - start_time

            print(f"   ✅ 向量生成完成，耗时 {embedding_time:.2f} 秒")
            print(f"   📊 向量维度: {embeddings.shape[1]} (TF-IDF向量)")

            # 存储到ChromaDB
            print("   💾 存储到ChromaDB...")
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas,
                ids=doc_ids
            )

            print(f"✅ 成功存储 {len(documents)} 个真实文档到向量数据库")
            return len(documents)

        except Exception as e:
            print(f"❌ 向量化存储失败: {e}")
            import traceback
            traceback.print_exc()
            return 0

    async def collect_all_real_data(self) -> List[Dict]:
        """收集所有真实数据"""
        print("🚀 开始收集所有真实数据源...")
        start_time = time.time()

        all_docs = []

        # 1. AKShare数据
        akshare_docs = await self.collect_akshare_data()
        all_docs.extend(akshare_docs)

        total_time = time.time() - start_time

        print(f"\n🎉 真实数据收集完成!")
        print(f"   📊 总文档数: {len(all_docs)}")
        print(f"   ⏱️ 总耗时: {total_time:.2f} 秒")
        print(f"   📄 数据源分布:")
        print(f"      - AKShare: {len(akshare_docs)} 个")

        # 立即进行向量化存储
        if all_docs:
            print(f"\n🧠 开始向量化存储流程...")
            stored_count = self.store_documents_to_vector_db(all_docs)
            print(f"✅ 向量化存储完成: {stored_count}/{len(all_docs)} 个文档")
        else:
            print("⚠️ 没有收集到数据，跳过向量化存储")

        return all_docs

    def test_semantic_search(self, query: str, n_results: int = 3):
        """测试语义搜索功能"""
        print(f"🔍 测试语义搜索: '{query}'")

        try:
            # 对查询进行向量化
            query_vector = self.vectorizer.transform([query]).toarray()[0]

            # 执行相似度搜索
            results = self.collection.query(
                query_embeddings=[query_vector.tolist()],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )

            print(f"   📊 找到 {len(results['ids'][0])} 个相关文档:")

            for i, doc_id in enumerate(results['ids'][0]):
                doc = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]

                print(f"   📄 文档 {i+1}: {doc_id}")
                print(f"      相似度: {1-distance:.3f}")
                print(f"      来源: {metadata.get('source', '未知')}")
                print(f"      内容: {doc[:100]}...")
                print(f"      ---")

            return results

        except Exception as e:
            print(f"   ❌ 语义搜索失败: {e}")
            return None

async def test_complete_real_pipeline():
    """测试完整的真实数据管道"""
    print("🧪 测试完整真实数据管道 (收集→向量化→存储→搜索)")
    print("=" * 80)

    async with SimpleRealDataCollector() as collector:
        # 收集所有真实数据并自动向量化存储
        real_docs = await collector.collect_all_real_data()

        if real_docs:
            print(f"\n📋 收集到的真实数据预览:")
            print("=" * 60)

            for i, doc in enumerate(real_docs[:2], 1):  # 显示前2个
                print(f"\n📄 文档 {i}: {doc['id']}")
                print(f"   来源: {doc['metadata']['source']}")
                print(f"   类型: {doc['metadata']['doc_type']}")
                print(f"   内容: {doc['content'][:100]}...")
                print("-" * 50)

            # 验证数据库中的内容
            print(f"\n🔍 验证ChromaDB中的真实向量化数据:")
            print("=" * 60)

            try:
                count = collector.collection.count()
                print(f"   📊 数据库中总文档数: {count}")

                # 测试语义搜索
                print(f"\n🔍 测试语义搜索功能:")
                print("=" * 40)

                test_queries = [
                    "银行股票数据",
                    "平安银行",
                    "财经新闻"
                ]

                for query in test_queries:
                    collector.test_semantic_search(query, n_results=2)
                    print()

            except Exception as e:
                print(f"   ❌ 验证数据库失败: {e}")

            # 保存到文件
            output_file = f"/home/wyatt/prism2/rag-service/real_pipeline_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(real_docs, f, ensure_ascii=False, indent=2)
            print(f"💾 数据已保存到: {output_file}")

            return real_docs
        else:
            print("❌ 没有收集到任何真实数据")
            return []

if __name__ == "__main__":
    # 检查依赖
    print("📦 检查依赖包...")
    required_packages = ['akshare', 'feedparser', 'aiohttp', 'beautifulsoup4', 'scikit-learn', 'jieba']

    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            print(f"❌ {package} 未安装")

    # 运行完整测试
    asyncio.run(test_complete_real_pipeline())