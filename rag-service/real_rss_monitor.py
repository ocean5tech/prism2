#!/usr/bin/env python3
"""
真实RSS监控系统
使用真实的Bloomberg、商务部、路透社等数据源
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
from bs4 import BeautifulSoup
import re
from archive_manager import ArchiveManager

class RealRSSMonitor:
    def __init__(self):
        # Clear proxy variables
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        self.client = None
        self.collection = None
        self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        self.archive_manager = ArchiveManager()

        # 真实RSS源配置
        self.rss_feeds = {
            # Bloomberg 财经新闻
            'Bloomberg Markets': 'https://feeds.bloomberg.com/markets/news.rss',
            'Bloomberg Economics': 'https://feeds.bloomberg.com/economics/news.rss',
            'Bloomberg Industries': 'https://feeds.bloomberg.com/industries/news.rss',
            'Bloomberg Green': 'https://feeds.bloomberg.com/green/news.rss',

            # 中国官方数据源
            '商务部': 'https://www.mofcom.gov.cn/zfxxgk/index.html',

            # 路透社
            'Thomson Reuters': 'https://ir.thomsonreuters.com/rss/news-releases.xml?items=15',

            # 和讯财经
            '和讯财经': 'https://news.hexun.com/rss/',

            # 备用源
            '新浪财经RSS': 'https://finance.sina.com.cn/roll/index.d.html?cid=56588',
            '网易财经RSS': 'http://money.163.com/special/002557S6/rss_newstop.xml'
        }

        # 监控配置
        self.update_interval = 15  # 15分钟更新一次
        self.max_articles_per_feed = 25  # 每个源最多获取25篇文章
        self.processed_urls = set()  # 已处理的URL
        self.session_timeout = 30  # 请求超时30秒

        # 数据质量过滤配置
        self.min_content_length = 80  # 最小内容长度
        self.blacklist_keywords = ['广告', '推广', '友情链接', '版权声明', 'advertisement']

    def connect_to_chromadb(self):
        """连接到ChromaDB"""
        try:
            self.client = chromadb.HttpClient(host='localhost', port=8000)
            self.client.heartbeat()

            collection_name = "real_financial_news"
            try:
                self.collection = self.client.get_collection(collection_name)
                print(f"📁 使用现有集合: {collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": "Real financial news from RSS feeds"}
                )
                print(f"📁 创建新集合: {collection_name}")

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
            return [0.0] * 1000

    def clean_html_content(self, html_content: str) -> str:
        """清理HTML内容，提取纯文本"""
        if not html_content:
            return ""

        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # 移除脚本和样式标签
            for script in soup(["script", "style"]):
                script.decompose()

            # 获取纯文本
            text = soup.get_text()

            # 清理空白字符
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text

        except Exception as e:
            print(f"⚠️ HTML清理失败: {e}")
            # 回退到简单的正则清理
            text = re.sub(r'<[^>]+>', '', html_content)
            text = re.sub(r'\s+', ' ', text).strip()
            return text

    def extract_keywords(self, title: str, content: str) -> List[str]:
        """提取关键词"""
        combined_text = f"{title} {content}"

        # 英文关键词提取
        english_keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', combined_text)

        # 中文关键词提取
        chinese_words = jieba.cut(combined_text)
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        chinese_keywords = [word for word in chinese_words if len(word) > 1 and word not in stop_words]

        # 合并并去重
        all_keywords = list(set(english_keywords + chinese_keywords))
        return all_keywords[:15]  # 返回前15个关键词

    def calculate_importance_score(self, article: Dict) -> int:
        """计算文章重要性分数 (1-10)"""
        score = 5  # 基础分数

        title = article.get('title', '').lower()
        content = article.get('content', '').lower()
        source = article.get('source', '').lower()

        # 重要关键词加分
        important_keywords = {
            # 英文关键词
            'fed': 3, 'federal reserve': 3, 'interest rate': 2, 'inflation': 2,
            'gdp': 2, 'unemployment': 2, 'recession': 2, 'market': 1,
            'stock': 1, 'bond': 1, 'currency': 1, 'oil': 1, 'gold': 1,
            'china': 2, 'us': 1, 'europe': 1, 'asia': 1,
            'earnings': 2, 'revenue': 1, 'profit': 1, 'loss': 1,
            'merger': 2, 'acquisition': 2, 'ipo': 2, 'dividend': 1,

            # 中文关键词
            '央行': 3, '利率': 2, 'GDP': 2, 'PMI': 2, '通胀': 2,
            '股市': 2, '基金': 1, '债券': 1, '外汇': 1,
            '政策': 2, '监管': 2, '改革': 2, '创新': 1,
            '风险': 1, '机会': 1, '投资': 2, '收益': 1,
            '业绩': 2, '财报': 2, '并购': 2, '上市': 2
        }

        for keyword, points in important_keywords.items():
            if keyword in title:
                score += points * 2  # 标题中的关键词权重更高
            elif keyword in content:
                score += points

        # 数据源权重
        source_weights = {
            'bloomberg': 2,
            '商务部': 3,
            'thomson reuters': 2,
            '和讯': 1
        }

        for src, weight in source_weights.items():
            if src in source:
                score += weight

        # 内容长度调整
        content_length = len(content)
        if content_length > 1000:
            score += 2
        elif content_length > 500:
            score += 1
        elif content_length < 100:
            score -= 2

        # 时效性调整
        pub_time = article.get('published_time')
        if pub_time:
            try:
                if isinstance(pub_time, str):
                    pub_datetime = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
                else:
                    pub_datetime = pub_time

                hours_ago = (datetime.now() - pub_datetime.replace(tzinfo=None)).total_seconds() / 3600

                if hours_ago < 1:
                    score += 3  # 1小时内的新闻
                elif hours_ago < 6:
                    score += 2  # 6小时内的新闻
                elif hours_ago < 24:
                    score += 1  # 24小时内的新闻
            except:
                pass

        return max(1, min(10, score))  # 确保分数在1-10范围内

    def is_high_quality_content(self, article: Dict) -> bool:
        """判断是否为高质量内容"""
        title = article.get('title', '')
        content = article.get('content', '')
        url = article.get('url', '')

        # 基本质量检查
        if len(content) < self.min_content_length:
            return False

        # 标题不能为空
        if not title.strip():
            return False

        # 黑名单词汇检查
        combined_text = f"{title} {content}".lower()
        for keyword in self.blacklist_keywords:
            if keyword in combined_text:
                return False

        # 重复内容检查
        content_hash = hashlib.md5(f"{title}{content}".encode()).hexdigest()
        if content_hash in self.processed_urls:
            return False

        # URL重复检查
        if url in self.processed_urls:
            return False

        self.processed_urls.add(content_hash)
        self.processed_urls.add(url)
        return True

    async def fetch_rss_feed(self, session: aiohttp.ClientSession, feed_name: str, feed_url: str) -> List[Dict]:
        """获取RSS源内容"""
        articles = []

        try:
            print(f"🔍 获取RSS源: {feed_name}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                'Cache-Control': 'no-cache'
            }

            async with session.get(feed_url, timeout=self.session_timeout, headers=headers) as response:
                if response.status == 200:
                    rss_content = await response.text()

                    # 尝试解析RSS
                    feed = feedparser.parse(rss_content)

                    if feed.entries:
                        print(f"   📰 找到 {len(feed.entries)} 篇文章")

                        for entry in feed.entries[:self.max_articles_per_feed]:
                            try:
                                # 获取发布时间
                                pub_time = None
                                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                    pub_time = datetime(*entry.published_parsed[:6])
                                elif hasattr(entry, 'published'):
                                    try:
                                        pub_time = datetime.fromisoformat(entry.published.replace('Z', '+00:00'))
                                    except:
                                        pub_time = datetime.now()
                                else:
                                    pub_time = datetime.now()

                                # 获取内容
                                content = ""
                                if hasattr(entry, 'content') and entry.content:
                                    content = self.clean_html_content(entry.content[0].value)
                                elif hasattr(entry, 'summary'):
                                    content = self.clean_html_content(entry.summary)
                                elif hasattr(entry, 'description'):
                                    content = self.clean_html_content(entry.description)

                                # 如果内容太短，尝试获取全文
                                if len(content) < 200 and hasattr(entry, 'link'):
                                    try:
                                        full_content = await self.fetch_article_content(session, entry.link)
                                        if full_content and len(full_content) > len(content):
                                            content = full_content
                                    except:
                                        pass

                                article = {
                                    'title': getattr(entry, 'title', 'No Title'),
                                    'content': content,
                                    'url': getattr(entry, 'link', ''),
                                    'source': feed_name,
                                    'published_time': pub_time.isoformat() if pub_time else datetime.now().isoformat(),
                                    'summary': getattr(entry, 'summary', '')[:200] + '...' if hasattr(entry, 'summary') else '',
                                }

                                # 质量检查
                                if self.is_high_quality_content(article):
                                    article['importance'] = self.calculate_importance_score(article)
                                    article['keywords'] = self.extract_keywords(article['title'], article['content'])
                                    articles.append(article)
                                    print(f"   ✅ 收集: {article['title'][:50]}...")

                            except Exception as e:
                                print(f"   ⚠️ 处理文章失败: {e}")
                                continue
                    else:
                        print(f"   ❌ RSS源无有效内容")
                else:
                    print(f"   ❌ 获取失败: HTTP {response.status}")

        except asyncio.TimeoutError:
            print(f"   ⏰ RSS源超时: {feed_name}")
        except Exception as e:
            print(f"   ❌ RSS源获取失败: {e}")

        return articles

    async def fetch_article_content(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """获取文章详细内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            async with session.get(url, timeout=15, headers=headers) as response:
                if response.status == 200:
                    html_content = await response.text()
                    clean_content = self.clean_html_content(html_content)
                    return clean_content[:2000]  # 限制长度

        except Exception as e:
            print(f"   ⚠️ 获取文章内容失败: {e}")

        return None

    async def collect_real_rss_articles(self) -> List[Dict]:
        """收集所有RSS源的真实文章"""
        all_articles = []

        print(f"🚀 开始真实RSS监控任务")
        print(f"📡 监控 {len(self.rss_feeds)} 个真实RSS源")
        print("-" * 70)

        connector = aiohttp.TCPConnector(limit=10, limit_per_host=2)
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for feed_name, feed_url in self.rss_feeds.items():
                task = self.fetch_rss_feed(session, feed_name, feed_url)
                tasks.append(task)

            # 并发获取所有RSS源，但限制并发数
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                feed_name = list(self.rss_feeds.keys())[i]
                if isinstance(result, list):
                    all_articles.extend(result)
                    print(f"   ✅ {feed_name}: {len(result)} 篇文章")
                else:
                    print(f"   ❌ {feed_name}: {result}")

        # 按重要性和时间排序
        all_articles.sort(key=lambda x: (x['importance'], x['published_time']), reverse=True)

        print(f"📊 总共收集到 {len(all_articles)} 篇真实财经文章")
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
                doc_id = f"real_rss_{hashlib.md5(article['url'].encode()).hexdigest()[:12]}"

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

关键词: {', '.join(article['keywords'])}

来源: {article['source']}
发布时间: {article['published_time']}"""

                # 创建向量
                embedding = self.create_tfidf_vector(document_content)

                # 准备元数据
                metadata = {
                    'source_type': 'real_rss_news',
                    'source_name': article['source'],
                    'url': article['url'],
                    'timestamp': datetime.now().isoformat(),
                    'published_time': article['published_time'],
                    'importance': article['importance'],
                    'keywords': json.dumps(article['keywords'], ensure_ascii=False),
                    'category': 'real_financial_news',
                    'content_length': len(article['content'])
                }

                # 存储到ChromaDB
                self.collection.add(
                    documents=[document_content],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    ids=[doc_id]
                )

                stored_count += 1
                print(f"   ✅ 存储: {article['title'][:40]}...")

            except Exception as e:
                print(f"⚠️ 存储文章失败: {e}")
                continue

        print(f"✅ 成功存储 {stored_count} 篇真实新闻到RAG数据库")

        # 保存到归档
        if articles:
            archive_metadata = {
                'source': 'real_rss_monitor',
                'collection_name': 'real_financial_news',
                'stored_count': stored_count,
                'total_articles': len(articles),
                'feed_sources': list(self.rss_feeds.keys())
            }

            self.archive_manager.save_archive(
                data=articles,
                data_type='rss_news',
                metadata=archive_metadata,
                custom_suffix='real_feeds'
            )

    async def run_monitoring_cycle(self):
        """执行一次监控周期"""
        start_time = time.time()

        # 收集真实RSS文章
        articles = await self.collect_real_rss_articles()

        # 存储到RAG数据库
        if articles:
            self.store_articles_to_rag(articles)

        end_time = time.time()
        duration = end_time - start_time

        print(f"⏱️ 监控周期完成，耗时: {duration:.2f} 秒")
        print(f"🔄 下次更新时间: {(datetime.now() + timedelta(minutes=self.update_interval)).strftime('%H:%M:%S')}")
        print("=" * 80)

    def start_monitoring(self):
        """启动真实RSS监控"""
        if not self.connect_to_chromadb():
            return

        print(f"🎯 真实RSS监控系统启动")
        print(f"⏰ 更新间隔: {self.update_interval} 分钟")
        print(f"📡 监控源数量: {len(self.rss_feeds)}")
        print("="*80)

        # 立即执行一次
        asyncio.run(self.run_monitoring_cycle())

        # 设置定时任务
        schedule.every(self.update_interval).minutes.do(
            lambda: asyncio.run(self.run_monitoring_cycle())
        )

        print(f"⚡ 真实RSS定时监控已启动，按 Ctrl+C 停止")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            print(f"\n🛑 真实RSS监控已停止")

    def run_once(self):
        """运行一次监控（用于测试）"""
        if not self.connect_to_chromadb():
            return

        print(f"🧪 执行一次真实RSS监控测试")
        asyncio.run(self.run_monitoring_cycle())

def main():
    """主函数"""
    monitor = RealRSSMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # 测试模式：只运行一次
        monitor.run_once()
    else:
        # 正常模式：持续监控
        monitor.start_monitoring()

if __name__ == "__main__":
    main()