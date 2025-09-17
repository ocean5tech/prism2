#!/usr/bin/env python3
"""
真实数据收集器 + 向量化处理器
实现真实的金融数据获取：AKShare + RSS + 网页爬取
并使用真实的bge-large-zh-v1.5模型进行向量化存储
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
from sentence_transformers import SentenceTransformer

class RealDataCollector:
    """真实数据收集器 + 向量化处理器"""

    def __init__(self):
        self.session = None
        self.collected_data = []
        self.model = None
        self.client = None
        self.collection = None

    async def __aenter__(self):
        print("🚀 初始化真实数据收集和向量化系统...")

        # 清理代理变量
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        # 初始化真实的bge-large-zh-v1.5模型
        print("📥 加载真实的bge-large-zh-v1.5模型...")
        try:
            self.model = SentenceTransformer('BAAI/bge-large-zh-v1.5')
            print("✅ bge-large-zh-v1.5模型加载成功")
        except Exception as e:
            print(f"⚠️ 模型加载失败，尝试自动下载: {e}")
            try:
                # 强制下载模型
                self.model = SentenceTransformer('BAAI/bge-large-zh-v1.5', cache_folder='./models')
                print("✅ bge-large-zh-v1.5模型下载并加载成功")
            except Exception as e2:
                print(f"❌ 模型加载完全失败: {e2}")
                raise e2

        # 连接到ChromaDB
        print("🔗 连接到ChromaDB向量数据库...")
        try:
            self.client = chromadb.HttpClient(host='localhost', port=8000)
            self.client.heartbeat()
            self.collection = self.client.get_collection("financial_documents")
            print("✅ ChromaDB连接成功")
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

                for _, news in news_data.head(5).iterrows():  # 取前5条
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
                # 获取沪深300成分股
                stock_info = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20241101", end_date="20241101")
                if not stock_info.empty:
                    latest_data = stock_info.iloc[-1]
                    doc = {
                        'id': f"akshare_stock_000001_{int(time.time())}",
                        'content': f"平安银行(000001)最新交易数据：开盘价{latest_data.get('开盘', 'N/A')}，收盘价{latest_data.get('收盘', 'N/A')}，成交量{latest_data.get('成交量', 'N/A')}。",
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

            # 3. 获取宏观经济数据
            print("   获取宏观经济数据...")
            try:
                # 获取货币供应量数据
                macro_data = ak.macro_china_m2_yearly()
                if not macro_data.empty:
                    latest_m2 = macro_data.iloc[-1]
                    doc = {
                        'id': f"akshare_macro_m2_{int(time.time())}",
                        'content': f"中国货币供应量M2数据：{latest_m2.get('年份', 'N/A')}年M2同比增长{latest_m2.get('M2同比增长', 'N/A')}%，反映货币政策趋势。",
                        'metadata': {
                            'source': 'AKShare-宏观数据',
                            'doc_type': 'macro_economic',
                            'indicator': 'M2货币供应量',
                            'year': str(latest_m2.get('年份', '')),
                            'growth_rate': str(latest_m2.get('M2同比增长', '')),
                            'data_source': 'akshare_macro_m2',
                            'importance': 9,
                            'collection_time': datetime.now().isoformat()
                        }
                    }
                    collected_docs.append(doc)
                    print(f"   ✅ 获取到宏观经济数据")

            except Exception as e:
                print(f"   ⚠️ 获取宏观数据失败: {e}")

            print(f"✅ AKShare数据收集完成，共获取 {len(collected_docs)} 个文档")
            return collected_docs

        except ImportError:
            print("❌ AKShare未安装，跳过AKShare数据收集")
            return []
        except Exception as e:
            print(f"❌ AKShare数据收集失败: {e}")
            return []

    async def collect_rss_data(self) -> List[Dict]:
        """收集RSS新闻数据"""
        print("📡 开始收集RSS新闻数据...")

        rss_feeds = [
            {
                'url': 'http://www.cs.com.cn/xwzx/hwxx/rss.xml',
                'name': '中证网-海外新闻',
                'category': 'overseas_news'
            },
            {
                'url': 'http://finance.sina.com.cn/roll/index.d.html?cid=56588&page=1',
                'name': '新浪财经',
                'category': 'financial_news'
            }
        ]

        collected_docs = []

        for feed_info in rss_feeds:
            try:
                print(f"   处理RSS源: {feed_info['name']}")

                # 尝试解析RSS
                feed = feedparser.parse(feed_info['url'])

                if feed.entries:
                    print(f"   ✅ 获取到 {len(feed.entries)} 个RSS条目")

                    for i, entry in enumerate(feed.entries[:3]):  # 取前3条
                        # 清理HTML标签
                        content = BeautifulSoup(entry.get('summary', entry.get('description', '')), 'html.parser').get_text()

                        doc = {
                            'id': f"rss_{feed_info['category']}_{int(time.time())}_{i}",
                            'content': f"{entry.get('title', '')} {content}",
                            'metadata': {
                                'source': feed_info['name'],
                                'doc_type': 'rss_news',
                                'category': feed_info['category'],
                                'title': entry.get('title', ''),
                                'link': entry.get('link', ''),
                                'published': entry.get('published', ''),
                                'rss_url': feed_info['url'],
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

    async def collect_web_scraping_data(self) -> List[Dict]:
        """网页爬取数据"""
        print("🕷️ 开始网页爬取数据...")

        web_sources = [
            {
                'url': 'https://www.eastmoney.com/',
                'name': '东方财富网',
                'type': 'financial_portal'
            },
            {
                'url': 'https://finance.sina.com.cn/',
                'name': '新浪财经',
                'type': 'financial_news'
            }
        ]

        collected_docs = []

        if not self.session:
            print("❌ HTTP会话未初始化")
            return collected_docs

        for source in web_sources:
            try:
                print(f"   爬取网站: {source['name']}")

                async with self.session.get(source['url']) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        soup = BeautifulSoup(html_content, 'html.parser')

                        # 提取标题和摘要
                        titles = soup.find_all(['h1', 'h2', 'h3'], limit=5)
                        for i, title in enumerate(titles):
                            title_text = title.get_text(strip=True)
                            if len(title_text) > 10:  # 过滤过短的标题

                                # 尝试找到相关段落
                                content = title_text
                                next_elem = title.find_next(['p', 'div'], class_=lambda x: x and 'content' in str(x).lower())
                                if next_elem:
                                    content += " " + next_elem.get_text(strip=True)[:200]

                                doc = {
                                    'id': f"webscrape_{source['type']}_{int(time.time())}_{i}",
                                    'content': content,
                                    'metadata': {
                                        'source': source['name'],
                                        'doc_type': 'web_scraped',
                                        'website_type': source['type'],
                                        'url': source['url'],
                                        'title': title_text,
                                        'scrape_time': datetime.now().isoformat(),
                                        'importance': 5,
                                        'collection_time': datetime.now().isoformat()
                                    }
                                }
                                collected_docs.append(doc)

                        print(f"   ✅ 从 {source['name']} 提取了 {len([t for t in titles if len(t.get_text(strip=True)) > 10])} 个内容")

                    else:
                        print(f"   ⚠️ 网站访问失败 {source['name']}: HTTP {response.status}")

            except Exception as e:
                print(f"   ❌ 网站爬取失败 {source['name']}: {e}")

        print(f"✅ 网页爬取完成，共获取 {len(collected_docs)} 个文档")
        return collected_docs

    def store_documents_to_vector_db(self, documents: List[Dict]) -> int:
        """将文档存储到向量数据库，使用真实的bge-large-zh-v1.5模型"""
        if not documents:
            print("⚠️ 没有文档需要存储")
            return 0

        print(f"🧠 开始使用真实bge-large-zh-v1.5模型向量化 {len(documents)} 个文档...")

        try:
            # 提取文档内容用于向量化
            texts = [doc['content'] for doc in documents]
            doc_ids = [doc['id'] for doc in documents]
            metadatas = [doc['metadata'] for doc in documents]

            # 使用真实的bge-large-zh-v1.5模型生成向量
            print("   🔄 生成向量嵌入...")
            start_time = time.time()
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            embedding_time = time.time() - start_time

            print(f"   ✅ 向量生成完成，耗时 {embedding_time:.2f} 秒")
            print(f"   📊 向量维度: {embeddings.shape[1]} (应该是1024维)")

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

        # 1. AKShare数据 (无需异步)
        akshare_docs = await self.collect_akshare_data()
        all_docs.extend(akshare_docs)

        # 2. RSS数据
        rss_docs = await self.collect_rss_data()
        all_docs.extend(rss_docs)

        # 3. 网页爬取数据
        web_docs = await self.collect_web_scraping_data()
        all_docs.extend(web_docs)

        total_time = time.time() - start_time

        print(f"\n🎉 真实数据收集完成!")
        print(f"   📊 总文档数: {len(all_docs)}")
        print(f"   ⏱️ 总耗时: {total_time:.2f} 秒")
        print(f"   📄 数据源分布:")
        print(f"      - AKShare: {len(akshare_docs)} 个")
        print(f"      - RSS: {len(rss_docs)} 个")
        print(f"      - 网页爬取: {len(web_docs)} 个")

        # 立即进行向量化存储
        if all_docs:
            print(f"\n🧠 开始向量化存储流程...")
            stored_count = self.store_documents_to_vector_db(all_docs)
            print(f"✅ 向量化存储完成: {stored_count}/{len(all_docs)} 个文档")
        else:
            print("⚠️ 没有收集到数据，跳过向量化存储")

        return all_docs

async def test_real_data_collection():
    """测试真实数据收集 + 向量化存储完整流程"""
    print("🧪 测试真实数据收集 + 向量化存储系统")
    print("=" * 80)

    async with RealDataCollector() as collector:
        # 收集所有真实数据并自动向量化存储
        real_docs = await collector.collect_all_real_data()

        if real_docs:
            print(f"\n📋 收集到的真实数据预览:")
            print("=" * 60)

            for i, doc in enumerate(real_docs[:3], 1):  # 显示前3个
                print(f"\n📄 文档 {i}: {doc['id']}")
                print(f"   来源: {doc['metadata']['source']}")
                print(f"   类型: {doc['metadata']['doc_type']}")
                print(f"   内容: {doc['content'][:150]}...")
                print("-" * 50)

            # 保存到文件用于调试
            output_file = f"/home/wyatt/prism2/rag-service/real_data_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(real_docs, f, ensure_ascii=False, indent=2)
            print(f"\n💾 数据已保存到: {output_file}")

            # 验证数据库中的内容
            print(f"\n🔍 验证ChromaDB中的真实向量化数据:")
            print("=" * 60)

            try:
                count = collector.collection.count()
                print(f"   📊 数据库中总文档数: {count}")

                # 获取最新存储的文档
                recent_results = collector.collection.get(
                    include=['documents', 'metadatas', 'embeddings'],
                    limit=3
                )

                for i, doc_id in enumerate(recent_results['ids']):
                    metadata = recent_results['metadatas'][i] if recent_results['metadatas'] else {}
                    embedding_dim = len(recent_results['embeddings'][i]) if recent_results['embeddings'] and recent_results['embeddings'][i] else 0

                    print(f"   📄 向量化文档 {i+1}: {doc_id}")
                    print(f"      向量维度: {embedding_dim}")
                    print(f"      来源: {metadata.get('source', '未知')}")
                    print(f"      类型: {metadata.get('doc_type', '未知')}")

            except Exception as e:
                print(f"   ❌ 验证数据库失败: {e}")

            return real_docs
        else:
            print("❌ 没有收集到任何真实数据")
            return []

if __name__ == "__main__":
    # 安装必要的依赖
    print("📦 检查依赖包...")
    try:
        import akshare
        print("✅ AKShare 已安装")
    except ImportError:
        print("⚠️ AKShare 未安装，将跳过AKShare数据收集")

    try:
        import feedparser
        print("✅ feedparser 已安装")
    except ImportError:
        print("❌ feedparser 未安装，安装中...")
        os.system("pip install feedparser")

    try:
        import aiohttp
        print("✅ aiohttp 已安装")
    except ImportError:
        print("❌ aiohttp 未安装，安装中...")
        os.system("pip install aiohttp")

    try:
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup 已安装")
    except ImportError:
        print("❌ BeautifulSoup 未安装，安装中...")
        os.system("pip install beautifulsoup4")

    # 运行数据收集测试
    asyncio.run(test_real_data_collection())