-- Prism2 批处理系统数据表创建脚本
-- 执行时间: 2025-09-19
-- 说明: 包含自选股管理、RAG版本控制、批处理任务管理表

-- 检查是否已存在相关表
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_watchlists') THEN
        RAISE NOTICE '批处理表已存在，跳过创建';
    ELSE
        RAISE NOTICE '开始创建批处理系统表';
    END IF;
END $$;

-- =============================================================================
-- 1. 自选股管理表
-- =============================================================================

-- 用户自选股列表表
CREATE TABLE IF NOT EXISTS user_watchlists (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,              -- 用户标识
    watchlist_name VARCHAR(100) NOT NULL,       -- 自选股列表名称
    description TEXT,                           -- 列表描述
    stock_codes TEXT[] NOT NULL,               -- 股票代码数组
    priority_level INTEGER DEFAULT 3,          -- 优先级 (1-5, 5最高)
    auto_batch BOOLEAN DEFAULT true,           -- 是否参与自动批处理
    data_types TEXT[] DEFAULT ARRAY['financial', 'announcements', 'shareholders'], -- 需要预热的数据类型
    schedule_time TIME DEFAULT '01:00:00',     -- 自定义调度时间
    is_active BOOLEAN DEFAULT true,           -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_priority CHECK (priority_level BETWEEN 1 AND 5),
    CONSTRAINT valid_data_types CHECK (array_length(data_types, 1) > 0),
    CONSTRAINT non_empty_stock_codes CHECK (array_length(stock_codes, 1) > 0)
);

-- 自选股使用统计表
CREATE TABLE IF NOT EXISTS watchlist_usage_stats (
    id SERIAL PRIMARY KEY,
    watchlist_id INTEGER NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    access_count INTEGER DEFAULT 0,           -- 访问次数
    last_accessed TIMESTAMP,                  -- 最后访问时间
    avg_response_time DECIMAL(10,3),          -- 平均响应时间
    cache_hit_rate DECIMAL(5,4),             -- 缓存命中率
    data_quality_score DECIMAL(5,4),         -- 数据质量评分
    date_recorded DATE DEFAULT CURRENT_DATE,  -- 统计日期

    FOREIGN KEY (watchlist_id) REFERENCES user_watchlists(id) ON DELETE CASCADE,
    CONSTRAINT uk_watchlist_stats UNIQUE(watchlist_id, date_recorded)
);

-- =============================================================================
-- 2. RAG版本管理表
-- =============================================================================

-- RAG数据版本表
CREATE TABLE IF NOT EXISTS rag_data_versions (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    data_type VARCHAR(50) NOT NULL,           -- financial, announcements, shareholders, longhubang
    version_id UUID DEFAULT gen_random_uuid() UNIQUE,
    data_hash VARCHAR(64) NOT NULL,           -- 数据MD5指纹
    vector_status VARCHAR(20) DEFAULT 'active', -- active, deprecated, archived, failed
    source_data JSONB NOT NULL,               -- 原始结构化数据
    vector_metadata JSONB,                    -- 向量化元数据
    embedding_model VARCHAR(100) DEFAULT 'bge-large-zh-v1.5',
    chunk_count INTEGER DEFAULT 0,           -- 分块数量
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activated_at TIMESTAMP,                  -- 激活时间
    deprecated_at TIMESTAMP,                 -- 废弃时间

    CONSTRAINT valid_vector_status CHECK (vector_status IN ('pending', 'active', 'deprecated', 'archived', 'failed')),
    CONSTRAINT valid_data_type CHECK (data_type IN ('financial', 'announcements', 'shareholders', 'longhubang')),
    CONSTRAINT valid_chunk_count CHECK (chunk_count >= 0)
);

-- 向量映射表
CREATE TABLE IF NOT EXISTS rag_vector_mappings (
    id SERIAL PRIMARY KEY,
    version_id UUID NOT NULL,                -- 对应的版本ID
    vector_id VARCHAR(100) NOT NULL,         -- ChromaDB中的向量ID
    collection_name VARCHAR(100) NOT NULL,   -- ChromaDB集合名
    chunk_index INTEGER NOT NULL,           -- 分块索引
    chunk_text TEXT NOT NULL,               -- 分块文本内容
    metadata JSONB,                         -- 向量元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (version_id) REFERENCES rag_data_versions(version_id) ON DELETE CASCADE,
    CONSTRAINT uk_vector_mapping UNIQUE(vector_id, collection_name),
    CONSTRAINT valid_chunk_index CHECK (chunk_index >= 0)
);

-- =============================================================================
-- 3. 批处理任务管理表
-- =============================================================================

-- 批处理任务表
CREATE TABLE IF NOT EXISTS batch_jobs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,          -- 任务名称
    job_type VARCHAR(50) NOT NULL,           -- watchlist_warm, market_scan, cache_clean, rag_sync
    job_category VARCHAR(30) NOT NULL,       -- scheduled, manual, priority
    stock_code VARCHAR(10),                  -- 处理的股票代码 (可选)
    data_type VARCHAR(50),                   -- 处理的数据类型 (可选)
    watchlist_id INTEGER,                   -- 关联的自选股列表 (可选)
    status VARCHAR(20) DEFAULT 'pending',    -- pending, running, success, failed, cancelled
    priority_level INTEGER DEFAULT 3,        -- 任务优先级
    scheduled_time TIMESTAMP,               -- 计划执行时间
    start_time TIMESTAMP,                   -- 实际开始时间
    end_time TIMESTAMP,                     -- 完成时间
    duration_seconds INTEGER,               -- 执行耗时(秒)
    processed_count INTEGER DEFAULT 0,      -- 处理数量
    success_count INTEGER DEFAULT 0,        -- 成功数量
    failed_count INTEGER DEFAULT 0,         -- 失败数量
    error_message TEXT,                     -- 错误信息
    result_summary JSONB,                   -- 结果摘要
    retry_count INTEGER DEFAULT 0,         -- 重试次数
    max_retries INTEGER DEFAULT 3,         -- 最大重试次数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_job_status CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
    CONSTRAINT valid_job_type CHECK (job_type IN ('watchlist_warm', 'market_scan', 'cache_clean', 'rag_sync')),
    CONSTRAINT valid_job_category CHECK (job_category IN ('scheduled', 'manual', 'priority')),
    CONSTRAINT valid_priority CHECK (priority_level BETWEEN 1 AND 5),
    CONSTRAINT valid_counts CHECK (processed_count >= 0 AND success_count >= 0 AND failed_count >= 0),
    CONSTRAINT valid_retry_count CHECK (retry_count <= max_retries)
);

-- 批处理性能统计表
CREATE TABLE IF NOT EXISTS batch_performance_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    metric_type VARCHAR(50) NOT NULL,        -- job_count, avg_duration, success_rate, cache_hit_rate
    metric_category VARCHAR(30),             -- job_type分类
    metric_value DECIMAL(15,6) NOT NULL,
    additional_data JSONB,                   -- 额外统计数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_daily_metric UNIQUE(date, metric_type, metric_category)
);

-- =============================================================================
-- 4. 索引创建
-- =============================================================================

-- 自选股表索引
CREATE INDEX IF NOT EXISTS idx_watchlists_user_active ON user_watchlists(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_watchlists_priority_batch ON user_watchlists(priority_level, auto_batch) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_watchlists_schedule ON user_watchlists(schedule_time) WHERE auto_batch = true AND is_active = true;

-- RAG版本表索引
CREATE INDEX IF NOT EXISTS idx_rag_versions_stock_type ON rag_data_versions(stock_code, data_type);
CREATE INDEX IF NOT EXISTS idx_rag_versions_status ON rag_data_versions(vector_status, created_at);
CREATE INDEX IF NOT EXISTS idx_rag_versions_hash ON rag_data_versions(data_hash);
CREATE INDEX IF NOT EXISTS idx_rag_versions_active ON rag_data_versions(stock_code, data_type, vector_status) WHERE vector_status = 'active';

-- 向量映射表索引
CREATE INDEX IF NOT EXISTS idx_vector_mappings_version ON rag_vector_mappings(version_id);
CREATE INDEX IF NOT EXISTS idx_vector_mappings_collection ON rag_vector_mappings(collection_name);

-- 批处理任务表索引
CREATE INDEX IF NOT EXISTS idx_batch_jobs_status_time ON batch_jobs(status, scheduled_time);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_type_priority ON batch_jobs(job_type, priority_level);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_watchlist ON batch_jobs(watchlist_id) WHERE watchlist_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_batch_jobs_created_at ON batch_jobs(created_at);

-- 性能指标表索引
CREATE INDEX IF NOT EXISTS idx_performance_date_type ON batch_performance_metrics(date, metric_type);

-- =============================================================================
-- 5. 触发器和函数
-- =============================================================================

-- 更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为自选股表添加更新时间触发器
DROP TRIGGER IF EXISTS update_watchlists_updated_at ON user_watchlists;
CREATE TRIGGER update_watchlists_updated_at
    BEFORE UPDATE ON user_watchlists
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RAG版本状态管理函数
CREATE OR REPLACE FUNCTION manage_rag_version_status()
RETURNS TRIGGER AS $$
BEGIN
    -- 当激活新版本时，废弃同股票同类型的其他活跃版本
    IF NEW.vector_status = 'active' AND (OLD.vector_status IS NULL OR OLD.vector_status != 'active') THEN
        UPDATE rag_data_versions
        SET vector_status = 'deprecated',
            deprecated_at = CURRENT_TIMESTAMP
        WHERE stock_code = NEW.stock_code
          AND data_type = NEW.data_type
          AND vector_status = 'active'
          AND version_id != NEW.version_id;

        NEW.activated_at = CURRENT_TIMESTAMP;
    END IF;

    -- 当废弃版本时，设置废弃时间
    IF NEW.vector_status = 'deprecated' AND (OLD.vector_status IS NULL OR OLD.vector_status != 'deprecated') THEN
        NEW.deprecated_at = CURRENT_TIMESTAMP;
    END IF;

    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为RAG版本表添加状态管理触发器
DROP TRIGGER IF EXISTS manage_rag_version_status_trigger ON rag_data_versions;
CREATE TRIGGER manage_rag_version_status_trigger
    BEFORE INSERT OR UPDATE ON rag_data_versions
    FOR EACH ROW EXECUTE FUNCTION manage_rag_version_status();

-- =============================================================================
-- 6. 初始数据插入
-- =============================================================================

-- 插入测试自选股列表
INSERT INTO user_watchlists (user_id, watchlist_name, description, stock_codes, priority_level, data_types)
VALUES
    ('test_user_001', '测试自选股-高优先级', '用于测试批处理功能的高优先级股票',
     ARRAY['000001', '600919'], 5, ARRAY['financial', 'announcements', 'shareholders']),
    ('test_user_001', '测试自选股-中优先级', '用于测试的中优先级股票',
     ARRAY['600519', '688469'], 3, ARRAY['financial', 'announcements']),
    ('system', '系统默认股票池', '系统维护的默认股票池',
     ARRAY['000001', '600519', '000002', '600036', '688469'], 4, ARRAY['financial', 'announcements', 'shareholders', 'longhubang'])
ON CONFLICT DO NOTHING;

-- 插入初始性能指标
INSERT INTO batch_performance_metrics (metric_type, metric_category, metric_value, additional_data)
VALUES
    ('baseline_cache_hit_rate', 'system', 0.30, '{"description": "初始缓存命中率基准"}'),
    ('baseline_avg_response_time', 'system', 5.0, '{"description": "初始平均响应时间基准(秒)"}')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- 7. 权限设置
-- =============================================================================

-- 为prism2用户授权
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO prism2;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO prism2;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO prism2;

-- 完成信息
DO $$
BEGIN
    RAISE NOTICE '批处理系统数据表创建完成！';
    RAISE NOTICE '包含表: user_watchlists, watchlist_usage_stats, rag_data_versions, rag_vector_mappings, batch_jobs, batch_performance_metrics';
    RAISE NOTICE '包含索引: 性能优化索引已创建';
    RAISE NOTICE '包含触发器: 自动更新时间和RAG版本管理';
    RAISE NOTICE '包含初始数据: 测试自选股列表和基准指标';
END $$;