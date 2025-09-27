#!/usr/bin/env python3
"""
创建RAG示例数据用于查看
"""

import sys
import os
sys.path.append('/home/wyatt/prism2/rag-service')

import time

def create_sample_rag_data():
    """创建示例RAG数据"""
    print("🎯 创建RAG示例数据")
    print("=" * 50)

    # Clear proxy variables
    for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
        if proxy_var in os.environ:
            del os.environ[proxy_var]

    try:
        from app.services.vector_service import vector_service
        from app.models.requests import DocumentInput

        # Connect to ChromaDB
        if not vector_service.connect():
            print("❌ 无法连接到ChromaDB")
            return False

        print("✅ 连接到ChromaDB成功")

        # Create sample financial documents
        sample_docs = [
            DocumentInput(
                id="sample_analysis_001",
                content="平安银行三季度净利润390.2亿元，同比增长6.2%。不良贷款率1.05%，较上季度下降5bp。ROE持续提升，资产质量改善明显。维持买入评级，目标价20.5元。",
                metadata={
                    "stock_code": "000001",
                    "company_name": "平安银行",
                    "doc_type": "quarterly_analysis",
                    "source": "券商研报",
                    "publish_date": "2024-10-30",
                    "rating": "买入",
                    "target_price": "20.5",
                    "analyst": "金融分析师",
                    "importance": 9
                }
            ),
            DocumentInput(
                id="sample_policy_news_001",
                content="央行宣布降准0.25个百分点，释放流动性约5000亿元。此次降准体现货币政策前瞻性调节，银行股、地产股等利率敏感板块有望受益。多家机构认为这是政策宽松信号。",
                metadata={
                    "doc_type": "policy_news",
                    "source": "财经新闻",
                    "publish_date": "2024-10-29",
                    "category": "货币政策",
                    "impact_level": "高",
                    "affected_sectors": "银行,地产,科技",
                    "sentiment": "积极",
                    "importance": 8
                }
            ),
            DocumentInput(
                id="sample_ai_research_001",
                content="人工智能产业链迎来发展机遇。AI芯片需求爆发，设计公司订单饱满。云计算厂商受益AI训练需求增长。应用软件企业AI赋能效果显著，用户付费意愿增强。建议重点关注技术领先的龙头企业。",
                metadata={
                    "doc_type": "sector_research",
                    "source": "行业研报",
                    "publish_date": "2024-10-28",
                    "sector": "人工智能",
                    "sub_sectors": "芯片设计,算力服务,应用软件",
                    "investment_theme": "新质生产力",
                    "time_horizon": "长期",
                    "risk_level": "中等",
                    "importance": 7
                }
            ),
            DocumentInput(
                id="sample_market_trend_001",
                content="A股市场呈现结构性行情，新能源、医药、科技等成长板块表现活跃。机构资金持续流入优质赛道。北向资金连续净流入，外资看好中国资产长期价值。建议关注基本面改善的优质成长股。",
                metadata={
                    "doc_type": "market_analysis",
                    "source": "市场分析",
                    "publish_date": "2024-10-27",
                    "market_trend": "结构性行情",
                    "hot_sectors": "新能源,医药,科技",
                    "fund_flow": "净流入",
                    "investment_style": "成长股",
                    "importance": 6
                }
            ),
            DocumentInput(
                id="sample_company_news_001",
                content="比亚迪发布10月销量数据，新能源汽车销量达到30.1万辆，同比增长15.2%。其中纯电动车型销量占比超过60%。公司海外市场拓展顺利，出口量创历史新高。三季度业绩超预期。",
                metadata={
                    "stock_code": "002594",
                    "company_name": "比亚迪",
                    "doc_type": "company_news",
                    "source": "上市公司公告",
                    "publish_date": "2024-11-01",
                    "news_type": "销量数据",
                    "sector": "新能源汽车",
                    "performance": "超预期",
                    "importance": 8
                }
            )
        ]

        # Generate mock embeddings (768 dimensions like bge-large-zh-v1.5)
        embeddings = []
        for i, doc in enumerate(sample_docs):
            # Different document types get different vector patterns
            if "analysis" in doc.metadata.get("doc_type", ""):
                base_vector = [0.1 + i*0.01] * 768
            elif "policy" in doc.metadata.get("doc_type", ""):
                base_vector = [0.2 + i*0.01] * 768
            elif "research" in doc.metadata.get("doc_type", ""):
                base_vector = [0.3 + i*0.01] * 768
            elif "market" in doc.metadata.get("doc_type", ""):
                base_vector = [0.4 + i*0.01] * 768
            else:
                base_vector = [0.5 + i*0.01] * 768

            embeddings.append(base_vector)

        # Store documents
        print(f"📄 准备存储 {len(sample_docs)} 个示例文档...")

        processed_count, failed_docs = vector_service.add_documents(
            documents=sample_docs,
            embeddings=embeddings
        )

        print(f"✅ 存储完成:")
        print(f"   成功: {processed_count} 个文档")
        print(f"   失败: {len(failed_docs)} 个文档")

        if failed_docs:
            print(f"   失败文档: {failed_docs}")

        # Verify storage
        stats = vector_service.get_collection_stats()
        print(f"\n📊 数据库状态:")
        print(f"   集合: {stats['collection_name']}")
        print(f"   文档数: {stats['document_count']}")
        print(f"   状态: {stats['status']}")

        print(f"\n🎉 示例数据创建完成!")
        print(f"现在可以使用 RAG 数据库查看器查看内容")

        return True

    except Exception as e:
        print(f"❌ 创建示例数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    create_sample_rag_data()