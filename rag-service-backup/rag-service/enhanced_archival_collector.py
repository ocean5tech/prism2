#!/usr/bin/env python3
"""
增强的数据归档收集器
完整保存原文数据，包括URL、原始内容、作者、日期等所有信息
用于构建可重用的RAG数据档案
"""

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import asyncio
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any
import chromadb
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import jieba

class EnhancedArchivalCollector:
    """增强的数据归档收集器 - 完整保存原文信息"""

    def __init__(self):
        self.vectorizer = None
        self.client = None
        self.collection = None
        self.archive_data = []  # 用于保存完整的归档数据

    async def __aenter__(self):
        print("🚀 初始化增强数据归档收集系统...")

        # 清理代理变量
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        # 初始化TF-IDF向量化器
        self.vectorizer = TfidfVectorizer(
            max_features=768,
            analyzer='word',
            tokenizer=lambda x: jieba.lcut(x),
            token_pattern=None,
            lowercase=False,
            stop_words=None
        )

        # 连接到ChromaDB
        print("🔗 连接到ChromaDB向量数据库...")
        self.client = chromadb.HttpClient(host='localhost', port=8000)
        self.client.heartbeat()

        try:
            self.client.delete_collection("financial_documents")
            print("   🗑️ 删除现有集合")
        except:
            pass

        self.collection = self.client.create_collection("financial_documents")
        print("✅ ChromaDB连接成功，创建新集合")

        print("✅ 增强数据归档收集系统初始化完成")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def create_document_hash(self, content: str) -> str:
        """为文档内容创建唯一哈希标识"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:12]

    def create_archive_record(self, raw_data: Any, processed_content: str, metadata: Dict, data_source_info: Dict) -> Dict:
        """创建完整的归档记录"""
        doc_hash = self.create_document_hash(processed_content)
        timestamp = datetime.now().isoformat()

        archive_record = {
            # 唯一标识
            'document_id': f"archive_{data_source_info['source_type']}_{doc_hash}",
            'document_hash': doc_hash,
            'collection_timestamp': timestamp,

            # 原始数据保存
            'raw_data': {
                'original_response': raw_data,  # 完整的API响应
                'raw_content_length': len(str(raw_data)),
                'data_encoding': 'utf-8'
            },

            # 数据源详细信息
            'source_info': {
                'source_type': data_source_info['source_type'],
                'api_endpoint': data_source_info.get('api_endpoint', ''),
                'data_provider': data_source_info.get('data_provider', ''),
                'access_method': data_source_info.get('access_method', ''),
                'source_url': data_source_info.get('source_url', ''),
                'source_description': data_source_info.get('source_description', ''),
                'data_license': data_source_info.get('data_license', 'Unknown'),
                'update_frequency': data_source_info.get('update_frequency', 'Unknown'),
                'collection_method': data_source_info.get('collection_method', '')
            },

            # 内容信息
            'content_info': {
                'processed_content': processed_content,
                'content_language': 'zh-cn',
                'content_length': len(processed_content),
                'processing_method': 'text_extraction_and_analysis'
            },

            # 元数据
            'metadata': metadata,

            # 作者和发布信息
            'publication_info': {
                'author': metadata.get('author', '未知'),
                'publish_date': metadata.get('publish_date', ''),
                'original_title': metadata.get('title', ''),
                'publisher': metadata.get('source', ''),
                'publication_url': metadata.get('link', ''),
                'content_type': metadata.get('doc_type', '')
            },

            # 质量和重要性评估
            'quality_metrics': {
                'importance_score': metadata.get('importance', 5),
                'content_completeness': 'complete' if len(processed_content) > 100 else 'partial',
                'data_reliability': data_source_info.get('reliability_score', 'medium'),
                'freshness_score': self.calculate_freshness_score(metadata.get('publish_date', ''))
            },

            # 技术信息
            'technical_info': {
                'collection_version': '1.0.0',
                'collector_name': 'EnhancedArchivalCollector',
                'processing_pipeline': 'akshare_api -> text_extraction -> jieba_tokenization -> tfidf_vectorization',
                'vector_dimension': 768,
                'embedding_method': 'TF-IDF',
                'storage_format': 'ChromaDB'
            }
        }

        return archive_record

    def calculate_freshness_score(self, publish_date: str) -> float:
        """计算数据新鲜度分数"""
        try:
            if not publish_date:
                return 0.0

            pub_date = datetime.strptime(publish_date, '%Y%m%d')
            days_old = (datetime.now() - pub_date).days

            if days_old <= 1:
                return 1.0
            elif days_old <= 7:
                return 0.8
            elif days_old <= 30:
                return 0.6
            elif days_old <= 90:
                return 0.4
            else:
                return 0.2
        except:
            return 0.0

    async def collect_stocks_with_full_archive(self) -> List[Dict]:
        """收集股票数据并创建完整归档"""
        print("📊 开始收集股票数据并创建完整归档...")

        try:
            import akshare as ak
            print("✅ AKShare模块加载成功")

            collected_docs = []

            # 精选重要股票进行详细收集
            important_stocks = {
                '002230': {'name': '科大讯飞', 'sector': '人工智能', 'description': '中国智能语音领导者'},
                '000725': {'name': '京东方A', 'sector': '显示技术', 'description': '全球半导体显示龙头'},
                '002460': {'name': '赣锋锂业', 'sector': '锂电池材料', 'description': '全球锂化合物领军企业'},
                '300750': {'name': '宁德时代', 'sector': '动力电池', 'description': '全球动力电池龙头'},
                '300229': {'name': '拓尔思', 'sector': '大数据AI', 'description': '专业大数据和AI服务商'}
            }

            for stock_code, stock_info in important_stocks.items():
                try:
                    print(f"   详细收集 {stock_info['name']}({stock_code}) 数据...")

                    # 数据源信息
                    data_source_info = {
                        'source_type': 'akshare_stock_data',
                        'api_endpoint': f'ak.stock_zh_a_hist(symbol="{stock_code}")',
                        'data_provider': 'AKShare',
                        'access_method': 'Python API',
                        'source_url': f'https://akshare.akfamily.xyz/data/stock/stock.html#{stock_code}',
                        'source_description': f'AKShare提供的{stock_info["name"]}股票历史交易数据',
                        'data_license': 'AKShare License',
                        'update_frequency': 'Daily',
                        'collection_method': 'akshare.stock_zh_a_hist API',
                        'reliability_score': 'high'
                    }

                    # 获取原始数据
                    raw_stock_data = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="daily",
                        start_date="20241001",
                        end_date="20241101"
                    )

                    if not raw_stock_data.empty:
                        latest_data = raw_stock_data.iloc[-1]

                        # 计算技术指标
                        if len(raw_stock_data) > 1:
                            prev_close = raw_stock_data.iloc[-2]['收盘']
                            change_pct = ((latest_data['收盘'] - prev_close) / prev_close) * 100
                        else:
                            change_pct = 0

                        # 处理后的内容
                        processed_content = f"{stock_info['name']}({stock_code}) - {stock_info['description']}。最新交易数据：收盘价{latest_data.get('收盘', 'N/A')}元，涨跌幅{change_pct:.2f}%，成交量{latest_data.get('成交量', 'N/A')}股，成交额{latest_data.get('成交额', 'N/A')}元。所属{stock_info['sector']}板块，为{stock_info['sector']}领域重要投资标的。"

                        # 元数据
                        metadata = {
                            'source': f'AKShare-{stock_info["sector"]}',
                            'doc_type': 'archived_stock_analysis',
                            'sector': stock_info['sector'],
                            'stock_code': stock_code,
                            'company_name': stock_info['name'],
                            'close_price': float(latest_data.get('收盘', 0)),
                            'volume': int(latest_data.get('成交量', 0)),
                            'amount': float(latest_data.get('成交额', 0)),
                            'change_pct': round(change_pct, 2),
                            'publish_date': str(latest_data.name).replace('-', ''),
                            'title': f"{stock_info['name']}股票交易数据",
                            'author': 'AKShare数据源',
                            'link': f'https://akshare.akfamily.xyz/data/stock/stock.html#{stock_code}',
                            'data_source': 'akshare_archived_stocks',
                            'importance': 9,
                            'collection_time': datetime.now().isoformat()
                        }

                        # 创建完整归档记录
                        archive_record = self.create_archive_record(
                            raw_data=raw_stock_data.to_dict(),
                            processed_content=processed_content,
                            metadata=metadata,
                            data_source_info=data_source_info
                        )

                        # 保存到归档
                        self.archive_data.append(archive_record)

                        # 创建用于向量化的文档
                        doc = {
                            'id': archive_record['document_id'],
                            'content': processed_content,
                            'metadata': metadata
                        }
                        collected_docs.append(doc)

                        print(f"   ✅ {stock_info['name']} 完整归档创建成功")
                        await asyncio.sleep(1)  # 避免API频率限制

                except Exception as e:
                    print(f"   ⚠️ 获取股票{stock_code}数据失败: {e}")

            # 收集央视财经新闻并归档
            print("   收集央视财经新闻并创建归档...")
            try:
                raw_news_data = ak.news_cctv()
                data_source_info = {
                    'source_type': 'akshare_cctv_news',
                    'api_endpoint': 'ak.news_cctv()',
                    'data_provider': 'AKShare + CCTV',
                    'access_method': 'Python API',
                    'source_url': 'http://www.cctv.com/finance/',
                    'source_description': 'AKShare提供的央视财经新闻数据',
                    'data_license': 'AKShare License + CCTV',
                    'update_frequency': 'Hourly',
                    'collection_method': 'akshare.news_cctv API',
                    'reliability_score': 'very_high'
                }

                if not raw_news_data.empty:
                    for _, news in raw_news_data.head(5).iterrows():
                        processed_content = f"{news.get('title', '')} {news.get('content', '')}"

                        metadata = {
                            'source': '央视财经官方',
                            'doc_type': 'archived_financial_news',
                            'news_type': '权威财经资讯',
                            'title': news.get('title', ''),
                            'author': '央视财经记者',
                            'publish_date': str(news.get('date', datetime.now().date())).replace('-', ''),
                            'link': 'http://www.cctv.com/finance/',
                            'data_source': 'akshare_cctv_archived',
                            'importance': 9,
                            'collection_time': datetime.now().isoformat()
                        }

                        # 创建归档记录
                        archive_record = self.create_archive_record(
                            raw_data=news.to_dict(),
                            processed_content=processed_content,
                            metadata=metadata,
                            data_source_info=data_source_info
                        )

                        self.archive_data.append(archive_record)

                        doc = {
                            'id': archive_record['document_id'],
                            'content': processed_content,
                            'metadata': metadata
                        }
                        collected_docs.append(doc)

                    print(f"   ✅ 央视财经新闻归档: {len(raw_news_data.head(5))} 条")

            except Exception as e:
                print(f"   ⚠️ 央视新闻归档失败: {e}")

            print(f"✅ 完整数据归档收集完成，共获取 {len(collected_docs)} 个文档")
            print(f"📁 归档记录: {len(self.archive_data)} 个完整档案")
            return collected_docs

        except ImportError:
            print("❌ AKShare未安装")
            return []
        except Exception as e:
            print(f"❌ 数据收集失败: {e}")
            return []

    def store_documents_to_vector_db(self, documents: List[Dict]) -> int:
        """存储文档到向量数据库"""
        if not documents:
            return 0

        print(f"🧠 开始向量化存储 {len(documents)} 个归档文档...")

        try:
            texts = [doc['content'] for doc in documents]
            doc_ids = [doc['id'] for doc in documents]
            metadatas = [doc['metadata'] for doc in documents]

            print("   🔄 生成TF-IDF向量嵌入...")
            start_time = time.time()
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            embeddings = tfidf_matrix.toarray()
            embedding_time = time.time() - start_time

            print(f"   ✅ 向量生成完成，耗时 {embedding_time:.2f} 秒")
            print(f"   📊 向量维度: {embeddings.shape[1]}")

            print("   💾 存储到ChromaDB...")
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas,
                ids=doc_ids
            )

            print(f"✅ 成功存储 {len(documents)} 个归档文档到向量数据库")
            return len(documents)

        except Exception as e:
            print(f"❌ 向量化存储失败: {e}")
            return 0

    def save_complete_archive(self) -> str:
        """保存完整的数据归档"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 主归档文件
        archive_file = f"/home/wyatt/prism2/rag-service/complete_data_archive_{timestamp}.json"

        # 归档元信息
        archive_metadata = {
            'archive_info': {
                'creation_date': datetime.now().isoformat(),
                'archive_version': '1.0.0',
                'total_documents': len(self.archive_data),
                'data_sources': list(set([record['source_info']['source_type'] for record in self.archive_data])),
                'archive_purpose': 'Complete financial data archive for RAG system reconstruction',
                'archive_format': 'JSON with full metadata and raw data',
                'reconstruction_instructions': 'Use this archive to rebuild RAG database without re-downloading'
            },
            'documents': self.archive_data
        }

        # 保存完整归档 (处理日期序列化)
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(archive_metadata, f, ensure_ascii=False, indent=2, default=str)

        print(f"📁 完整数据归档已保存: {archive_file}")
        return archive_file

    async def collect_all_with_archive(self) -> tuple:
        """收集所有数据并创建完整归档"""
        print("🚀 开始完整数据收集和归档...")
        start_time = time.time()

        # 收集数据
        all_docs = await self.collect_stocks_with_full_archive()

        total_time = time.time() - start_time

        print(f"\n🎉 完整数据收集和归档完成!")
        print(f"   📊 向量化文档数: {len(all_docs)}")
        print(f"   📁 归档记录数: {len(self.archive_data)}")
        print(f"   ⏱️ 总耗时: {total_time:.2f} 秒")

        # 向量化存储
        if all_docs:
            print(f"\n🧠 开始向量化存储...")
            stored_count = self.store_documents_to_vector_db(all_docs)
            print(f"✅ 向量化存储完成: {stored_count}/{len(all_docs)} 个文档")

        # 保存完整归档
        archive_file = self.save_complete_archive()

        return all_docs, archive_file

async def test_archival_system():
    """测试完整归档系统"""
    print("🧪 测试增强数据归档系统")
    print("=" * 80)

    async with EnhancedArchivalCollector() as collector:
        # 收集并归档数据
        docs, archive_file = await collector.collect_all_with_archive()

        if docs:
            # 验证数据库
            count = collector.collection.count()
            print(f"\n📊 最终数据库统计: {count} 个文档")
            print(f"📁 完整归档文件: {archive_file}")

            print(f"\n✅ 数据归档特性:")
            print(f"   - 原始API响应数据: 完整保存")
            print(f"   - 数据源URL和描述: 详细记录")
            print(f"   - 作者和发布信息: 完整元数据")
            print(f"   - 数据新鲜度评分: 自动计算")
            print(f"   - 重建RAG库: 支持离线重建")

            return docs, archive_file
        else:
            print("❌ 没有收集到数据")
            return [], ""

if __name__ == "__main__":
    asyncio.run(test_archival_system())