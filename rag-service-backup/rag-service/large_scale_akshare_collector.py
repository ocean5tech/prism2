#!/usr/bin/env python3
"""
大规模AKShare数据收集器
专注于A股行业数据收集：计算机、芯片、有色金属等
"""

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import chromadb
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import jieba

class LargeScaleAKShareCollector:
    """大规模AKShare数据收集器"""

    def __init__(self):
        self.vectorizer = None
        self.client = None
        self.collection = None

    async def __aenter__(self):
        print("🚀 初始化大规模AKShare数据收集系统...")

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

        print("✅ 大规模数据收集系统初始化完成")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def collect_sector_stocks_comprehensive(self) -> List[Dict]:
        """全面收集A股行业股票数据"""
        print("📊 开始全面收集A股行业股票数据...")

        try:
            import akshare as ak
            print("✅ AKShare模块加载成功")

            collected_docs = []

            # 扩大的股票池
            sectors = {
                '计算机': {
                    'stocks': ['002230', '000938', '002415', '300014', '000977', '600570', '300496', '002353'],
                    'name': '计算机软件'
                },
                '芯片半导体': {
                    'stocks': ['000725', '002049', '002938', '688981', '688012', '002371', '300661'],
                    'name': '半导体芯片'
                },
                '有色金属': {
                    'stocks': ['000831', '002460', '600362', '000878', '600219', '600111', '000629'],
                    'name': '有色金属'
                },
                '新能源': {
                    'stocks': ['300750', '002594', '300274', '300450', '002129', '600884'],
                    'name': '新能源汽车'
                },
                '人工智能': {
                    'stocks': ['300229', '002253', '000063', '002410', '300243', '300383'],
                    'name': '人工智能'
                }
            }

            for sector_key, sector_info in sectors.items():
                print(f"   收集{sector_info['name']}行业股票数据...")

                for stock_code in sector_info['stocks']:
                    try:
                        # 获取股票基本信息
                        stock_info = ak.stock_zh_a_hist(
                            symbol=stock_code,
                            period="daily",
                            start_date="20241001",
                            end_date="20241101"
                        )

                        if not stock_info.empty:
                            latest_data = stock_info.iloc[-1]

                            # 计算涨跌幅
                            if len(stock_info) > 1:
                                prev_close = stock_info.iloc[-2]['收盘']
                                change_pct = ((latest_data['收盘'] - prev_close) / prev_close) * 100
                            else:
                                change_pct = 0

                            # 获取股票名称
                            try:
                                stock_name_df = ak.stock_zh_a_spot_em()
                                stock_name = stock_name_df[stock_name_df['代码'] == stock_code]['名称'].iloc[0]
                            except:
                                stock_name = f"股票{stock_code}"

                            content = f"{sector_info['name']}龙头股票{stock_name}({stock_code})最新交易分析：收盘价{latest_data.get('收盘', 'N/A')}元，涨跌幅{change_pct:.2f}%，成交量{latest_data.get('成交量', 'N/A')}股，成交额{latest_data.get('成交额', 'N/A')}元。该股属于{sector_info['name']}板块，为{sector_key}领域重要标的，具有较高投资价值和市场关注度。"

                            doc = {
                                'id': f"stock_{sector_key}_{stock_code}_{int(time.time())}",
                                'content': content,
                                'metadata': {
                                    'source': f'AKShare-{sector_info["name"]}',
                                    'doc_type': 'sector_stock_analysis',
                                    'sector': sector_key,
                                    'sector_name': sector_info['name'],
                                    'stock_code': stock_code,
                                    'company_name': stock_name,
                                    'close_price': float(latest_data.get('收盘', 0)),
                                    'volume': int(latest_data.get('成交量', 0)),
                                    'amount': float(latest_data.get('成交额', 0)),
                                    'change_pct': round(change_pct, 2),
                                    'date': str(latest_data.name),
                                    'data_source': 'akshare_comprehensive_stocks',
                                    'importance': 8,
                                    'collection_time': datetime.now().isoformat()
                                }
                            }
                            collected_docs.append(doc)
                            print(f"   ✅ {sector_info['name']}-{stock_name}({stock_code}) 数据收集完成")

                            # 添加延时避免频率限制
                            await asyncio.sleep(0.5)

                    except Exception as e:
                        print(f"   ⚠️ 获取股票{stock_code}数据失败: {e}")

            # 收集行业ETF数据
            print("   收集行业ETF数据...")
            etf_codes = {
                '515050': '5G通信ETF',
                '159995': '芯片ETF',
                '515000': '科技ETF',
                '516970': '计算机ETF',
                '159928': '中证消费ETF'
            }

            for etf_code, etf_name in etf_codes.items():
                try:
                    etf_info = ak.fund_etf_hist_em(symbol=etf_code, period="daily", start_date="20241001", end_date="20241101")
                    if not etf_info.empty:
                        latest_etf = etf_info.iloc[-1]

                        content = f"{etf_name}({etf_code})最新交易数据：净值{latest_etf.get('收盘', 'N/A')}，成交量{latest_etf.get('成交量', 'N/A')}。该ETF跟踪相关行业指数，为投资者提供一站式行业投资工具，具有分散化投资优势。"

                        doc = {
                            'id': f"etf_{etf_code}_{int(time.time())}",
                            'content': content,
                            'metadata': {
                                'source': 'AKShare-行业ETF',
                                'doc_type': 'etf_data',
                                'etf_code': etf_code,
                                'etf_name': etf_name,
                                'net_value': float(latest_etf.get('收盘', 0)),
                                'volume': int(latest_etf.get('成交量', 0)),
                                'data_source': 'akshare_etf',
                                'importance': 7,
                                'collection_time': datetime.now().isoformat()
                            }
                        }
                        collected_docs.append(doc)
                        print(f"   ✅ {etf_name} ETF数据收集完成")

                except Exception as e:
                    print(f"   ⚠️ 获取ETF{etf_code}数据失败: {e}")

            print(f"✅ 全面股票数据收集完成，共获取 {len(collected_docs)} 个文档")
            return collected_docs

        except ImportError:
            print("❌ AKShare未安装")
            return []
        except Exception as e:
            print(f"❌ 股票数据收集失败: {e}")
            return []

    async def collect_comprehensive_news(self) -> List[Dict]:
        """收集全面财经新闻"""
        print("📰 开始收集全面财经新闻...")

        try:
            import akshare as ak
            collected_docs = []

            # 1. 央视财经新闻
            print("   收集央视财经新闻...")
            try:
                news_data = ak.news_cctv()
                if not news_data.empty:
                    for _, news in news_data.head(15).iterrows():  # 增加到15条
                        doc = {
                            'id': f"news_cctv_{int(time.time())}_{len(collected_docs)}",
                            'content': f"{news.get('title', '')} {news.get('content', '')}",
                            'metadata': {
                                'source': '央视财经',
                                'doc_type': 'financial_news',
                                'news_type': '宏观财经',
                                'title': news.get('title', ''),
                                'publish_date': str(news.get('date', datetime.now().date())),
                                'data_source': 'akshare_cctv_news',
                                'importance': 9,
                                'collection_time': datetime.now().isoformat()
                            }
                        }
                        collected_docs.append(doc)
                    print(f"   ✅ 央视财经新闻: {len(news_data.head(15))} 条")
            except Exception as e:
                print(f"   ⚠️ 央视新闻获取失败: {e}")

            # 2. 获取宏观经济数据新闻
            print("   生成宏观经济分析...")
            try:
                # PMI数据
                pmi_data = ak.macro_china_pmi()
                if not pmi_data.empty:
                    latest_pmi = pmi_data.iloc[-1]
                    content = f"中国制造业PMI指数分析：{latest_pmi.get('月份', 'N/A')}月PMI为{latest_pmi.get('PMI', 'N/A')}，制造业景气度{'扩张' if float(latest_pmi.get('PMI', 50)) > 50 else '收缩'}。PMI作为经济先行指标，直接影响股市投资情绪，特别是制造业相关板块如有色金属、机械设备等。当前数据显示制造业运行态势，为投资决策提供重要参考。"

                    doc = {
                        'id': f"macro_pmi_analysis_{int(time.time())}",
                        'content': content,
                        'metadata': {
                            'source': 'AKShare-宏观分析',
                            'doc_type': 'macro_analysis',
                            'indicator': 'PMI制造业指数',
                            'value': str(latest_pmi.get('PMI', '')),
                            'period': str(latest_pmi.get('月份', '')),
                            'data_source': 'akshare_macro_analysis',
                            'importance': 9,
                            'collection_time': datetime.now().isoformat()
                        }
                    }
                    collected_docs.append(doc)
                    print(f"   ✅ PMI宏观分析完成")
            except Exception as e:
                print(f"   ⚠️ 宏观数据分析失败: {e}")

            # 3. 生成行业分析报告
            print("   生成行业分析报告...")
            sector_analyses = [
                {
                    'sector': '人工智能',
                    'content': '人工智能产业迎来政策利好，大模型技术不断突破，算力需求激增。相关上市公司包括科大讯飞、商汤科技等在AI应用落地方面取得重要进展。投资者应关注具备核心技术的龙头企业，重点布局算力基础设施、AI应用软件等细分领域。',
                    'importance': 9
                },
                {
                    'sector': '芯片半导体',
                    'content': '国内芯片产业链加速发展，政策扶持力度加大。设计、制造、封测等各环节均有所突破。重点关注具备自主知识产权的芯片设计公司，如韦尔股份、澜起科技等。随着国产替代进程加速，相关标的具备长期投资价值。',
                    'importance': 8
                },
                {
                    'sector': '新能源汽车',
                    'content': '新能源汽车销量持续增长，产业链日趋成熟。电池技术不断进步，充电基础设施加快建设。宁德时代、比亚迪等龙头企业市场地位稳固。投资机会主要集中在电池材料、智能驾驶、充电设施等细分赛道。',
                    'importance': 8
                }
            ]

            for analysis in sector_analyses:
                doc = {
                    'id': f"sector_analysis_{analysis['sector']}_{int(time.time())}",
                    'content': f"{analysis['sector']}行业投资分析：{analysis['content']}",
                    'metadata': {
                        'source': '行业研究分析',
                        'doc_type': 'sector_analysis',
                        'sector': analysis['sector'],
                        'analysis_type': '投资策略',
                        'data_source': 'sector_analysis_report',
                        'importance': analysis['importance'],
                        'collection_time': datetime.now().isoformat()
                    }
                }
                collected_docs.append(doc)

            print(f"✅ 全面财经新闻收集完成，共获取 {len(collected_docs)} 个文档")
            return collected_docs

        except Exception as e:
            print(f"❌ 财经新闻收集失败: {e}")
            return []

    def store_documents_to_vector_db(self, documents: List[Dict]) -> int:
        """批量存储文档到向量数据库"""
        if not documents:
            return 0

        print(f"🧠 开始大规模向量化存储 {len(documents)} 个文档...")

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

            # 分批存储避免一次性存储过多
            batch_size = 50
            total_stored = 0

            for i in range(0, len(documents), batch_size):
                batch_texts = texts[i:i+batch_size]
                batch_ids = doc_ids[i:i+batch_size]
                batch_metadatas = metadatas[i:i+batch_size]
                batch_embeddings = embeddings[i:i+batch_size]

                print(f"   💾 存储批次 {i//batch_size + 1}: {len(batch_texts)} 个文档...")

                self.collection.add(
                    embeddings=batch_embeddings.tolist(),
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )

                total_stored += len(batch_texts)
                time.sleep(1)  # 避免频率限制

            print(f"✅ 成功存储 {total_stored} 个文档到向量数据库")
            return total_stored

        except Exception as e:
            print(f"❌ 向量化存储失败: {e}")
            import traceback
            traceback.print_exc()
            return 0

    async def collect_all_large_scale_data(self) -> List[Dict]:
        """收集所有大规模数据"""
        print("🚀 开始大规模数据收集...")
        start_time = time.time()

        all_docs = []

        # 1. 全面股票数据
        stock_docs = await self.collect_sector_stocks_comprehensive()
        all_docs.extend(stock_docs)

        # 2. 全面财经新闻
        news_docs = await self.collect_comprehensive_news()
        all_docs.extend(news_docs)

        total_time = time.time() - start_time

        print(f"\n🎉 大规模数据收集完成!")
        print(f"   📊 总文档数: {len(all_docs)}")
        print(f"   ⏱️ 总耗时: {total_time:.2f} 秒")
        print(f"   📄 数据分布:")
        print(f"      - 股票数据: {len(stock_docs)} 个")
        print(f"      - 财经新闻: {len(news_docs)} 个")

        # 向量化存储
        if all_docs:
            print(f"\n🧠 开始大规模向量化存储...")
            stored_count = self.store_documents_to_vector_db(all_docs)
            print(f"✅ 大规模向量化存储完成: {stored_count}/{len(all_docs)} 个文档")

        return all_docs

    def get_test_stocks(self) -> List[Dict]:
        """提供测试用的股票例子"""
        test_stocks = [
            {
                'code': '002230',
                'name': '科大国创',
                'sector': '计算机',
                'description': '国内领先的智能语音和人工智能技术公司'
            },
            {
                'code': '000725',
                'name': '京东方A',
                'sector': '芯片半导体',
                'description': '全球领先的半导体显示技术公司'
            },
            {
                'code': '002460',
                'name': '赣锋锂业',
                'sector': '有色金属',
                'description': '全球领先的锂化合物生产商'
            },
            {
                'code': '300750',
                'name': '宁德时代',
                'sector': '新能源',
                'description': '全球动力电池行业领军企业'
            },
            {
                'code': '300229',
                'name': '拓尔思',
                'sector': '人工智能',
                'description': '专业的人工智能和大数据技术服务商'
            }
        ]
        return test_stocks

async def test_large_scale_pipeline():
    """测试大规模数据管道"""
    print("🧪 测试大规模AKShare数据管道")
    print("=" * 80)

    async with LargeScaleAKShareCollector() as collector:
        # 收集大规模数据
        all_docs = await collector.collect_all_large_scale_data()

        if all_docs:
            # 保存数据
            output_file = f"/home/wyatt/prism2/rag-service/large_scale_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_docs, f, ensure_ascii=False, indent=2)
            print(f"💾 大规模数据已保存到: {output_file}")

            # 验证数据库
            count = collector.collection.count()
            print(f"\n📊 最终数据库统计: {count} 个文档")

            # 提供测试股票
            test_stocks = collector.get_test_stocks()
            print(f"\n🎯 RAG测试用股票例子:")
            print("=" * 50)
            for stock in test_stocks:
                print(f"📄 {stock['name']}({stock['code']})")
                print(f"   行业: {stock['sector']}")
                print(f"   描述: {stock['description']}")
                print(f"   测试查询示例: '{stock['name']}', '股票{stock['code']}', '{stock['sector']}行业'")
                print("-" * 40)

            return all_docs, test_stocks
        else:
            print("❌ 没有收集到数据")
            return [], []

if __name__ == "__main__":
    asyncio.run(test_large_scale_pipeline())