#!/usr/bin/env python3
"""
简化版RSS监控系统
演示财经RSS监控功能和RAG数据库更新
"""

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import chromadb
import json
from datetime import datetime, timedelta
from typing import List, Dict
import hashlib
import time
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
import random
from archive_manager import ArchiveManager

class SimpleRSSMonitor:
    def __init__(self):
        # Clear proxy variables
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        self.client = None
        self.collection = None
        self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        self.archive_manager = ArchiveManager()

        # 模拟财经新闻数据
        self.mock_news_templates = [
            {
                'title': '央行宣布下调存款准备金率0.5个百分点',
                'content': '中国人民银行决定于2025年1月15日下调金融机构存款准备金率0.5个百分点，释放长期资金约1万亿元。此次降准旨在保持银行体系流动性合理充裕，支持实体经济发展。市场分析认为，这将有利于降低银行资金成本，引导贷款利率进一步下行，对股市构成利好。',
                'source': '央视财经',
                'importance': 9,
                'keywords': ['央行', '降准', '流动性', '实体经济', '利好']
            },
            {
                'title': '科技股集体大涨，AI板块再现涨停潮',
                'content': '今日A股市场科技股表现强劲，人工智能、芯片、软件等板块全线上涨。其中AI概念股涨幅居前，多只个股涨停。分析师认为，随着AI技术不断突破和应用场景扩大，相关上市公司有望迎来业绩和估值双重提升。投资者应关注具备核心技术和商业化能力的优质标的。',
                'source': '证券时报',
                'importance': 8,
                'keywords': ['科技股', 'AI', '涨停', '芯片', '投资机会']
            },
            {
                'title': '新能源汽车销量创新高，产业链公司受益',
                'content': '据中汽协数据显示，2024年新能源汽车销量同比增长35%，创历史新高。动力电池、充电桩、智能驾驶等产业链各环节均实现快速发展。机构预测，随着技术进步和成本下降，新能源汽车渗透率将持续提升，相关产业链公司长期成长空间广阔。',
                'source': '第一财经',
                'importance': 7,
                'keywords': ['新能源汽车', '销量', '产业链', '动力电池', '成长空间']
            },
            {
                'title': '房地产政策持续优化，一线城市成交量回升',
                'content': '近期多个一线城市进一步优化房地产调控政策，包括降低首付比例、放宽购房限制等措施。数据显示，政策调整后一线城市新房和二手房成交量均有明显回升。业内专家表示，政策支持有助于房地产市场企稳回升，但仍需关注后续政策执行情况。',
                'source': '经济日报',
                'importance': 6,
                'keywords': ['房地产', '政策优化', '成交量', '一线城市', '企稳']
            },
            {
                'title': '消费数据向好，内需潜力持续释放',
                'content': '国家统计局公布的最新数据显示，社会消费品零售总额同比增长7.8%，消费市场呈现稳步回升态势。其中，服务消费、绿色消费、数字消费等新兴消费领域表现突出。专家认为，随着促消费政策持续发力，内需市场潜力将进一步释放，为经济增长提供重要支撑。',
                'source': '新华财经',
                'importance': 7,
                'keywords': ['消费数据', '内需', '零售总额', '新兴消费', '经济增长']
            }
        ]

    def connect_to_chromadb(self):
        """连接到ChromaDB"""
        try:
            self.client = chromadb.HttpClient(host='localhost', port=8000)
            self.client.heartbeat()

            collection_name = "financial_rss_news"
            try:
                # 尝试删除旧集合以避免维度冲突
                try:
                    old_collection = self.client.get_collection(collection_name)
                    self.client.delete_collection(collection_name)
                    print("🗑️ 清理旧集合")
                except:
                    pass

                # 创建新集合
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": "Financial RSS news documents"}
                )
                print("📁 创建新集合")

            except Exception as e:
                print(f"集合操作失败: {e}")
                return False

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
                all_texts = [self.chinese_tokenize(template['content']) for template in self.mock_news_templates]
                all_texts.append(processed_text)
                self.vectorizer.fit(all_texts)
                vector = self.vectorizer.transform([processed_text])
                return vector.toarray()[0].tolist()
        except Exception as e:
            print(f"⚠️ 向量化失败: {e}")
            return [0.0] * 1000

    def generate_mock_articles(self, count: int = 3) -> List[Dict]:
        """生成模拟新闻文章"""
        articles = []

        for i in range(count):
            # 随机选择模板
            template = random.choice(self.mock_news_templates)

            # 添加时间变化
            pub_time = datetime.now() - timedelta(hours=random.randint(0, 12))

            article = {
                'title': template['title'],
                'content': template['content'],
                'url': f"https://finance.example.com/news/{random.randint(100000, 999999)}",
                'source': template['source'],
                'published_time': pub_time.isoformat(),
                'importance': template['importance'],
                'keywords': template['keywords'],
                'summary': template['content'][:100] + '...'
            }

            articles.append(article)

        return articles

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
                        continue
                except:
                    pass

                # 准备文档内容
                document_content = f"""标题: {article['title']}

内容: {article['content']}

关键词: {', '.join(article['keywords'])}

来源: {article['source']}"""

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
                print(f"   ✅ 存储: {article['title'][:30]}...")

            except Exception as e:
                print(f"⚠️ 存储文章失败: {e}")
                continue

        print(f"✅ 成功存储 {stored_count} 篇新文章到RAG数据库")

        # 保存到归档
        if articles:
            archive_metadata = {
                'source': 'rss_monitor',
                'collection_name': 'financial_rss_news',
                'stored_count': stored_count,
                'total_articles': len(articles)
            }

            self.archive_manager.save_archive(
                data=articles,
                data_type='rss_news',
                metadata=archive_metadata
            )

    def simulate_monitoring_cycle(self, article_count: int = 5):
        """模拟一次监控周期"""
        print(f"🚀 开始RSS监控模拟")
        print(f"📡 模拟收集 {article_count} 篇财经新闻")
        print("-" * 60)

        start_time = time.time()

        # 生成模拟文章
        articles = self.generate_mock_articles(article_count)

        print(f"📰 生成了 {len(articles)} 篇模拟新闻:")
        for i, article in enumerate(articles, 1):
            print(f"   {i}. {article['title']} (重要性: {article['importance']}/10)")

        print(f"\n💾 开始存储到RAG数据库...")

        # 存储到RAG数据库
        self.store_articles_to_rag(articles)

        end_time = time.time()
        duration = end_time - start_time

        print(f"\n⏱️ 监控周期完成，耗时: {duration:.2f} 秒")
        print(f"📊 本次更新统计:")
        print(f"   - 新增文章: {len(articles)} 篇")
        print(f"   - 平均重要性: {sum(a['importance'] for a in articles) / len(articles):.1f}/10")
        print(f"   - 时间范围: 最近12小时内")

    def show_database_status(self):
        """显示数据库状态"""
        if not self.collection:
            print("❌ RAG数据库未连接")
            return

        try:
            count = self.collection.count()
            print(f"\n📊 RAG数据库状态:")
            print(f"   - 总文档数: {count}")

            if count > 0:
                # 获取最近的文档
                results = self.collection.get(
                    limit=5,
                    include=['documents', 'metadatas']
                )

                print(f"   - 最近文档预览:")
                for i, doc_id in enumerate(results['ids'][:3]):
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
                    doc_content = results['documents'][i] if results['documents'] else ''

                    title = doc_content.split('\n')[0].replace('标题: ', '') if doc_content else 'Unknown'
                    source = metadata.get('source_name', 'Unknown')
                    importance = metadata.get('importance', 'N/A')

                    print(f"     {i+1}. {title[:40]}... (来源: {source}, 重要性: {importance})")

        except Exception as e:
            print(f"❌ 获取数据库状态失败: {e}")

def main():
    """主函数"""
    print("🎯 RSS监控系统演示")
    print("="*60)

    monitor = SimpleRSSMonitor()

    if not monitor.connect_to_chromadb():
        return

    # 显示当前数据库状态
    monitor.show_database_status()

    print(f"\n" + "="*60)

    # 运行模拟监控
    if len(sys.argv) > 1:
        try:
            article_count = int(sys.argv[1])
        except ValueError:
            article_count = 5
    else:
        article_count = 5

    monitor.simulate_monitoring_cycle(article_count)

    # 显示更新后的数据库状态
    print(f"\n" + "="*60)
    monitor.show_database_status()

    print(f"\n🎉 RSS监控演示完成!")
    print(f"💡 实际使用时，可以:")
    print(f"   - 配置真实的RSS源")
    print(f"   - 设置定时任务(如每30分钟)")
    print(f"   - 添加内容质量过滤")
    print(f"   - 实现增量更新策略")

if __name__ == "__main__":
    main()