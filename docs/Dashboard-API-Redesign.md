# Dashboard API 重新设计方案

## 📋 问题分析

当前Dashboard API存在的问题：
1. **数据过于简单**：只有基本信息、实时价格和1天K线
2. **数据源单一**：主要依赖AKShare，缺乏多源数据整合
3. **缺乏深度分析**：没有AI分析、财务分析、新闻舆情等
4. **K线数据不足**：1天数据无法绘制有意义的图表
5. **缺少关键信息**：没有公告、新闻、龙虎榜、股东信息等

## 🎯 重新设计的Dashboard API

### 📊 综合数据架构

```
Dashboard API = PostgreSQL静态数据 + AKShare实时数据 + RAG AI分析 + 新闻公告数据
```

### 🗂️ 数据分类与来源

#### 1. **PostgreSQL存储的静态数据**
- 📈 **基本信息**：公司名称、行业、市值、股本结构
- 💰 **财务数据**：最近8个季度财报数据
- 👥 **股东信息**：前十大股东、股东变化
- 🏆 **龙虎榜**：历史龙虎榜数据
- 🏢 **公司治理**：管理层信息、公司简介

#### 2. **AKShare实时数据**
- 📊 **实时行情**：价格、涨跌、成交量
- 📈 **K线数据**：日K、周K、月K (60天-2年数据)
- 📰 **最新公告**：当日新发布公告
- 📢 **新闻资讯**：相关新闻和研报
- 💹 **技术指标**：MA、MACD、RSI等

#### 3. **RAG + AI分析数据**
- 🤖 **AI股票评价**：基于财报和新闻的智能分析
- 📊 **投资建议**：买入/卖出/持有建议
- 📈 **趋势分析**：技术面和基本面综合判断
- ⚠️ **风险提示**：潜在风险识别

### 🔧 API设计方案

#### Request Structure
```json
{
  "stock_code": "601169",
  "data_types": [
    "basic_info",      // 基本信息 (PostgreSQL)
    "realtime",        // 实时行情 (AKShare)
    "kline",          // K线数据 (AKShare)
    "financial",       // 财务数据 (PostgreSQL)
    "shareholders",    // 股东信息 (PostgreSQL)
    "longhubang",     // 龙虎榜 (PostgreSQL)
    "announcements",   // 公告信息 (AKShare)
    "news",           // 新闻资讯 (AKShare)
    "ai_analysis"     // AI分析 (RAG Service)
  ],
  "kline_period": "daily",    // 可选：daily/weekly/monthly
  "kline_days": 60,          // 可选：K线天数
  "news_days": 7             // 可选：新闻天数
}
```

#### Response Structure
```json
{
  "success": true,
  "stock_code": "601169",
  "stock_name": "北京银行",
  "timestamp": "2025-09-19T11:00:00Z",
  "data_sources": {
    "postgresql": ["basic_info", "financial", "shareholders", "longhubang"],
    "akshare": ["realtime", "kline", "announcements", "news"],
    "rag_service": ["ai_analysis"]
  },
  "data": {
    "basic_info": {
      "code": "601169",
      "name": "北京银行",
      "market": "SH",
      "industry": "银行",
      "sector": "金融业",
      "market_cap": 120000000000,
      "total_shares": 20000000000,
      "float_shares": 18000000000,
      "pe_ratio": 4.5,
      "pb_ratio": 0.6,
      "dividend_yield": 3.2,
      "listing_date": "2007-09-19"
    },
    "realtime": {
      "current_price": 5.62,
      "change_amount": -0.01,
      "change_percent": -0.18,
      "volume": 1169646,
      "turnover": 655088331.0,
      "high": 5.73,
      "low": 5.55,
      "open": 5.63,
      "prev_close": 5.63,
      "amplitude": 3.2,
      "volume_ratio": 0.85,
      "turnover_rate": 0.65,
      "timestamp": "2025-09-19T11:00:00Z"
    },
    "kline": {
      "period": "daily",
      "days": 60,
      "data": [
        {
          "date": "2025-09-18",
          "open": 5.60,
          "high": 5.75,
          "low": 5.55,
          "close": 5.63,
          "volume": 1200000,
          "turnover": 6750000,
          "change_percent": 0.54
        }
        // ... 59 more days
      ]
    },
    "financial": {
      "latest_quarter": "2024Q3",
      "revenue_ttm": 45600000000,      // 滚动12个月营收
      "net_profit_ttm": 23400000000,   // 滚动12个月净利润
      "roe": 12.5,                     // 净资产收益率
      "roa": 0.85,                     // 总资产收益率
      "debt_ratio": 0.92,              // 资产负债率
      "quarterly_data": [
        {
          "quarter": "2024Q3",
          "revenue": 11800000000,
          "net_profit": 6200000000,
          "eps": 0.31,
          "revenue_growth": 8.5,
          "profit_growth": 12.3
        },
        {
          "quarter": "2024Q2",
          "revenue": 11200000000,
          "net_profit": 5800000000,
          "eps": 0.29,
          "revenue_growth": 7.2,
          "profit_growth": 10.1
        }
        // ... 最近8个季度
      ]
    },
    "shareholders": {
      "update_date": "2024-09-30",
      "total_shareholders": 145623,
      "top_10": [
        {
          "rank": 1,
          "name": "北京市国有资产经营有限责任公司",
          "shares": 2850000000,
          "ratio": 14.25,
          "type": "国有股"
        },
        {
          "rank": 2,
          "name": "ING银行",
          "shares": 2680000000,
          "ratio": 13.40,
          "type": "外资股"
        }
        // ... 前10大股东
      ],
      "changes": [
        {
          "date": "2024-09-30",
          "shareholder": "ING银行",
          "change_type": "增持",
          "change_shares": 50000000,
          "change_ratio": 0.25
        }
      ]
    },
    "longhubang": {
      "recent_records": [
        {
          "date": "2025-09-18",
          "reason": "日跌幅偏离值达7%",
          "buy_amount": 125600000,
          "sell_amount": 98500000,
          "net_amount": 27100000,
          "details": [
            {
              "seat_name": "中信证券上海分公司",
              "buy_amount": 45600000,
              "sell_amount": 0,
              "net_amount": 45600000
            }
          ]
        }
      ]
    },
    "announcements": {
      "recent_days": 7,
      "count": 3,
      "list": [
        {
          "date": "2025-09-18",
          "title": "北京银行股份有限公司第三季度报告",
          "type": "定期报告",
          "url": "http://static.cninfo.com.cn/...",
          "summary": "公司2024年第三季度实现营业收入118亿元，同比增长8.5%..."
        },
        {
          "date": "2025-09-15",
          "title": "关于董事会换届选举的公告",
          "type": "临时公告",
          "url": "http://static.cninfo.com.cn/...",
          "summary": "公司董事会进行换届选举，选举新一届董事会成员..."
        }
      ]
    },
    "news": {
      "recent_days": 7,
      "count": 8,
      "list": [
        {
          "date": "2025-09-19",
          "title": "北京银行三季报：净利润同比增长12.3%，资产质量持续改善",
          "source": "财经网",
          "sentiment": "positive",
          "url": "https://...",
          "summary": "北京银行发布三季报，业绩表现亮眼..."
        },
        {
          "date": "2025-09-18",
          "title": "银行业数字化转型加速，北京银行科技投入增长25%",
          "source": "证券时报",
          "sentiment": "positive",
          "url": "https://...",
          "summary": "随着银行业数字化转型的深入..."
        }
      ]
    },
    "ai_analysis": {
      "overall_rating": "买入",
      "confidence": 0.78,
      "price_target": 6.20,
      "analysis": {
        "fundamental": {
          "score": 8.5,
          "summary": "基本面稳健，盈利能力强。ROE保持在12%以上，资产质量持续改善，不良贷款率控制良好。"
        },
        "technical": {
          "score": 7.2,
          "summary": "技术面偏强。股价突破60日均线，MACD指标显示多头排列，成交量温和放大。"
        },
        "valuation": {
          "score": 8.8,
          "summary": "估值具备吸引力。当前PB仅0.6倍，低于银行业平均水平，股息率3.2%，具备价值投资属性。"
        },
        "risk_factors": [
          "宏观经济下行压力可能影响银行资产质量",
          "利率市场化对净息差形成压力",
          "房地产行业风险需持续关注"
        ],
        "catalysts": [
          "数字化转型效果逐步显现",
          "京津冀一体化政策支持",
          "资本充足率提升支持业务扩张"
        ]
      },
      "generated_at": "2025-09-19T11:00:00Z",
      "model_version": "qwen2.5-7b-instruct"
    }
  }
}
```

## 🚀 实施计划

### Phase 1: 扩展AKShare数据获取
1. **K线数据增强**：获取60天日K线数据
2. **公告新闻接口**：集成公告和新闻数据
3. **财务数据接口**：获取季报数据

### Phase 2: PostgreSQL数据结构
1. **设计表结构**：股东、龙虎榜、财务数据表
2. **数据导入**：批量导入历史数据
3. **定期更新**：建立数据更新机制

### Phase 3: RAG服务集成
1. **AI分析接口**：连接RAG服务
2. **智能评价**：基于多维数据的AI分析
3. **风险识别**：智能风险提示

### Phase 4: 性能优化
1. **缓存策略**：不同数据类型的缓存TTL
2. **并发处理**：多数据源并行获取
3. **降级机制**：数据源故障时的处理

## 📊 数据获取策略

### 🔥 高频实时数据 (每次调用)
- 实时行情
- 最新公告 (当日)
- AI分析 (基于最新数据)

### 🔄 中频更新数据 (缓存30分钟)
- K线数据
- 新闻资讯
- 技术指标

### 📚 低频静态数据 (缓存1天)
- 基本信息
- 财务数据
- 股东信息
- 龙虎榜历史

---

这样设计的Dashboard API将提供：
- **完整的投资决策信息**
- **多维度的数据分析**
- **实用的K线图表数据**
- **智能的AI投资建议**
- **及时的新闻公告信息**

是否开始实施这个综合性的Dashboard API设计？