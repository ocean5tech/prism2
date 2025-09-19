-- 创建四大股票功能的PostgreSQL表结构
-- 用于完善三层架构: Redis → PostgreSQL → AKShare

-- 1. 财务数据表
CREATE TABLE IF NOT EXISTS stock_financial (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),
    summary_data JSONB,
    detailed_data JSONB,
    periods JSONB,
    data_source VARCHAR(50) DEFAULT 'akshare',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 为财务数据表创建索引
CREATE INDEX IF NOT EXISTS idx_stock_financial_code ON stock_financial(stock_code);
CREATE INDEX IF NOT EXISTS idx_stock_financial_created_at ON stock_financial(created_at);

-- 2. 公告信息表
CREATE TABLE IF NOT EXISTS stock_announcements (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),
    announcement_data JSONB,
    count INTEGER DEFAULT 0,
    data_source VARCHAR(50) DEFAULT 'akshare',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 为公告信息表创建索引
CREATE INDEX IF NOT EXISTS idx_stock_announcements_code ON stock_announcements(stock_code);
CREATE INDEX IF NOT EXISTS idx_stock_announcements_created_at ON stock_announcements(created_at);

-- 3. 股东信息表
CREATE TABLE IF NOT EXISTS stock_shareholders (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),
    shareholders_data JSONB,
    top_10_count INTEGER DEFAULT 0,
    data_source VARCHAR(50) DEFAULT 'akshare',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 为股东信息表创建索引
CREATE INDEX IF NOT EXISTS idx_stock_shareholders_code ON stock_shareholders(stock_code);
CREATE INDEX IF NOT EXISTS idx_stock_shareholders_created_at ON stock_shareholders(created_at);

-- 4. 龙虎榜数据表
CREATE TABLE IF NOT EXISTS stock_longhubang (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),
    longhubang_data JSONB,
    records_count INTEGER DEFAULT 0,
    query_days INTEGER DEFAULT 30,
    data_source VARCHAR(50) DEFAULT 'akshare',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 为龙虎榜表创建索引
CREATE INDEX IF NOT EXISTS idx_stock_longhubang_code ON stock_longhubang(stock_code);
CREATE INDEX IF NOT EXISTS idx_stock_longhubang_created_at ON stock_longhubang(created_at);

-- 添加更新时间自动更新触发器的函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有表添加自动更新updated_at的触发器
CREATE TRIGGER update_stock_financial_updated_at BEFORE UPDATE ON stock_financial FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_stock_announcements_updated_at BEFORE UPDATE ON stock_announcements FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_stock_shareholders_updated_at BEFORE UPDATE ON stock_shareholders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_stock_longhubang_updated_at BEFORE UPDATE ON stock_longhubang FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 创建复合索引用于优化查询性能
CREATE INDEX IF NOT EXISTS idx_stock_financial_code_updated ON stock_financial(stock_code, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_stock_announcements_code_updated ON stock_announcements(stock_code, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_stock_shareholders_code_updated ON stock_shareholders(stock_code, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_stock_longhubang_code_updated ON stock_longhubang(stock_code, updated_at DESC);

-- 添加表注释
COMMENT ON TABLE stock_financial IS '股票财务数据表 - 存储从AKShare获取的财务摘要信息';
COMMENT ON TABLE stock_announcements IS '股票公告信息表 - 存储从AKShare获取的新闻公告数据';
COMMENT ON TABLE stock_shareholders IS '股票股东信息表 - 存储从AKShare获取的股东持股信息';
COMMENT ON TABLE stock_longhubang IS '股票龙虎榜表 - 存储从AKShare获取的龙虎榜数据';

-- 添加列注释
COMMENT ON COLUMN stock_financial.summary_data IS '财务摘要数据JSON格式';
COMMENT ON COLUMN stock_financial.detailed_data IS '详细财务数据JSON格式';
COMMENT ON COLUMN stock_financial.periods IS '报告期列表JSON格式';

COMMENT ON COLUMN stock_announcements.announcement_data IS '公告信息数据JSON格式';
COMMENT ON COLUMN stock_announcements.count IS '公告条数';

COMMENT ON COLUMN stock_shareholders.shareholders_data IS '股东信息数据JSON格式';
COMMENT ON COLUMN stock_shareholders.top_10_count IS '前十大股东数量';

COMMENT ON COLUMN stock_longhubang.longhubang_data IS '龙虎榜数据JSON格式';
COMMENT ON COLUMN stock_longhubang.records_count IS '龙虎榜记录数量';
COMMENT ON COLUMN stock_longhubang.query_days IS '查询天数范围';