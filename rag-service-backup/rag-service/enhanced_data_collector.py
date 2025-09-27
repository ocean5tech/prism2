#!/usr/bin/env python3
"""
增强的真实数据收集器
扩大数据源：更多RSS源、A股行业数据、英文翻译
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
from googletrans import Translator

class EnhancedDataCollector:
    """增强的数据收集器：更多数据源 + 英文翻译"""

    def __init__(self):
        self.session = None
        self.collected_data = []
        self.vectorizer = None
        self.client = None
        self.collection = None
        self.translator = Translator()

    async def __aenter__(self):
        print("🚀 初始化增强数据收集系统...")

        # 清理代理变量
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        # 初始化TF-IDF向量化器
        print("📥 初始化TF-IDF中文向量化器...")
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

        # 设置HTTP会话
        connector = aiohttp.TCPConnector(limit=20)
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

        print("✅ 增强数据收集系统初始化完成")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def translate_to_chinese(self, text: str, max_length: int = 5000) -> str:
        """将英文翻译成中文"""
        try:
            if len(text) > max_length:
                text = text[:max_length]

            # 检测语言
            detected = self.translator.detect(text)
            if detected.lang == 'zh' or detected.lang == 'zh-cn':
                return text

            # 翻译成中文
            translated = self.translator.translate(text, dest='zh-cn')
            return translated.text
        except Exception as e:
            print(f"   ⚠️ 翻译失败: {e}")
            return text  # 返回原文

    async def collect_enhanced_rss_data(self) -> List[Dict]:
        """收集增强的RSS新闻数据"""
        print("📡 开始收集增强RSS新闻数据...")

        rss_feeds = [
            # 中文财经源
            {
                'url': 'http://www.cs.com.cn/xwzx/hwxx/rss.xml',
                'name': '中证网-海外新闻',
                'category': 'overseas_news',
                'language': 'zh'
            },
            {
                'url': 'http://finance.sina.com.cn/roll/index.d.html?cid=56588&page=1',
                'name': '新浪财经',
                'category': 'financial_news',
                'language': 'zh'
            },
            # 凤凰财经
            {
                'url': 'http://finance.ifeng.com/rss/index.xml',
                'name': '凤凰财经',
                'category': 'financial_news',
                'language': 'zh'
            },
            # 英文财经源（需要翻译）
            {
                'url': 'https://feeds.bloomberg.com/markets/news.rss',
                'name': 'Bloomberg Markets',
                'category': 'international_markets',
                'language': 'en'
            },
            {
                'url': 'https://feeds.finance.yahoo.com/rss/2.0/headline',
                'name': 'Yahoo Finance',
                'category': 'international_finance',
                'language': 'en'
            }
        ]

        collected_docs = []

        for feed_info in rss_feeds:
            try:
                print(f"   处理RSS源: {feed_info['name']} ({feed_info['language']})")

                # 尝试解析RSS
                feed = feedparser.parse(feed_info['url'])

                if feed.entries:
                    print(f"   ✅ 获取到 {len(feed.entries)} 个RSS条目")

                    for i, entry in enumerate(feed.entries[:5]):  # 增加到前5条
                        # 清理HTML标签
                        content = BeautifulSoup(entry.get('summary', entry.get('description', '')), 'html.parser').get_text()
                        title = entry.get('title', '')

                        full_content = f"{title} {content}"

                        # 如果是英文，翻译成中文
                        if feed_info['language'] == 'en':
                            print(f"   🔄 翻译英文内容: {title[:50]}...")
                            full_content = self.translate_to_chinese(full_content)

                        doc = {
                            'id': f"rss_{feed_info['category']}_{int(time.time())}_{i}",
                            'content': full_content,
                            'metadata': {
                                'source': feed_info['name'],
                                'doc_type': 'rss_news',
                                'category': feed_info['category'],
                                'title': title,
                                'link': entry.get('link', ''),
                                'published': entry.get('published', ''),
                                'rss_url': feed_info['url'],
                                'language': feed_info['language'],
                                'importance': 6,
                                'collection_time': datetime.now().isoformat()
                            }
                        }
                        collected_docs.append(doc)

                else:
                    print(f"   ⚠️ RSS源无数据: {feed_info['name']}")

            except Exception as e:
                print(f"   ❌ RSS源处理失败 {feed_info['name']}: {e}")

        print(f"✅ RSS数据收集完成，共获取 {len(collected_docs)} 个文档")
        return collected_docs

    async def collect_sector_stocks_data(self) -> List[Dict]:
        """收集A股行业股票数据：计算机、芯片、有色金属"""
        print("📊 开始收集A股行业股票数据...")

        try:
            import akshare as ak
            print("✅ AKShare模块加载成功")

            collected_docs = []

            # 定义目标行业和相关股票
            sectors = {
                '计算机': ['002230', '000938', '002415', '300014', '000977'],  # 科大国创、紫光股份、汇纳科技、亿纬锂能、浪潮信息
                '芯片': ['000725', '002049', '002938', '688981', '688012'],    # 京东方、紫光国微、鹏鼎控股、中芯国际、中微公司
                '有色金属': ['000831', '002460', '600362', '000878', '600219'] # 五矿发展、赣锋锂业、江西铜业、云南铜业、南山铝业
            }

            for sector_name, stock_codes in sectors.items():
                print(f"   收集{sector_name}行业股票数据...")

                for stock_code in stock_codes:
                    try:
                        # 获取股票基本信息
                        stock_info = ak.stock_zh_a_hist(
                            symbol=stock_code,
                            period="daily",
                            start_date="20241101",
                            end_date="20241101"
                        )

                        if not stock_info.empty:
                            latest_data = stock_info.iloc[-1]

                            # 获取股票名称
                            try:
                                stock_name_df = ak.stock_zh_a_spot_em()
                                stock_name = stock_name_df[stock_name_df['代码'] == stock_code]['名称'].iloc[0]
                            except:
                                stock_name = f"股票{stock_code}"

                            content = f"{sector_name}行业股票{stock_name}({stock_code})最新交易数据：开盘价{latest_data.get('开盘', 'N/A')}，收盘价{latest_data.get('收盘', 'N/A')}，成交量{latest_data.get('成交量', 'N/A')}。该股属于{sector_name}板块，为重要的科技类投资标的。"

                            doc = {
                                'id': f"akshare_stock_{sector_name}_{stock_code}_{int(time.time())}",
                                'content': content,
                                'metadata': {
                                    'source': f'AKShare-{sector_name}股票',
                                    'doc_type': 'sector_stock_data',
                                    'sector': sector_name,
                                    'stock_code': stock_code,
                                    'company_name': stock_name,
                                    'open_price': float(latest_data.get('开盘', 0)),
                                    'close_price': float(latest_data.get('收盘', 0)),
                                    'volume': int(latest_data.get('成交量', 0)),
                                    'date': str(latest_data.name),
                                    'data_source': 'akshare_sector_stocks',
                                    'importance': 7,
                                    'collection_time': datetime.now().isoformat()
                                }
                            }
                            collected_docs.append(doc)
                            print(f"   ✅ 获取到{sector_name}-{stock_name}数据")

                    except Exception as e:
                        print(f"   ⚠️ 获取股票{stock_code}数据失败: {e}")

            # 获取行业指数信息
            print("   收集行业指数数据...")
            try:
                # 科技100指数
                tech_index = ak.stock_zh_index_daily(symbol="sh000903")
                if not tech_index.empty:
                    latest_tech = tech_index.iloc[-1]
                    doc = {
                        'id': f"akshare_index_tech100_{int(time.time())}",
                        'content': f"中证科技100指数最新数据：收盘点位{latest_tech.get('close', 'N/A')}，涨跌幅反映科技股整体表现。该指数包含计算机、芯片、通信等科技龙头股票，是科技板块重要风向标。",
                        'metadata': {
                            'source': 'AKShare-行业指数',
                            'doc_type': 'index_data',
                            'index_name': '中证科技100',
                            'index_code': 'sh000903',
                            'close_price': float(latest_tech.get('close', 0)),
                            'data_source': 'akshare_index',
                            'importance': 8,
                            'collection_time': datetime.now().isoformat()
                        }
                    }
                    collected_docs.append(doc)

            except Exception as e:
                print(f"   ⚠️ 获取指数数据失败: {e}")

            print(f"✅ A股行业数据收集完成，共获取 {len(collected_docs)} 个文档")
            return collected_docs

        except ImportError:
            print("❌ AKShare未安装，跳过股票数据收集")
            return []
        except Exception as e:
            print(f"❌ 股票数据收集失败: {e}")
            return []

    async def collect_financial_news_data(self) -> List[Dict]:
        """收集更多财经新闻数据"""
        print("📰 开始收集更多财经新闻数据...")

        try:
            import akshare as ak

            collected_docs = []

            # 1. 获取更多新闻类型
            news_sources = [
                ('news_cctv', '央视财经新闻'),
                ('news_sina', '新浪财经新闻'),
                ('news_163', '网易财经新闻')
            ]

            for source_func, source_name in news_sources:
                try:
                    print(f"   获取{source_name}...")

                    if source_func == 'news_cctv':
                        news_data = ak.news_cctv()
                    elif source_func == 'news_sina':
                        news_data = ak.news_sina()
                    else:
                        continue  # 跳过不支持的源

                    if not news_data.empty:
                        print(f"   ✅ 获取到 {len(news_data)} 条{source_name}")

                        for _, news in news_data.head(10).iterrows():  # 增加到前10条
                            doc = {
                                'id': f"akshare_{source_func}_{int(time.time())}_{len(collected_docs)}",
                                'content': f"{news.get('title', '')} {news.get('content', '')}",
                                'metadata': {
                                    'source': source_name,
                                    'doc_type': 'financial_news',
                                    'title': news.get('title', ''),
                                    'publish_date': str(news.get('date', datetime.now().date())),
                                    'data_source': source_func,
                                    'importance': 7,
                                    'collection_time': datetime.now().isoformat()
                                }
                            }
                            collected_docs.append(doc)

                except Exception as e:
                    print(f"   ⚠️ 获取{source_name}失败: {e}")

            # 2. 获取宏观经济数据
            print("   获取宏观经济数据...")
            try:
                # PMI数据
                pmi_data = ak.macro_china_pmi()
                if not pmi_data.empty:
                    latest_pmi = pmi_data.iloc[-1]
                    doc = {
                        'id': f"akshare_macro_pmi_{int(time.time())}",
                        'content': f"中国制造业PMI数据：{latest_pmi.get('月份', 'N/A')}月PMI指数为{latest_pmi.get('PMI', 'N/A')}，反映制造业景气程度。PMI高于50表明制造业扩张，是重要的经济先行指标。",
                        'metadata': {
                            'source': 'AKShare-宏观数据',
                            'doc_type': 'macro_economic',
                            'indicator': 'PMI制造业指数',
                            'value': str(latest_pmi.get('PMI', '')),
                            'period': str(latest_pmi.get('月份', '')),
                            'data_source': 'akshare_macro_pmi',
                            'importance': 9,
                            'collection_time': datetime.now().isoformat()
                        }
                    }
                    collected_docs.append(doc)

            except Exception as e:
                print(f"   ⚠️ 获取宏观数据失败: {e}")

            print(f"✅ 财经新闻数据收集完成，共获取 {len(collected_docs)} 个文档")
            return collected_docs

        except Exception as e:
            print(f"❌ 财经新闻收集失败: {e}")
            return []

    def store_documents_to_vector_db(self, documents: List[Dict]) -> int:
        """将文档存储到向量数据库"""
        if not documents:
            return 0

        print(f"🧠 开始向量化存储 {len(documents)} 个文档...")

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

            print(f"✅ 成功存储 {len(documents)} 个文档到向量数据库")
            return len(documents)

        except Exception as e:
            print(f"❌ 向量化存储失败: {e}")
            return 0

    async def collect_all_enhanced_data(self) -> List[Dict]:
        """收集所有增强数据"""
        print("🚀 开始收集大规模增强数据...")
        start_time = time.time()

        all_docs = []

        # 1. 增强RSS数据
        rss_docs = await self.collect_enhanced_rss_data()
        all_docs.extend(rss_docs)

        # 2. A股行业股票数据
        stock_docs = await self.collect_sector_stocks_data()
        all_docs.extend(stock_docs)

        # 3. 更多财经新闻
        news_docs = await self.collect_financial_news_data()
        all_docs.extend(news_docs)

        total_time = time.time() - start_time

        print(f"\n🎉 大规模数据收集完成!")
        print(f"   📊 总文档数: {len(all_docs)}")
        print(f"   ⏱️ 总耗时: {total_time:.2f} 秒")
        print(f"   📄 数据源分布:")
        print(f"      - RSS新闻: {len(rss_docs)} 个")
        print(f"      - A股行业数据: {len(stock_docs)} 个")
        print(f"      - 财经新闻: {len(news_docs)} 个")

        # 向量化存储
        if all_docs:
            print(f"\n🧠 开始大规模向量化存储...")
            stored_count = self.store_documents_to_vector_db(all_docs)
            print(f"✅ 大规模向量化存储完成: {stored_count}/{len(all_docs)} 个文档")

        return all_docs

async def test_enhanced_pipeline():
    """测试增强数据管道"""
    print("🧪 测试大规模增强数据管道")
    print("=" * 80)

    async with EnhancedDataCollector() as collector:
        # 收集大规模数据
        all_docs = await collector.collect_all_enhanced_data()

        if all_docs:
            # 保存数据
            output_file = f"/home/wyatt/prism2/rag-service/enhanced_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_docs, f, ensure_ascii=False, indent=2)
            print(f"💾 大规模数据已保存到: {output_file}")

            # 验证数据库
            count = collector.collection.count()
            print(f"\n📊 最终数据库统计: {count} 个文档")

            return all_docs
        else:
            print("❌ 没有收集到数据")
            return []

if __name__ == "__main__":
    print("📦 检查依赖包...")
    required_packages = ['akshare', 'feedparser', 'aiohttp', 'beautifulsoup4', 'scikit-learn', 'jieba', 'googletrans']

    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            print(f"❌ {package} 未安装")

    asyncio.run(test_enhanced_pipeline())