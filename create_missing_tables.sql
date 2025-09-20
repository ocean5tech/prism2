-- 创建缺失的股票数据库表结构
-- 基于 enhanced_dashboard_api.py 中的代码分析

-- 1. 股票基本信息表
CREATE TABLE IF NOT EXISTS stock_basic_info (
    stock_code VARCHAR(10) PRIMARY KEY,
    stock_name VARCHAR(100) NOT NULL,
    market VARCHAR(20),
    industry VARCHAR(100),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. 股票K线数据表 (日线)
CREATE TABLE IF NOT EXISTS stock_kline_daily (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    close_price DECIMAL(10,2),
    volume BIGINT,
    turnover DECIMAL(15,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, trade_date)
);

-- 3. 股票新闻表
CREATE TABLE IF NOT EXISTS stock_news (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    publish_time TIMESTAMP WITH TIME ZONE,
    source VARCHAR(100),
    url VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. 股票实时数据表
CREATE TABLE IF NOT EXISTS stock_realtime (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    current_price DECIMAL(10,2),
    change_amount DECIMAL(10,2),
    change_percent DECIMAL(6,2),
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    volume BIGINT,
    turnover DECIMAL(15,2),
    market_cap DECIMAL(20,2),
    pe_ratio DECIMAL(8,2),
    pb_ratio DECIMAL(8,2),
    trade_date DATE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, trade_date)
);

-- 5. AI分析结果表 (为了支持ai_analysis数据类型)
CREATE TABLE IF NOT EXISTS stock_ai_analysis (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,
    analysis_result JSONB,
    confidence_score DECIMAL(4,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_stock_kline_daily_code_date ON stock_kline_daily(stock_code, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_news_code_time ON stock_news(stock_code, publish_time DESC);
CREATE INDEX IF NOT EXISTS idx_stock_realtime_code_date ON stock_realtime(stock_code, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_ai_analysis_code ON stock_ai_analysis(stock_code, created_at DESC);

-- 添加TimescaleDB超表优化（如果已安装TimescaleDB扩展）
-- 这些语句在TimescaleDB不可用时会失败，但不影响基本功能
DO $$
BEGIN
    -- 尝试为时间序列数据创建超表
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        -- 将K线数据表转换为超表（按时间分片）
        PERFORM create_hypertable('stock_kline_daily', 'trade_date', if_not_exists => TRUE);

        -- 将实时数据表转换为超表（按时间分片）
        PERFORM create_hypertable('stock_realtime', 'updated_at', if_not_exists => TRUE);

        -- 将新闻数据表转换为超表（按时间分片）
        PERFORM create_hypertable('stock_news', 'created_at', if_not_exists => TRUE);

        RAISE NOTICE 'TimescaleDB hypertables created successfully';
    ELSE
        RAISE NOTICE 'TimescaleDB extension not found, using regular tables';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'TimescaleDB hypertable creation skipped: %', SQLERRM;
END $$;

-- 验证表创建
SELECT 'Tables created successfully. Current table count: ' || count(*) as status
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('stock_basic_info', 'stock_kline_daily', 'stock_news', 'stock_realtime', 'stock_ai_analysis');