# Product Backlog - Prism2 股票分析平台

> **文档说明**: 记录暂缓开发但有价值的功能需求，按优先级排序

## 📋 Backlog 总览

| 优先级 | 功能模块 | 状态 | 预计工作量 | 依赖项 |
|--------|----------|------|------------|--------|
| P1 | 市场筛选查询 | Backlog | 2-3周 | 全市场数据采集 |
| P2 | 技术指标筛选 | Backlog | 1-2周 | 指标计算引擎 |
| P3 | 实时监控告警 | Backlog | 2周 | WebSocket推送 |
| P4 | 自定义选股策略 | Backlog | 3-4周 | 策略引擎 |

---

## 🎯 P1: 市场筛选查询功能

### 功能描述
支持用户通过自然语言查询全市场股票筛选结果

### 用户故事
**作为** 投资者
**我希望** 能够问"哪个股票昨天涨停了？"
**以便** 快速发现市场热点和投资机会

### 具体需求

#### 1.1 涨跌幅筛选
- **需求**: "哪个股票昨天涨停了？"
- **实现**:
  ```sql
  SELECT stock_code, stock_name, change_percent
  FROM market_daily_data
  WHERE trade_date = '2025-09-19'
  AND change_percent >= 9.9
  ```

#### 1.2 成交量筛选
- **需求**: "成交量放大3倍以上的股票有哪些？"
- **实现**: 需要对比历史平均成交量

#### 1.3 排序查询
- **需求**: "涨幅前10名股票"
- **实现**: 按涨幅排序并限制返回数量

### 技术要求

#### 数据库架构扩展
```sql
-- 全市场日线数据表
CREATE TABLE market_daily_data (
    trade_date DATE NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),
    open_price DECIMAL(10,2),
    close_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    volume BIGINT,
    turnover DECIMAL(15,2),
    change_amount DECIMAL(10,2),
    change_percent DECIMAL(6,2),
    turnover_rate DECIMAL(6,2),
    pe_ratio DECIMAL(8,2),
    pb_ratio DECIMAL(8,2),
    market_cap DECIMAL(20,2),
    -- 筛选标记字段
    is_limit_up BOOLEAN DEFAULT FALSE,
    is_limit_down BOOLEAN DEFAULT FALSE,
    is_st BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (trade_date, stock_code),
    INDEX idx_date_change (trade_date, change_percent DESC),
    INDEX idx_date_volume (trade_date, volume DESC)
);

-- 历史统计数据表（用于对比）
CREATE TABLE market_statistics (
    stock_code VARCHAR(10),
    avg_volume_20d BIGINT,      -- 20日平均成交量
    avg_turnover_20d DECIMAL(15,2),
    price_ma_5 DECIMAL(10,2),   -- 5日均价
    price_ma_20 DECIMAL(10,2),  -- 20日均价
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code)
);
```

#### API接口设计
```python
# 市场筛选API
@app.post("/api/v1/market/screen")
async def screen_market(request: MarketScreenRequest):
    """
    市场筛选接口

    Request Body:
    {
        "date": "2025-09-20",
        "filters": [
            {"field": "change_percent", "operator": ">=", "value": 9.9},
            {"field": "volume", "operator": ">", "value": 100000000}
        ],
        "sort": {"field": "change_percent", "order": "desc"},
        "limit": 20
    }
    """

# 快速筛选预设
@app.get("/api/v1/market/quick-screen/{screen_type}")
async def quick_screen(screen_type: str, date: str = None):
    """
    快速筛选预设

    screen_type:
    - limit_up: 涨停股票
    - limit_down: 跌停股票
    - high_volume: 放量股票
    - new_high: 创新高股票
    """
```

#### RAG Tool扩展
```python
# tools/market_screening_tool.py
def screen_market_stocks(
    query: str,
    date: str = None,
    limit: int = 20
) -> dict:
    """
    市场筛选工具

    Args:
        query: 自然语言查询，如"昨天涨停的股票"
        date: 查询日期，默认最新交易日
        limit: 返回结果数量限制

    Returns:
        {
            "query_type": "limit_up_stocks",
            "results": [
                {
                    "stock_code": "000001",
                    "stock_name": "平安银行",
                    "change_percent": 10.01,
                    "volume": 12345678,
                    "turnover": 1234567890.12
                }
            ],
            "total_count": 15,
            "analysis_summary": "今日共有15只股票涨停..."
        }
    """

# 查询意图识别
def parse_market_query(query: str) -> dict:
    """
    解析市场查询意图

    Examples:
        "昨天涨停的股票" -> {"type": "limit_up", "date": "yesterday"}
        "涨幅前10名" -> {"type": "top_gainers", "limit": 10}
        "成交量最大的股票" -> {"type": "high_volume", "limit": 20}
    """
```

### 数据采集挑战

#### 1. 数据量估算
- **A股股票数量**: ~4,200只
- **每日数据量**: 4,200 × 20字段 ≈ 84,000条记录/天
- **年度数据量**: 84,000 × 250交易日 ≈ 2,100万条记录
- **存储空间**: 约2-3GB/年（包含索引）

#### 2. 数据采集方案
```python
# 全市场数据采集
def collect_market_data():
    """
    采集全市场股票数据

    挑战:
    - AKShare API限流：每分钟60次请求
    - 4200只股票需要70分钟完成一轮采集
    - 需要增量更新策略
    """

    # 方案1：分批采集
    stock_list = ak.stock_zh_a_spot_em()  # 获取股票列表
    for batch in batch_process(stock_list, batch_size=50):
        for stock in batch:
            data = ak.stock_zh_a_hist(symbol=stock['code'])
            save_to_database(data)
            time.sleep(1)  # 限流控制

    # 方案2：多进程采集
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(fetch_stock_data, stock)
                  for stock in stock_list]
```

#### 3. 实时性要求
- **盘中更新**: 每15分钟更新一次
- **盘后处理**: 当日收盘后1小时内完成全量更新
- **技术指标计算**: 需要历史数据，计算密集

### 预计开发工作量

#### Phase 1: 基础市场筛选 (1-2周)
- [ ] 扩展数据库表结构
- [ ] 开发数据采集脚本
- [ ] 实现基础筛选API
- [ ] 集成到RAG Tool

#### Phase 2: 高级筛选功能 (1周)
- [ ] 复杂筛选条件支持
- [ ] 排序和分页功能
- [ ] 查询性能优化

#### Phase 3: 用户体验优化 (0.5周)
- [ ] 自然语言查询解析
- [ ] 结果可视化
- [ ] 筛选结果导出

---

## 🔧 P2: 技术指标筛选功能

### 功能描述
基于技术指标进行股票筛选和信号识别

### 用户故事
**作为** 技术分析爱好者
**我希望** 能够问"哪个股票MACD逆转？"
**以便** 捕捉技术分析信号

### 具体需求

#### 2.1 MACD信号筛选
- **需求**: "哪个股票MACD逆转？"、"MACD金叉的股票"
- **技术实现**: MACD指标计算 + 信号识别

#### 2.2 KDJ信号筛选
- **需求**: "KDJ金叉的股票"、"KDJ超卖区域"
- **技术实现**: KDJ指标计算 + 金叉/死叉识别

#### 2.3 RSI筛选
- **需求**: "RSI超卖的股票"、"RSI突破50的股票"
- **技术实现**: RSI计算 + 超买超卖识别

### 技术指标计算引擎

```python
# indicators/calculator.py
class TechnicalIndicators:

    def calculate_macd(self, prices: List[float],
                      fast=12, slow=26, signal=9) -> dict:
        """计算MACD指标"""
        ema_fast = self.ema(prices, fast)
        ema_slow = self.ema(prices, slow)
        dif = ema_fast - ema_slow
        dea = self.ema(dif, signal)
        histogram = dif - dea

        return {
            'dif': dif,
            'dea': dea,
            'histogram': histogram,
            'signal': self.detect_macd_signals(dif, dea)
        }

    def calculate_kdj(self, high: List[float],
                     low: List[float],
                     close: List[float]) -> dict:
        """计算KDJ指标"""
        # KDJ计算逻辑
        pass

    def calculate_rsi(self, prices: List[float], period=14) -> dict:
        """计算RSI指标"""
        # RSI计算逻辑
        pass

# 信号识别
def detect_macd_signals(dif: List[float], dea: List[float]) -> str:
    """
    检测MACD信号

    Returns:
        - "golden_cross": 金叉
        - "death_cross": 死叉
        - "bullish_divergence": 底背离
        - "bearish_divergence": 顶背离
        - "neutral": 无明显信号
    """
```

### 数据库扩展

```sql
-- 技术指标数据表
CREATE TABLE technical_indicators (
    trade_date DATE NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    -- MACD指标
    macd_dif DECIMAL(8,4),
    macd_dea DECIMAL(8,4),
    macd_histogram DECIMAL(8,4),
    macd_signal VARCHAR(20),  -- golden_cross, death_cross, etc.
    -- KDJ指标
    kdj_k DECIMAL(5,2),
    kdj_d DECIMAL(5,2),
    kdj_j DECIMAL(5,2),
    kdj_signal VARCHAR(20),
    -- RSI指标
    rsi_6 DECIMAL(5,2),
    rsi_14 DECIMAL(5,2),
    rsi_24 DECIMAL(5,2),
    rsi_signal VARCHAR(20),
    -- 均线
    ma_5 DECIMAL(10,2),
    ma_10 DECIMAL(10,2),
    ma_20 DECIMAL(10,2),
    ma_60 DECIMAL(10,2),
    -- 布林带
    bb_upper DECIMAL(10,2),
    bb_middle DECIMAL(10,2),
    bb_lower DECIMAL(10,2),

    PRIMARY KEY (trade_date, stock_code),
    INDEX idx_macd_signal (trade_date, macd_signal),
    INDEX idx_kdj_signal (trade_date, kdj_signal),
    INDEX idx_rsi_signal (trade_date, rsi_signal)
);
```

### 预计工作量: 1-2周

---

## 📡 P3: 实时监控告警功能

### 功能描述
实时监控市场变化，主动推送重要信息

### 用户故事
**作为** 活跃投资者
**我希望** 系统能主动告诉我"平安银行突破年线了"
**以便** 及时把握投资机会

### 具体需求

#### 3.1 价格告警
- **需求**: 股价突破关键位置时主动提醒
- **实现**: WebSocket推送 + 价格监控

#### 3.2 技术信号告警
- **需求**: 重要技术信号出现时推送
- **实现**: 实时指标计算 + 信号检测

#### 3.3 异常监控
- **需求**: 异常成交量、大单交易等
- **实现**: 统计异常检测

### 预计工作量: 2周

---

## 🧠 P4: 自定义选股策略功能

### 功能描述
允许用户定义复杂的选股策略和回测

### 用户故事
**作为** 量化投资者
**我希望** 能够自定义"RSI<30且MACD金叉"的选股策略
**以便** 实现个性化的投资策略

### 预计工作量: 3-4周

---

## 📅 实施建议

### 优先级排序原则
1. **用户价值**: 功能对用户的实际价值
2. **技术复杂度**: 开发难度和时间成本
3. **数据依赖**: 对外部数据源的依赖程度
4. **维护成本**: 长期维护的复杂度

### 实施时机
- **当前阶段**: 专注单股票AI分析功能
- **V2版本**: 考虑加入P1市场筛选功能
- **V3版本**: 技术指标筛选和实时监控
- **V4版本**: 自定义策略功能

### 技术债务评估
- **数据存储成本**: 全市场数据约10GB/年
- **计算资源**: 技术指标计算需要额外CPU资源
- **API限流**: 数据采集受第三方API限制
- **实时性挑战**: 盘中数据更新的技术复杂度

---

**📝 文档维护**: 此Backlog将根据用户反馈和技术发展持续更新

**🔄 最后更新**: 2025-09-20

**👤 负责人**: Claude + 用户协作