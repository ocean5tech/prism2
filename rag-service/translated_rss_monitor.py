#!/usr/bin/env python3
"""
带翻译功能的RSS监控系统
自动检测语言并翻译英文新闻为中文，提高中文RAG检索效果
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
from googletrans import Translator
import langdetect
from langdetect import detect

class TranslatedRSSMonitor:
    def __init__(self):
        # Clear proxy variables
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        self.client = None
        self.collection = None
        self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        self.archive_manager = ArchiveManager()

        # 翻译器初始化
        self.translator = Translator()
        self.translation_cache = {}  # 翻译缓存

        # 真实RSS源配置
        self.rss_feeds = {
            # Bloomberg 财经新闻 (英文)
            'Bloomberg Markets': 'https://feeds.bloomberg.com/markets/news.rss',
            'Bloomberg Economics': 'https://feeds.bloomberg.com/economics/news.rss',
            'Bloomberg Industries': 'https://feeds.bloomberg.com/industries/news.rss',
            'Bloomberg Green': 'https://feeds.bloomberg.com/green/news.rss',

            # 路透社 (英文)
            'Thomson Reuters': 'https://ir.thomsonreuters.com/rss/news-releases.xml?items=15',

            # 和讯财经 (中文)
            '和讯财经': 'https://news.hexun.com/rss/',

            # 中国官方数据源 (中文)
            '中国证券网': 'http://news.cnstock.com/rss/news_zzkx.xml',
            '新浪财经': 'https://finance.sina.com.cn/roll/index.d.html?cid=56588'
        }

        # 监控配置
        self.update_interval = 20  # 20分钟更新一次（翻译需要更多时间）
        self.max_articles_per_feed = 15  # 减少数量以提高翻译质量
        self.processed_urls = set()
        self.session_timeout = 30

        # 翻译配置
        self.translate_english = True  # 是否翻译英文内容
        self.max_translation_length = 1500  # 最大翻译长度
        self.batch_translation_size = 3  # 批量翻译大小

        # 数据质量过滤配置
        self.min_content_length = 80
        self.blacklist_keywords = ['广告', '推广', '友情链接', '版权声明', 'advertisement', 'sponsored']

    def connect_to_chromadb(self):
        """连接到ChromaDB"""
        try:
            self.client = chromadb.HttpClient(host='localhost', port=8000)
            self.client.heartbeat()

            collection_name = "translated_financial_news"
            try:
                self.collection = self.client.get_collection(collection_name)
                print(f"📁 使用现有集合: {collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": "Translated financial news from multilingual RSS feeds"}
                )
                print(f"📁 创建新集合: {collection_name}")

            print("✅ 连接到ChromaDB成功")
            return True

        except Exception as e:
            print(f"❌ 连接ChromaDB失败: {e}")
            return False

    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        try:
            # 清理文本
            clean_text = re.sub(r'[^\w\s]', ' ', text).strip()
            if len(clean_text) < 10:
                return 'unknown'

            lang = detect(clean_text)
            return lang
        except Exception as e:
            print(f"⚠️ 语言检测失败: {e}")
            # 简单的启发式检测
            if re.search(r'[\u4e00-\u9fff]', text):
                return 'zh'
            elif re.search(r'[a-zA-Z]', text):
                return 'en'
            else:
                return 'unknown'

    def should_translate(self, text: str, detected_lang: str) -> bool:
        """判断是否需要翻译"""
        if not self.translate_english:
            return False

        # 只翻译英文内容
        if detected_lang != 'en':
            return False

        # 检查长度限制
        if len(text) > self.max_translation_length:
            return False

        # 检查是否已缓存
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.translation_cache:
            return False

        return True

    def translate_text(self, text: str, source_lang: str = 'en', target_lang: str = 'zh') -> Optional[str]:
        """翻译文本"""
        if not text or not text.strip():
            return text

        # 检查缓存
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.translation_cache:
            return self.translation_cache[text_hash]

        try:
            # 分段翻译长文本
            if len(text) > 800:
                sentences = re.split(r'[.!?。！？]', text)
                translated_sentences = []

                for sentence in sentences:
                    if sentence.strip():
                        try:
                            result = self.translator.translate(
                                sentence.strip(),
                                src=source_lang,
                                dest=target_lang
                            )
                            translated_sentences.append(result.text)
                            time.sleep(0.5)  # 避免请求过于频繁
                        except Exception as e:
                            print(f"⚠️ 句子翻译失败: {e}")
                            translated_sentences.append(sentence.strip())

                translated_text = '。'.join(translated_sentences)
            else:
                # 短文本直接翻译
                result = self.translator.translate(text, src=source_lang, dest=target_lang)
                translated_text = result.text

            # 缓存翻译结果
            self.translation_cache[text_hash] = translated_text
            return translated_text

        except Exception as e:
            print(f"⚠️ 翻译失败: {e}")
            return text  # 返回原文

    def process_article_translation(self, article: Dict) -> Dict:
        """处理文章翻译"""
        title = article.get('title', '')
        content = article.get('content', '')
        summary = article.get('summary', '')

        # 检测语言
        title_lang = self.detect_language(title)
        content_lang = self.detect_language(content)

        # 翻译逻辑
        translated_article = article.copy()

        # 翻译标题
        if self.should_translate(title, title_lang):
            print(f"   🌐 翻译标题: {title[:50]}...")
            translated_title = self.translate_text(title)
            if translated_title:
                translated_article['title'] = translated_title
                translated_article['original_title'] = title
                translated_article['title_translated'] = True

        # 翻译内容
        if self.should_translate(content, content_lang):
            print(f"   🌐 翻译内容: {len(content)} 字符")
            translated_content = self.translate_text(content)
            if translated_content:
                translated_article['content'] = translated_content
                translated_article['original_content'] = content
                translated_article['content_translated'] = True

        # 翻译摘要
        if summary and self.should_translate(summary, self.detect_language(summary)):
            translated_summary = self.translate_text(summary)
            if translated_summary:
                translated_article['summary'] = translated_summary
                translated_article['original_summary'] = summary

        # 添加语言信息
        translated_article['detected_language'] = {
            'title': title_lang,
            'content': content_lang
        }

        return translated_article

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
            soup = BeautifulSoup(html_content, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text

        except Exception as e:
            print(f"⚠️ HTML清理失败: {e}")
            text = re.sub(r'<[^>]+>', '', html_content)
            text = re.sub(r'\s+', ' ', text).strip()
            return text

    def extract_keywords(self, title: str, content: str) -> List[str]:
        """提取关键词（支持中英文）"""
        combined_text = f"{title} {content}"

        # 英文关键词提取
        english_keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', combined_text)

        # 中文关键词提取
        chinese_words = jieba.cut(combined_text)
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        chinese_keywords = [word for word in chinese_words if len(word) > 1 and word not in stop_words]

        # 合并并去重
        all_keywords = list(set(english_keywords + chinese_keywords))
        return all_keywords[:15]

    def calculate_importance_score(self, article: Dict) -> int:
        """计算文章重要性分数（考虑翻译质量）"""
        score = 5

        title = article.get('title', '').lower()
        content = article.get('content', '').lower()
        source = article.get('source', '').lower()

        # 重要关键词加分（中英文）
        important_keywords = {
            # 英文关键词
            'fed': 3, 'federal reserve': 3, 'interest rate': 2, 'inflation': 2,
            'gdp': 2, 'unemployment': 2, 'recession': 2, 'earnings': 2,
            'merger': 2, 'acquisition': 2, 'ipo': 2, 'dividend': 1,

            # 中文关键词
            '央行': 3, '利率': 2, 'GDP': 2, 'PMI': 2, '通胀': 2,
            '股市': 2, '基金': 1, '债券': 1, '外汇': 1,
            '政策': 2, '监管': 2, '改革': 2, '创新': 1,
            '业绩': 2, '财报': 2, '并购': 2, '上市': 2, '收益': 1
        }

        for keyword, points in important_keywords.items():
            if keyword in title:
                score += points * 2
            elif keyword in content:
                score += points

        # 翻译质量加分
        if article.get('title_translated') or article.get('content_translated'):
            score += 1  # 翻译内容可能更有价值

        # 数据源权重
        source_weights = {
            'bloomberg': 3,
            'thomson reuters': 2,
            '和讯': 1,
            '中国证券网': 2
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

        return max(1, min(10, score))

    def is_high_quality_content(self, article: Dict) -> bool:
        """判断是否为高质量内容"""
        title = article.get('title', '')
        content = article.get('content', '')
        url = article.get('url', '')

        # 基本质量检查
        if len(content) < self.min_content_length:
            return False

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
                                    # 翻译处理
                                    translated_article = self.process_article_translation(article)

                                    # 计算重要性和提取关键词
                                    translated_article['importance'] = self.calculate_importance_score(translated_article)
                                    translated_article['keywords'] = self.extract_keywords(
                                        translated_article['title'],
                                        translated_article['content']
                                    )

                                    articles.append(translated_article)
                                    print(f"   ✅ 收集: {translated_article['title'][:50]}...")

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

    async def collect_translated_rss_articles(self) -> List[Dict]:
        """收集并翻译RSS源的文章"""
        all_articles = []

        print(f"🚀 开始多语言RSS监控任务（含翻译）")
        print(f"📡 监控 {len(self.rss_feeds)} 个RSS源")
        print(f"🌐 翻译功能: {'开启' if self.translate_english else '关闭'}")
        print("-" * 70)

        connector = aiohttp.TCPConnector(limit=10, limit_per_host=2)
        timeout = aiohttp.ClientTimeout(total=120)  # 增加超时时间给翻译预留时间

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for feed_name, feed_url in self.rss_feeds.items():
                task = self.fetch_rss_feed(session, feed_name, feed_url)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                feed_name = list(self.rss_feeds.keys())[i]
                if isinstance(result, list):
                    all_articles.extend(result)
                    translated_count = sum(1 for a in result if a.get('title_translated') or a.get('content_translated'))
                    print(f"   ✅ {feed_name}: {len(result)} 篇文章 (翻译: {translated_count}篇)")
                else:
                    print(f"   ❌ {feed_name}: {result}")

        # 按重要性和时间排序
        all_articles.sort(key=lambda x: (x['importance'], x['published_time']), reverse=True)

        total_translated = sum(1 for a in all_articles if a.get('title_translated') or a.get('content_translated'))
        print(f"📊 总共收集到 {len(all_articles)} 篇文章，其中 {total_translated} 篇已翻译")

        return all_articles

    def store_articles_to_rag(self, articles: List[Dict]):
        """将翻译后的文章存储到RAG数据库"""
        if not self.collection:
            print("❌ RAG数据库未连接")
            return

        stored_count = 0

        for article in articles:
            try:
                doc_id = f"translated_rss_{hashlib.md5(article['url'].encode()).hexdigest()[:12]}"

                # 检查是否已存在
                try:
                    existing = self.collection.get(ids=[doc_id])
                    if existing['ids']:
                        continue
                except:
                    pass

                # 准备文档内容（包含原文和译文信息）
                document_content = f"""标题: {article['title']}

内容: {article['content']}

摘要: {article['summary']}

关键词: {', '.join(article['keywords'])}

来源: {article['source']}
发布时间: {article['published_time']}"""

                # 如果有翻译，添加原文信息
                if article.get('title_translated'):
                    document_content += f"\n原文标题: {article.get('original_title', '')}"

                if article.get('content_translated'):
                    document_content += f"\n翻译说明: 本文由英文翻译而来"

                # 创建向量
                embedding = self.create_tfidf_vector(document_content)

                # 准备元数据
                metadata = {
                    'source_type': 'translated_rss_news',
                    'source_name': article['source'],
                    'url': article['url'],
                    'timestamp': datetime.now().isoformat(),
                    'published_time': article['published_time'],
                    'importance': article['importance'],
                    'keywords': json.dumps(article['keywords'], ensure_ascii=False),
                    'category': 'multilingual_financial_news',
                    'content_length': len(article['content']),
                    'title_translated': article.get('title_translated', False),
                    'content_translated': article.get('content_translated', False),
                    'detected_language': json.dumps(article.get('detected_language', {}))
                }

                # 存储到ChromaDB
                self.collection.add(
                    documents=[document_content],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    ids=[doc_id]
                )

                stored_count += 1
                translation_note = "📝翻译" if (article.get('title_translated') or article.get('content_translated')) else "📄原文"
                print(f"   ✅ 存储({translation_note}): {article['title'][:40]}...")

            except Exception as e:
                print(f"⚠️ 存储文章失败: {e}")
                continue

        print(f"✅ 成功存储 {stored_count} 篇文章到RAG数据库")

        # 保存到归档
        if articles:
            archive_metadata = {
                'source': 'translated_rss_monitor',
                'collection_name': 'translated_financial_news',
                'stored_count': stored_count,
                'total_articles': len(articles),
                'translated_articles': sum(1 for a in articles if a.get('title_translated') or a.get('content_translated')),
                'feed_sources': list(self.rss_feeds.keys()),
                'translation_enabled': self.translate_english
            }

            self.archive_manager.save_archive(
                data=articles,
                data_type='rss_news',
                metadata=archive_metadata,
                custom_suffix='translated'
            )

    async def run_monitoring_cycle(self):
        """执行一次监控周期"""
        start_time = time.time()

        # 收集并翻译RSS文章
        articles = await self.collect_translated_rss_articles()

        # 存储到RAG数据库
        if articles:
            self.store_articles_to_rag(articles)

        end_time = time.time()
        duration = end_time - start_time

        print(f"⏱️ 监控周期完成，耗时: {duration:.2f} 秒")
        print(f"🔄 下次更新时间: {(datetime.now() + timedelta(minutes=self.update_interval)).strftime('%H:%M:%S')}")
        print("=" * 80)

    def start_monitoring(self):
        """启动翻译RSS监控"""
        if not self.connect_to_chromadb():
            return

        print(f"🎯 多语言RSS监控系统启动")
        print(f"⏰ 更新间隔: {self.update_interval} 分钟")
        print(f"📡 监控源数量: {len(self.rss_feeds)}")
        print(f"🌐 翻译功能: {'开启' if self.translate_english else '关闭'}")
        print("="*80)

        # 立即执行一次
        asyncio.run(self.run_monitoring_cycle())

        # 设置定时任务
        schedule.every(self.update_interval).minutes.do(
            lambda: asyncio.run(self.run_monitoring_cycle())
        )

        print(f"⚡ 多语言RSS定时监控已启动，按 Ctrl+C 停止")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            print(f"\n🛑 多语言RSS监控已停止")

    def run_once(self):
        """运行一次监控（用于测试）"""
        if not self.connect_to_chromadb():
            return

        print(f"🧪 执行一次多语言RSS监控测试")
        asyncio.run(self.run_monitoring_cycle())

def main():
    """主函数"""
    monitor = TranslatedRSSMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        monitor.run_once()
    else:
        monitor.start_monitoring()

if __name__ == "__main__":
    main()