#!/usr/bin/env python3
"""
高价值RAG构建器
专注收集真正有投资价值的深度内容
避免噪音数据，构建高质量的投资决策支持系统
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

class HighValueRAGBuilder:
    """高价值RAG构建器"""

    def __init__(self):
        self.vectorizer = None
        self.client = None
        self.collection = None
        self.high_value_docs = []

    async def __aenter__(self):
        print("🎯 初始化高价值RAG构建系统...")
        print("目标：构建真正有投资价值的知识库")

        # 清理代理变量
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]

        # 初始化向量化器
        self.vectorizer = TfidfVectorizer(
            max_features=768,
            analyzer='word',
            tokenizer=lambda x: jieba.lcut(x),
            token_pattern=None,
            lowercase=False,
            stop_words=None
        )

        # 连接ChromaDB
        print("🔗 连接到ChromaDB...")
        self.client = chromadb.HttpClient(host='localhost', port=8000)
        self.client.heartbeat()

        try:
            self.client.delete_collection("financial_documents")
            print("   🗑️ 清理旧数据")
        except:
            pass

        self.collection = self.client.create_collection("financial_documents")
        print("✅ 高价值RAG系统初始化完成")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def collect_company_fundamentals(self) -> List[Dict]:
        """收集公司基本面深度分析"""
        print("🏢 收集公司基本面深度分析...")

        try:
            import akshare as ak
            fundamental_docs = []

            # 重点关注的优质公司
            key_companies = {
                '002230': {'name': '科大讯飞', 'industry': 'AI语音', 'theme': '人工智能龙头'},
                '000725': {'name': '京东方A', 'industry': '显示面板', 'theme': '半导体显示'},
                '002460': {'name': '赣锋锂业', 'industry': '锂电材料', 'theme': '新能源材料'},
                '300750': {'name': '宁德时代', 'industry': '动力电池', 'theme': '新能源龙头'},
                '300229': {'name': '拓尔思', 'industry': '大数据', 'theme': 'AI+大数据'}
            }

            for stock_code, info in key_companies.items():
                try:
                    print(f"   分析 {info['name']} 基本面...")

                    # 获取财务数据
                    financial_data = ak.stock_financial_em(symbol=stock_code)

                    if not financial_data.empty:
                        latest_data = financial_data.iloc[0]

                        # 构建有价值的基本面分析
                        content = f"""
{info['name']}({stock_code}) 基本面深度分析

【公司概况】
{info['name']}是{info['industry']}领域的{info['theme']}企业，在行业中具有重要地位。

【财务健康度分析】
营业收入：{latest_data.get('营业收入', 'N/A')}万元
净利润：{latest_data.get('净利润', 'N/A')}万元
净资产收益率：{latest_data.get('净资产收益率', 'N/A')}%
资产负债率：{latest_data.get('资产负债率', 'N/A')}%
销售净利率：{latest_data.get('销售净利率', 'N/A')}%

【财务质量评估】
1. 盈利能力：{self.assess_profitability(latest_data)}
2. 偿债能力：{self.assess_solvency(latest_data)}
3. 成长性：{self.assess_growth_potential(info['industry'])}
4. 运营效率：{self.assess_operational_efficiency(latest_data)}

【投资亮点】
{self.generate_investment_highlights(info)}

【风险因素】
{self.generate_risk_factors(info)}

【投资建议】
基于基本面分析，该公司{self.generate_investment_recommendation(info)}
                        """.strip()

                        doc = {
                            'id': f"fundamental_analysis_{stock_code}_{int(time.time())}",
                            'content': content,
                            'metadata': {
                                'source': f'基本面研究-{info["name"]}',
                                'doc_type': 'fundamental_analysis',
                                'stock_code': stock_code,
                                'company_name': info['name'],
                                'industry': info['industry'],
                                'analysis_type': '深度基本面分析',
                                'data_source': 'akshare_financial_em',
                                'importance': 9,
                                'content_type': 'investment_analysis'
                            }
                        }
                        fundamental_docs.append(doc)
                        print(f"   ✅ {info['name']} 基本面分析完成")

                except Exception as e:
                    print(f"   ⚠️ {info['name']} 基本面分析失败: {e}")

                await asyncio.sleep(2)  # 避免API频率限制

            print(f"✅ 公司基本面分析完成: {len(fundamental_docs)} 篇")
            return fundamental_docs

        except Exception as e:
            print(f"❌ 基本面分析收集失败: {e}")
            return []

    def assess_profitability(self, data) -> str:
        """评估盈利能力"""
        try:
            roe = float(data.get('净资产收益率', 0))
            margin = float(data.get('销售净利率', 0))

            if roe > 15 and margin > 10:
                return "优秀，ROE和净利率均处于行业领先水平"
            elif roe > 10 and margin > 5:
                return "良好，盈利能力稳健"
            else:
                return "一般，需关注盈利能力改善"
        except:
            return "数据不足，需进一步分析"

    def assess_solvency(self, data) -> str:
        """评估偿债能力"""
        try:
            debt_ratio = float(data.get('资产负债率', 0))

            if debt_ratio < 40:
                return "优秀，财务杠杆较低，偿债压力小"
            elif debt_ratio < 60:
                return "良好，债务结构合理"
            else:
                return "需关注，债务水平较高"
        except:
            return "数据不足，需进一步分析"

    def assess_growth_potential(self, industry) -> str:
        """评估成长潜力"""
        growth_sectors = {
            'AI语音': '人工智能行业处于快速发展期，语音技术应用场景不断拓展',
            '显示面板': '新型显示技术升级，OLED、Mini LED等高端产品需求增长',
            '锂电材料': '新能源汽车爆发式增长，锂电材料需求强劲',
            '动力电池': '全球电动化趋势确定，动力电池市场空间巨大',
            '大数据': '数字经济发展，大数据和AI应用需求持续增长'
        }
        return growth_sectors.get(industry, '行业前景需进一步分析')

    def assess_operational_efficiency(self, data) -> str:
        """评估运营效率"""
        return "需结合更多运营指标综合评估，包括存货周转率、应收账款周转率等"

    def generate_investment_highlights(self, info) -> str:
        """生成投资亮点"""
        highlights = {
            'AI语音': '1.技术壁垒深厚 2.生态布局完善 3.政策支持明确',
            '显示面板': '1.产能规模领先 2.技术持续升级 3.下游需求稳定',
            '锂电材料': '1.资源储备丰富 2.产业链一体化 3.全球化布局',
            '动力电池': '1.技术领先优势 2.客户资源优质 3.规模效应显著',
            '大数据': '1.技术积累深厚 2.行业应用广泛 3.AI赋能效果明显'
        }
        return highlights.get(info['industry'], '需深入研究具体投资亮点')

    def generate_risk_factors(self, info) -> str:
        """生成风险因素"""
        risks = {
            'AI语音': '技术迭代风险、竞争加剧、政策变化',
            '显示面板': '周期性波动、技术替代、产能过剩',
            '锂电材料': '原材料价格波动、技术路线变化、环保政策',
            '动力电池': '技术迭代、客户集中、安全性要求',
            '大数据': '数据安全、隐私保护、技术更新'
        }
        return risks.get(info['industry'], '需识别行业特定风险')

    def generate_investment_recommendation(self, info) -> str:
        """生成投资建议"""
        recommendations = {
            'AI语音': '建议长期关注，在AI产业爆发期具备较强的投资价值',
            '显示面板': '建议关注行业周期底部的投资机会',
            '锂电材料': '建议重点配置，受益于新能源产业长期发展',
            '动力电池': '建议核心持有，全球电动化龙头标的',
            '大数据': '建议关注AI应用落地带来的业绩增长'
        }
        return recommendations.get(info['industry'], '需结合市场环境制定投资策略')

    async def collect_industry_research(self) -> List[Dict]:
        """收集行业研究报告"""
        print("🏭 收集深度行业研究...")

        try:
            import akshare as ak
            research_docs = []

            # 获取行业资金流向分析
            try:
                print("   分析行业资金流向...")
                industry_flow = ak.stock_sector_fund_flow_rank(indicator="今日")

                if not industry_flow.empty:
                    # 取资金净流入前5的行业
                    top_industries = industry_flow.head(5)

                    content = f"""
行业资金流向深度分析报告

【数据时间】{datetime.now().strftime('%Y年%m月%d日')}

【核心发现】
今日资金净流入前五大行业显示市场偏好趋势：

"""
                    for idx, row in top_industries.iterrows():
                        sector = row.get('行业', '未知行业')
                        net_inflow = row.get('净流入', 0)
                        content += f"""
{idx+1}. {sector}
   净流入资金：{net_inflow}万元
   市场判断：{self.analyze_sector_flow(sector, net_inflow)}
"""

                    content += f"""

【投资策略分析】
1. 资金流向反映：当前市场对{top_industries.iloc[0]['行业']}等行业信心较强
2. 配置建议：关注资金持续流入的优质赛道
3. 风险提示：短期资金流向存在波动，需结合基本面分析

【后市展望】
结合行业基本面和资金流向，建议重点关注具备长期成长逻辑且获得资金青睐的行业龙头标的。
                    """.strip()

                    doc = {
                        'id': f"industry_flow_analysis_{int(time.time())}",
                        'content': content,
                        'metadata': {
                            'source': '行业资金流向研究',
                            'doc_type': 'industry_flow_analysis',
                            'analysis_date': datetime.now().strftime('%Y%m%d'),
                            'top_sector': top_industries.iloc[0]['行业'],
                            'data_source': 'akshare_sector_fund_flow',
                            'importance': 8,
                            'content_type': 'market_analysis'
                        }
                    }
                    research_docs.append(doc)
                    print("   ✅ 行业资金流向分析完成")

            except Exception as e:
                print(f"   ⚠️ 行业资金流向分析失败: {e}")

            # 获取概念板块表现分析
            try:
                print("   分析热点概念板块...")
                concept_rank = ak.stock_board_concept_name_em()

                if not concept_rank.empty:
                    hot_concepts = concept_rank.head(10)

                    content = f"""
热点概念板块深度追踪报告

【市场热点概念分析】
当前市场关注的前十大概念板块：

"""
                    for idx, row in hot_concepts.iterrows():
                        concept = row.get('板块名称', '未知概念')
                        content += f"{idx+1}. {concept} - {self.analyze_concept_potential(concept)}\n"

                    content += f"""

【投资逻辑分析】
1. 概念轮动特征：当前市场呈现明显的主题投资特征
2. 持续性判断：需关注概念是否具备基本面支撑
3. 参与策略：建议关注有实质业务的概念龙头

【风险提示】
概念板块波动较大，投资需谨慎，建议以基本面为本，概念为辅的投资策略。
                    """.strip()

                    doc = {
                        'id': f"concept_analysis_{int(time.time())}",
                        'content': content,
                        'metadata': {
                            'source': '概念板块研究',
                            'doc_type': 'concept_analysis',
                            'hot_concepts': [row['板块名称'] for _, row in hot_concepts.iterrows()],
                            'data_source': 'akshare_concept_board',
                            'importance': 7,
                            'content_type': 'theme_analysis'
                        }
                    }
                    research_docs.append(doc)
                    print("   ✅ 概念板块分析完成")

            except Exception as e:
                print(f"   ⚠️ 概念板块分析失败: {e}")

            print(f"✅ 行业研究完成: {len(research_docs)} 篇")
            return research_docs

        except Exception as e:
            print(f"❌ 行业研究收集失败: {e}")
            return []

    def analyze_sector_flow(self, sector: str, net_inflow: float) -> str:
        """分析行业资金流向"""
        if net_inflow > 100000:  # 10亿以上
            return "强烈看好，大资金持续流入"
        elif net_inflow > 50000:  # 5亿以上
            return "积极关注，资金流入明显"
        elif net_inflow > 0:
            return "温和看好，小幅资金流入"
        else:
            return "谨慎观望，存在资金流出"

    def analyze_concept_potential(self, concept: str) -> str:
        """分析概念潜力"""
        high_value_concepts = ['人工智能', '新能源', '半导体', '生物医药', '5G']
        medium_value_concepts = ['云计算', '大数据', '物联网', '新材料']

        if any(keyword in concept for keyword in high_value_concepts):
            return "高价值概念，具备长期投资逻辑"
        elif any(keyword in concept for keyword in medium_value_concepts):
            return "中等价值概念，需关注落地情况"
        else:
            return "需深入分析概念的商业化前景"

    async def collect_macro_insights(self) -> List[Dict]:
        """收集宏观经济洞察"""
        print("📊 收集宏观经济深度洞察...")

        try:
            import akshare as ak
            macro_docs = []

            # 获取宏观经济数据并深度分析
            try:
                print("   分析宏观经济指标...")

                # PMI数据分析
                pmi_data = ak.macro_china_pmi()
                if not pmi_data.empty:
                    latest_pmi = pmi_data.iloc[-1]
                    pmi_value = latest_pmi.get('PMI', 50)

                    content = f"""
中国宏观经济景气度深度分析

【PMI指标解读】
最新PMI数据：{pmi_value}
数据时间：{latest_pmi.get('月份', '未知月份')}

【经济景气度判断】
{self.interpret_pmi(pmi_value)}

【对股市影响分析】
1. 制造业影响：PMI数据直接反映制造业景气程度，影响周期股表现
2. 货币政策预期：PMI数据影响央行货币政策预期，进而影响市场流动性
3. 行业轮动：不同PMI水平下，各行业表现分化明显

【投资策略建议】
基于当前PMI水平，建议：
{self.generate_pmi_strategy(pmi_value)}

【风险提示】
宏观数据存在滞后性，需结合其他先行指标综合判断经济走势。
                    """.strip()

                    doc = {
                        'id': f"macro_pmi_analysis_{int(time.time())}",
                        'content': content,
                        'metadata': {
                            'source': '宏观经济研究',
                            'doc_type': 'macro_analysis',
                            'indicator': 'PMI',
                            'pmi_value': float(pmi_value),
                            'analysis_period': str(latest_pmi.get('月份', '')),
                            'data_source': 'akshare_macro_pmi',
                            'importance': 9,
                            'content_type': 'macro_insight'
                        }
                    }
                    macro_docs.append(doc)
                    print("   ✅ PMI深度分析完成")

            except Exception as e:
                print(f"   ⚠️ PMI分析失败: {e}")

            print(f"✅ 宏观洞察完成: {len(macro_docs)} 篇")
            return macro_docs

        except Exception as e:
            print(f"❌ 宏观洞察收集失败: {e}")
            return []

    def interpret_pmi(self, pmi_value: float) -> str:
        """解读PMI数据"""
        try:
            pmi = float(pmi_value)
            if pmi > 52:
                return "经济扩张势头强劲，制造业活动明显回升，利好周期股和价值股"
            elif pmi > 50:
                return "经济温和扩张，制造业保持增长态势，市场情绪相对积极"
            elif pmi > 48:
                return "经济接近荣枯线，制造业活动趋于平稳，需关注政策支持"
            else:
                return "经济收缩压力较大，制造业活动低迷，需警惕下行风险"
        except:
            return "PMI数据异常，需进一步核实"

    def generate_pmi_strategy(self, pmi_value: float) -> str:
        """基于PMI生成投资策略"""
        try:
            pmi = float(pmi_value)
            if pmi > 52:
                return "1.加大周期股配置 2.关注有色金属、钢铁等行业 3.适度增加风险偏好"
            elif pmi > 50:
                return "1.均衡配置周期和成长 2.关注业绩确定性较强的标的 3.保持谨慎乐观"
            else:
                return "1.防御性配置为主 2.关注消费、医药等防御品种 3.降低风险敞口"
        except:
            return "需结合其他指标制定投资策略"

    def store_to_vector_db(self, documents: List[Dict]) -> int:
        """存储到向量数据库"""
        if not documents:
            return 0

        print(f"🧠 向量化存储 {len(documents)} 个高价值文档...")

        try:
            texts = [doc['content'] for doc in documents]
            doc_ids = [doc['id'] for doc in documents]
            metadatas = [doc['metadata'] for doc in documents]

            # 向量化
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            embeddings = tfidf_matrix.toarray()

            print(f"   📊 向量维度: {embeddings.shape[1]}")

            # 存储
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas,
                ids=doc_ids
            )

            print(f"✅ 高价值文档存储完成: {len(documents)} 篇")
            return len(documents)

        except Exception as e:
            print(f"❌ 向量化存储失败: {e}")
            return 0

    async def build_high_value_rag(self) -> List[Dict]:
        """构建高价值RAG系统"""
        print("🚀 开始构建高价值RAG系统...")
        start_time = time.time()

        all_docs = []

        # 1. 公司基本面深度分析
        fundamental_docs = await self.collect_company_fundamentals()
        all_docs.extend(fundamental_docs)

        # 2. 行业研究报告
        industry_docs = await self.collect_industry_research()
        all_docs.extend(industry_docs)

        # 3. 宏观经济洞察
        macro_docs = await self.collect_macro_insights()
        all_docs.extend(macro_docs)

        total_time = time.time() - start_time

        print(f"\n🎉 高价值内容收集完成!")
        print(f"   📊 总文档数: {len(all_docs)}")
        print(f"   ⏱️ 耗时: {total_time:.2f} 秒")
        print(f"   📄 内容分布:")
        print(f"      - 基本面分析: {len(fundamental_docs)} 篇")
        print(f"      - 行业研究: {len(industry_docs)} 篇")
        print(f"      - 宏观洞察: {len(macro_docs)} 篇")

        # 存储到向量数据库
        if all_docs:
            stored_count = self.store_to_vector_db(all_docs)
            print(f"✅ 向量化存储: {stored_count}/{len(all_docs)} 个文档")

        # 保存高价值内容
        output_file = f"/home/wyatt/prism2/rag-service/high_value_rag_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_docs, f, ensure_ascii=False, indent=2)
        print(f"💾 高价值内容已保存: {output_file}")

        return all_docs

async def test_high_value_rag():
    """测试高价值RAG构建"""
    print("🧪 测试高价值RAG构建系统")
    print("=" * 80)

    async with HighValueRAGBuilder() as builder:
        high_value_docs = await builder.build_high_value_rag()

        if high_value_docs:
            # 验证数据库
            count = builder.collection.count()
            print(f"\n📊 最终RAG数据库: {count} 个高价值文档")

            print(f"\n✅ 高价值RAG特性:")
            print(f"   - 深度基本面分析：公司财务健康度、投资亮点、风险因素")
            print(f"   - 行业资金流向：市场偏好、投资机会、配置建议")
            print(f"   - 宏观经济洞察：经济景气度、政策影响、投资策略")
            print(f"   - 专业投资逻辑：而非简单的价格数据堆砌")

            return high_value_docs
        else:
            print("❌ 没有构建成功")
            return []

if __name__ == "__main__":
    asyncio.run(test_high_value_rag())