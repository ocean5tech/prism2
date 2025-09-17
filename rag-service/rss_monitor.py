#!/usr/bin/env python3
"""
RSS监控系统
定期抓取财经RSS源，获取最新新闻并更新RAG数据库
"""

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import asyncio
import aiohttp
import feedparser
import chromadb
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import hashlib
import time
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
import schedule
import threading

class RSSMonitor:
    def __init__(self):
        # Clear proxy variables
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        self.client = None
        self.collection = None
        self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))

        # RSS源配置
        self.rss_feeds = {
            '央视财经': 'http://app.cctv.com/data/api/GetNewsHtml5?app=cctvnews&imageFlag=1&page=1&pageSize=20&serviceId=caijing',
            '人民网财经': 'http://finance.people.com.cn/rss/channel.xml',
            '新华财经': 'http://www.xinhuanet.com/finance/news_finance.xml',
            '中国新闻网财经': 'http://finance.chinanews.com/rss/finance.xml',
            '金融界': 'http://rss.jrj.com.cn/rss/focus.xml',
            '证券时报': 'http://news.stcn.com/rss/news.xml',
            '和讯财经': 'http://rss.hexun.com/rss_main.aspx'
        }

        # 监控配置
        self.update_interval = 30  # 30分钟更新一次
        self.max_articles_per_feed = 20  # 每个源最多获取20篇文章
        self.processed_urls = set()  # 已处理的URL

        # 数据质量过滤配置
        self.min_content_length = 100  # 最小内容长度
        self.blacklist_keywords = ['广告', '推广', '友情链接', '版权声明']

    def connect_to_chromadb(self):
        """连接到ChromaDB"""
        try:
            self.client = chromadb.HttpClient(host='localhost', port=8000)
            self.client.heartbeat()

            # 获取或创建集合
            try:
                self.collection = self.client.get_collection("financial_documents")
            except Exception:
                # 创建新集合
                self.collection = self.client.create_collection(
                    name="financial_documents",
                    metadata={"description": "Financial news and analysis documents"}
                )

            print("✅ 连接到ChromaDB成功")
            return True

        except Exception as e:
            print(f"❌ 连接ChromaDB失败: {e}")
            return False

    def chinese_tokenize(self, text: str) -> str:
        """中文分词"""
        return ' '.join(jieba.cut(text))

    def create_tfidf_vector(self, text: str) -> List[float]:
        """创建TF-IDF向量"""
        try:
            processed_text = self.chinese_tokenize(text)
            # 使用已训练的向量化器或创建新的
            try:
                vector = self.vectorizer.transform([processed_text])
                return vector.toarray()[0].tolist()
            except:
                # 重新训练向量化器
                self.vectorizer.fit([processed_text])
                vector = self.vectorizer.transform([processed_text])
                return vector.toarray()[0].tolist()
        except Exception as e:
            print(f"⚠️ 向量化失败: {e}")
            # 返回零向量
            return [0.0] * 1000

    def extract_keywords(self, title: str, content: str) -> List[str]:
        """提取关键词"""
        combined_text = f"{title} {content}"
        words = jieba.cut(combined_text)

        # 过滤常用词和停用词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]

        # 返回前10个关键词
        return list(set(keywords))[:10]

    def calculate_importance_score(self, article: Dict) -> int:
        """计算文章重要性分数 (1-10)"""
        score = 5  # 基础分数

        title = article.get('title', '').lower()
        content = article.get('content', '').lower()

        # 重要关键词加分
        important_keywords = {
            '央行': 2, '利率': 2, 'GDP': 2, 'PMI': 2,
            '股市': 1, '基金': 1, '债券': 1, '外汇': 1,
            '政策': 1, '监管': 1, '改革': 1, '创新': 1,
            '风险': 1, '机会': 1, '投资': 1, '收益': 1
        }

        for keyword, points in important_keywords.items():
            if keyword in title:
                score += points * 2  # 标题中的关键词权重更高
            elif keyword in content:
                score += points

        # 内容长度调整
        content_length = len(content)
        if content_length > 1000:
            score += 1
        elif content_length < 200:
            score -= 1

        # 时效性调整
        pub_time = article.get('published_time')
        if pub_time:
            try:
                pub_datetime = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
                hours_ago = (datetime.now() - pub_datetime.replace(tzinfo=None)).total_seconds() / 3600

                if hours_ago < 1:
                    score += 2  # 1小时内的新闻
                elif hours_ago < 6:
                    score += 1  # 6小时内的新闻
            except:
                pass

        return max(1, min(10, score))  # 确保分数在1-10范围内

    def is_high_quality_content(self, article: Dict) -> bool:
        """判断是否为高质量内容"""
        title = article.get('title', '')
        content = article.get('content', '')

        # 基本质量检查
        if len(content) < self.min_content_length:
            return False

        # 黑名单词汇检查
        combined_text = f"{title} {content}".lower()
        for keyword in self.blacklist_keywords:
            if keyword in combined_text:
                return False

        # 重复内容检查
        content_hash = hashlib.md5(content.encode()).hexdigest()
        if content_hash in self.processed_urls:
            return False

        self.processed_urls.add(content_hash)
        return True

    async def fetch_rss_feed(self, session: aiohttp.ClientSession, feed_name: str, feed_url: str) -> List[Dict]:
        """获取RSS源内容"""
        articles = []

        try:
            print(f"🔍 获取RSS源: {feed_name}")

            async with session.get(feed_url, timeout=30) as response:
                if response.status == 200:
                    rss_content = await response.text()
                    feed = feedparser.parse(rss_content)

                    if feed.entries:
                        print(f"   📰 找到 {len(feed.entries)} 篇文章")

                        for entry in feed.entries[:self.max_articles_per_feed]:
                            try:
                                # 获取文章详细内容
                                article_content = await self.fetch_article_content(session, entry.link)

                                article = {
                                    'title': entry.title,
                                    'content': article_content or entry.summary,
                                    'url': entry.link,
                                    'source': feed_name,
                                    'published_time': getattr(entry, 'published', datetime.now().isoformat()),
                                    'summary': getattr(entry, 'summary', ''),
                                }

                                # 质量检查
                                if self.is_high_quality_content(article):
                                    article['importance'] = self.calculate_importance_score(article)
                                    article['keywords'] = self.extract_keywords(article['title'], article['content'])
                                    articles.append(article)

                            except Exception as e:
                                print(f"   ⚠️ 处理文章失败: {e}")
                                continue
                    else:
                        print(f"   ❌ RSS源无有效内容")
                else:
                    print(f"   ❌ 获取失败: HTTP {response.status}")

        except Exception as e:
            print(f"   ❌ RSS源获取失败: {e}")

        return articles

    async def fetch_article_content(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """获取文章详细内容"""
        try:
            async with session.get(url, timeout=15) as response:
                if response.status == 200:
                    html_content = await response.text()
                    # 这里可以添加HTML解析逻辑提取正文
                    # 为简化，直接返回部分HTML内容
                    return html_content[:2000]  # 前2000字符

        except Exception as e:
            print(f"   ⚠️ 获取文章内容失败: {e}")

        return None

    async def collect_rss_articles(self) -> List[Dict]:
        """收集所有RSS源的文章"""
        all_articles = []

        print(f"🚀 开始RSS监控任务")
        print(f"📡 监控 {len(self.rss_feeds)} 个RSS源")

        async with aiohttp.ClientSession() as session:
            tasks = []
            for feed_name, feed_url in self.rss_feeds.items():
                task = self.fetch_rss_feed(session, feed_name, feed_url)
                tasks.append(task)

            # 并发获取所有RSS源
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, list):
                    all_articles.extend(result)
                    print(f"   ✅ {list(self.rss_feeds.keys())[i]}: {len(result)} 篇文章")
                else:
                    print(f"   ❌ {list(self.rss_feeds.keys())[i]}: {result}")

        # 按重要性和时间排序
        all_articles.sort(key=lambda x: (x['importance'], x['published_time']), reverse=True)

        print(f"📊 总共收集到 {len(all_articles)} 篇高质量文章")
        return all_articles

    def store_articles_to_rag(self, articles: List[Dict]):
        """将文章存储到RAG数据库"""
        if not self.collection:
            print("❌ RAG数据库未连接")
            return

        stored_count = 0

        for article in articles:
            try:
                # 创建文档ID
                doc_id = f"rss_{hashlib.md5(article['url'].encode()).hexdigest()[:12]}"

                # 检查是否已存在
                try:
                    existing = self.collection.get(ids=[doc_id])
                    if existing['ids']:
                        continue  # 跳过已存在的文档
                except:
                    pass

                # 准备文档内容
                document_content = f"""标题: {article['title']}

内容: {article['content']}

摘要: {article['summary']}

关键词: {', '.join(article['keywords'])}"""

                # 创建向量
                embedding = self.create_tfidf_vector(document_content)

                # 准备元数据
                metadata = {
                    'source_type': 'rss_news',
                    'source_name': article['source'],
                    'url': article['url'],
                    'timestamp': datetime.now().isoformat(),
                    'published_time': article['published_time'],
                    'importance': article['importance'],
                    'keywords': json.dumps(article['keywords'], ensure_ascii=False),
                    'category': 'financial_news'
                }

                # 存储到ChromaDB
                self.collection.add(
                    documents=[document_content],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    ids=[doc_id]
                )

                stored_count += 1

            except Exception as e:
                print(f"⚠️ 存储文章失败: {e}")
                continue

        print(f"✅ 成功存储 {stored_count} 篇新文章到RAG数据库")

    async def run_monitoring_cycle(self):
        """执行一次监控周期"""
        start_time = time.time()

        # 收集RSS文章
        articles = await self.collect_rss_articles()

        # 存储到RAG数据库
        if articles:
            self.store_articles_to_rag(articles)

        end_time = time.time()
        duration = end_time - start_time

        print(f"⏱️ 监控周期完成，耗时: {duration:.2f} 秒")
        print(f"🔄 下次更新时间: {(datetime.now() + timedelta(minutes=self.update_interval)).strftime('%H:%M:%S')}")
        print("-" * 80)

    def start_monitoring(self):
        """启动RSS监控"""
        if not self.connect_to_chromadb():
            return

        print(f"🎯 RSS监控系统启动")
        print(f"⏰ 更新间隔: {self.update_interval} 分钟")
        print(f"📡 监控源数量: {len(self.rss_feeds)}")
        print("="*80)

        # 立即执行一次
        asyncio.run(self.run_monitoring_cycle())

        # 设置定时任务
        schedule.every(self.update_interval).minutes.do(
            lambda: asyncio.run(self.run_monitoring_cycle())
        )

        print(f"⚡ 定时监控已启动，按 Ctrl+C 停止")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            print(f"\n🛑 RSS监控已停止")

    def run_once(self):
        """运行一次监控（用于测试）"""
        if not self.connect_to_chromadb():
            return

        print(f"🧪 执行一次RSS监控测试")
        asyncio.run(self.run_monitoring_cycle())

def main():
    """主函数"""
    monitor = RSSMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # 测试模式：只运行一次
        monitor.run_once()
    else:
        # 正常模式：持续监控
        monitor.start_monitoring()

if __name__ == "__main__":
    main()