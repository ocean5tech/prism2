#!/usr/bin/env python3
"""
隔离的RSS监控服务
- 只负责RSS数据收集
- 使用独立翻译服务
- 生成JSON格式数据供RAG消费
- 不直接依赖ChromaDB
"""

import asyncio
import aiohttp
import feedparser
import json
import os
import hashlib
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
from translation_service import TranslationService

class IsolatedRSSMonitor:
    def __init__(self):
        # 初始化翻译服务
        self.translation_service = TranslationService()

        # RSS源配置 - 使用可用的源进行测试
        self.rss_feeds = {
            'BBC Business': 'http://feeds.bbci.co.uk/news/business/rss.xml',
            'CNN Business': 'http://rss.cnn.com/rss/money_latest.rss',
            'Reuters Business': 'https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best',
            'AP Business': 'https://apnews.com/apf-BusinessNews',
            'Financial Times': 'https://www.ft.com/rss/home',
            # 备用简单测试源
            'Test News': 'https://rss-feed.com/feeds/all.rss.xml'
        }

        # 数据目录
        self.data_dir = "/home/wyatt/prism2/rag-service/rss_data"
        os.makedirs(self.data_dir, exist_ok=True)

        self.stats = {
            'total_articles': 0,
            'successful_translations': 0,
            'failed_translations': 0,
            'cache_hits': 0,
            'rss_errors': 0
        }

    async def fetch_rss_content(self, source_name: str, url: str) -> List[Dict]:
        """获取RSS内容"""
        articles = []

        try:
            print(f"🔍 获取RSS源: {source_name}")

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={'User-Agent': 'Mozilla/5.0 (compatible; RSSBot/1.0)'}
            ) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)

                        print(f"   📰 找到 {len(feed.entries)} 篇文章")

                        for entry in feed.entries:
                            article = self._process_entry(entry, source_name)
                            if article:
                                articles.append(article)
                                self.stats['total_articles'] += 1

                    else:
                        print(f"   ❌ HTTP {response.status}")
                        self.stats['rss_errors'] += 1

        except Exception as e:
            print(f"   ❌ RSS源获取失败: {e}")
            self.stats['rss_errors'] += 1

        return articles

    def _process_entry(self, entry, source_name: str) -> Optional[Dict]:
        """处理单个RSS条目"""
        try:
            # 提取基本信息
            title = getattr(entry, 'title', '').strip()
            link = getattr(entry, 'link', '')
            published = getattr(entry, 'published', '')

            # 提取内容
            content = ''
            if hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description

            # 清理HTML标签
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text().strip()

            # 基本验证
            if not title or len(title) < 10:
                return None

            # 生成文档ID
            doc_id = hashlib.md5(f"{link}{title}".encode()).hexdigest()

            # 计算重要性评分（简化版本）
            importance_score = self._calculate_importance_score(title, content)

            return {
                'id': doc_id,
                'title': title,
                'content': content,
                'link': link,
                'source': source_name,
                'published': published,
                'importance_score': importance_score,
                'collected_at': datetime.now().isoformat(),
                'translated': False
            }

        except Exception as e:
            print(f"   ⚠️ 处理条目失败: {e}")
            return None

    def _calculate_importance_score(self, title: str, content: str) -> float:
        """计算文章重要性评分（1-10）"""
        score = 5.0  # 基础分

        # 标题长度权重
        if len(title) > 50:
            score += 0.5
        elif len(title) < 20:
            score -= 0.5

        # 内容长度权重
        if len(content) > 200:
            score += 1.0
        elif len(content) < 50:
            score -= 1.0

        # 关键词权重
        important_keywords = [
            'federal reserve', '央行', '利率', 'interest rate',
            'earnings', '财报', 'revenue', '收益',
            'stock', '股票', 'market', '市场',
            'economy', '经济', 'gdp', 'inflation', '通胀'
        ]

        text_lower = (title + ' ' + content).lower()
        keyword_count = sum(1 for keyword in important_keywords if keyword in text_lower)
        score += keyword_count * 0.5

        # 限制在1-10范围内
        return max(1.0, min(10.0, score))

    def translate_articles(self, articles: List[Dict]) -> List[Dict]:
        """批量翻译文章"""
        translated_articles = []

        for article in articles:
            try:
                # 翻译标题
                title_result = self.translation_service.translate_text(article['title'])
                content_result = self.translation_service.translate_text(article['content'])

                # 更新文章信息
                article['translated_title'] = title_result['translated_text']
                article['translated_content'] = content_result['translated_text']
                article['original_language'] = title_result['detected_language']
                article['translated'] = title_result['translation_needed'] or content_result['translation_needed']

                if title_result['success'] and content_result['success']:
                    self.stats['successful_translations'] += 1
                else:
                    self.stats['failed_translations'] += 1
                    # 记录错误信息
                    if 'error' in title_result:
                        article['translation_error'] = title_result['error']
                    elif 'error' in content_result:
                        article['translation_error'] = content_result['error']

                translated_articles.append(article)

                # 避免翻译API频率限制
                time.sleep(0.1)

            except Exception as e:
                print(f"   ⚠️ 翻译失败: {e}")
                self.stats['failed_translations'] += 1
                article['translation_error'] = str(e)
                translated_articles.append(article)

        return translated_articles

    def save_to_file(self, articles: List[Dict], filename: str = None) -> str:
        """保存数据到JSON文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rss_data_{timestamp}.json"

        filepath = os.path.join(self.data_dir, filename)

        # 准备保存数据
        save_data = {
            'metadata': {
                'collection_time': datetime.now().isoformat(),
                'total_articles': len(articles),
                'sources_count': len(set(article['source'] for article in articles)),
                'translated_articles': sum(1 for article in articles if article.get('translated', False)),
                'stats': self.stats.copy()
            },
            'articles': articles
        }

        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        return filepath

    async def monitor_cycle(self) -> str:
        """执行一次完整的监控周期"""
        print(f"🚀 开始RSS监控任务 - {datetime.now()}")

        all_articles = []

        # 收集所有RSS源
        for source_name, url in self.rss_feeds.items():
            articles = await self.fetch_rss_content(source_name, url)
            all_articles.extend(articles)

        print(f"📊 总共收集到 {len(all_articles)} 篇文章")

        if all_articles:
            # 翻译文章
            print("🔄 开始翻译...")
            translated_articles = self.translate_articles(all_articles)

            # 保存数据
            saved_file = self.save_to_file(translated_articles)
            print(f"💾 数据保存到: {saved_file}")

            # 显示统计信息
            translation_stats = self.translation_service.get_stats()
            print(f"📈 翻译统计: 成功{self.stats['successful_translations']}, 失败{self.stats['failed_translations']}")
            print(f"🎯 缓存命中率: {translation_stats['cache_hit_rate']}")

            return saved_file
        else:
            print("⚠️ 未收集到任何文章")
            return ""

    async def run_continuous_monitoring(self, interval_minutes: int = 15):
        """运行连续监控"""
        print(f"⏰ 启动连续RSS监控，间隔 {interval_minutes} 分钟")

        while True:
            try:
                await self.monitor_cycle()
                print(f"😴 等待 {interval_minutes} 分钟...")
                await asyncio.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("🛑 监控已停止")
                break
            except Exception as e:
                print(f"❌ 监控周期错误: {e}")
                await asyncio.sleep(60)  # 错误后等待1分钟再重试

async def main():
    """主函数"""
    import sys

    monitor = IsolatedRSSMonitor()

    if len(sys.argv) > 1:
        if sys.argv[1] == "once":
            # 运行一次
            result = await monitor.monitor_cycle()
            print(f"✅ 完成，保存在: {result}")
        elif sys.argv[1] == "continuous":
            # 连续运行
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 15
            await monitor.run_continuous_monitoring(interval)
        else:
            print("用法: python3 isolated_rss_monitor.py [once|continuous [interval_minutes]]")
    else:
        # 默认运行一次
        result = await monitor.monitor_cycle()
        print(f"✅ 完成，保存在: {result}")

if __name__ == "__main__":
    asyncio.run(main())