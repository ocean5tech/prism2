#!/usr/bin/env python3
"""
测试真实数据收集（不含向量化）
先测试数据源是否正常工作
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

class SimpleDataCollector:
    """简化的数据收集器，仅测试数据源"""

    def __init__(self):
        self.session = None
        self.collected_data = []

    async def __aenter__(self):
        print("🚀 初始化简化数据收集系统...")

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

        print("✅ 简化数据收集系统初始化完成")
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

                    for i, entry in enumerate(feed.entries[:2]):  # 取前2条
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
                        titles = soup.find_all(['h1', 'h2', 'h3'], limit=2)
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

    async def collect_all_real_data(self) -> List[Dict]:
        """收集所有真实数据"""
        print("🚀 开始收集所有真实数据源...")
        start_time = time.time()

        all_docs = []

        # 1. AKShare数据
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

        return all_docs

async def test_data_sources():
    """测试数据源收集"""
    print("🧪 测试真实数据源")
    print("=" * 60)

    async with SimpleDataCollector() as collector:
        # 收集所有真实数据
        real_docs = await collector.collect_all_real_data()

        if real_docs:
            print(f"\n📋 收集到的真实数据预览:")
            print("=" * 60)

            for i, doc in enumerate(real_docs, 1):
                print(f"\n📄 文档 {i}: {doc['id']}")
                print(f"   来源: {doc['metadata']['source']}")
                print(f"   类型: {doc['metadata']['doc_type']}")
                print(f"   内容: {doc['content'][:100]}...")
                print("-" * 50)

            # 保存到文件用于调试
            output_file = f"/home/wyatt/prism2/rag-service/data_sources_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(real_docs, f, ensure_ascii=False, indent=2)
            print(f"\n💾 数据已保存到: {output_file}")

            return real_docs
        else:
            print("❌ 没有收集到任何真实数据")
            return []

if __name__ == "__main__":
    # 检查依赖
    print("📦 检查依赖包...")
    try:
        import akshare
        print("✅ AKShare 已安装")
    except ImportError:
        print("⚠️ AKShare 未安装")

    try:
        import feedparser
        print("✅ feedparser 已安装")
    except ImportError:
        print("❌ feedparser 未安装")

    try:
        import aiohttp
        print("✅ aiohttp 已安装")
    except ImportError:
        print("❌ aiohttp 未安装")

    try:
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup 已安装")
    except ImportError:
        print("❌ BeautifulSoup 未安装")

    # 运行测试
    asyncio.run(test_data_sources())