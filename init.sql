-- Prism2 数据库初始化脚本
-- 基于固定接口规范创建核心表结构

-- 启用 TimescaleDB 扩展
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 股票基础信息表
CREATE TABLE IF NOT EXISTS stocks (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    market VARCHAR(10) NOT NULL,
    industry VARCHAR(100),
    market_cap BIGINT,
    pe_ratio DECIMAL(10,2),
    pb_ratio DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- K线数据表（时序数据）
CREATE TABLE IF NOT EXISTS ohlcv_data (
    stock_code VARCHAR(10) NOT NULL,
    period VARCHAR(10) NOT NULL, -- 1d, 1w, 1m等
    timestamp TIMESTAMP NOT NULL,
    open_price DECIMAL(10,2) NOT NULL,
    high_price DECIMAL(10,2) NOT NULL,
    low_price DECIMAL(10,2) NOT NULL,
    close_price DECIMAL(10,2) NOT NULL,
    volume BIGINT NOT NULL,
    turnover DECIMAL(20,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code, period, timestamp)
);

-- 将K线数据表转换为超表
SELECT create_hypertable('ohlcv_data', 'timestamp', if_not_exists => TRUE);

-- 财务数据表
CREATE TABLE IF NOT EXISTS financial_reports (
    stock_code VARCHAR(10) NOT NULL,
    period VARCHAR(10) NOT NULL, -- 2024Q3等
    revenue BIGINT,
    net_profit BIGINT,
    roe DECIMAL(5,2),
    gross_margin DECIMAL(5,2),
    debt_ratio DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code, period)
);

-- 公司公告表
CREATE TABLE IF NOT EXISTS company_announcements (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    title TEXT NOT NULL,
    type VARCHAR(50),
    publish_date DATE NOT NULL,
    content TEXT,
    url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 股票新闻表
CREATE TABLE IF NOT EXISTS stock_news (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10),
    title TEXT NOT NULL,
    content TEXT,
    publish_time TIMESTAMP NOT NULL,
    source VARCHAR(100),
    sentiment_score DECIMAL(3,2), -- -1.0 到 1.0
    url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 龙虎榜数据表
CREATE TABLE IF NOT EXISTS longhubang_data (
    stock_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    rank_reason VARCHAR(200),
    buy_amount BIGINT,
    sell_amount BIGINT,
    net_amount BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code, trade_date)
);

-- 股东变更表
CREATE TABLE IF NOT EXISTS shareholder_changes (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    shareholder VARCHAR(200) NOT NULL,
    change_type VARCHAR(50), -- 增持、减持等
    change_amount BIGINT,
    change_ratio DECIMAL(5,2),
    change_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI分析结果表
CREATE TABLE IF NOT EXISTS ai_analysis_results (
    stock_code VARCHAR(10) NOT NULL,
    analysis_type VARCHAR(50) NOT NULL, -- comprehensive, technical等
    growth_score DECIMAL(3,2),
    profitability_score DECIMAL(3,2),
    risk_score DECIMAL(3,2),
    valuation_score DECIMAL(3,2),
    technical_score DECIMAL(3,2),
    market_sentiment_score DECIMAL(3,2),
    investment_recommendation VARCHAR(20), -- 买入、卖出、持有
    confidence_level DECIMAL(3,2),
    summary TEXT,
    analysis_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code, analysis_type, analysis_time)
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_stocks_market ON stocks(market);
CREATE INDEX IF NOT EXISTS idx_stocks_industry ON stocks(industry);
CREATE INDEX IF NOT EXISTS idx_ohlcv_stock_period ON ohlcv_data(stock_code, period);
CREATE INDEX IF NOT EXISTS idx_announcements_stock ON company_announcements(stock_code);
CREATE INDEX IF NOT EXISTS idx_announcements_date ON company_announcements(publish_date);
CREATE INDEX IF NOT EXISTS idx_news_stock ON stock_news(stock_code);
CREATE INDEX IF NOT EXISTS idx_news_time ON stock_news(publish_time);
CREATE INDEX IF NOT EXISTS idx_longhubang_date ON longhubang_data(trade_date);

-- 插入一些测试数据
INSERT INTO stocks (code, name, market, industry, market_cap) VALUES
('000001', '平安银行', 'SZ', '银行', 280000000000),
('000002', '万科A', 'SZ', '房地产', 195000000000),
('600519', '贵州茅台', 'SH', '白酒', 2200000000000)
ON CONFLICT (code) DO NOTHING;

-- 授权给应用用户
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO prism2;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO prism2;