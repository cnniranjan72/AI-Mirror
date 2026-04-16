-- Migration: Elite-Level Upgrades
-- Description: Hybrid search, RL logging, and optimized table structure

-- ============================================================
-- 1. ADD FULL-TEXT SEARCH SUPPORT FOR HYBRID SEARCH
-- ============================================================

-- Add tsvector column for full-text search
ALTER TABLE behavioral_memory 
ADD COLUMN IF NOT EXISTS content_tsv tsvector;

-- Create GIN index for full-text search
CREATE INDEX IF NOT EXISTS idx_behavioral_memory_content_tsv 
ON behavioral_memory USING gin(content_tsv);

-- Create trigger to auto-update tsvector
CREATE OR REPLACE FUNCTION behavioral_memory_content_tsv_trigger() 
RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('english', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tsvector_update_behavioral_memory 
BEFORE INSERT OR UPDATE ON behavioral_memory
FOR EACH ROW EXECUTE FUNCTION behavioral_memory_content_tsv_trigger();

-- Update existing rows
UPDATE behavioral_memory 
SET content_tsv = to_tsvector('english', COALESCE(content, ''))
WHERE content_tsv IS NULL;

-- Add tsvector to chat_history as well
ALTER TABLE chat_history 
ADD COLUMN IF NOT EXISTS message_tsv tsvector;

CREATE INDEX IF NOT EXISTS idx_chat_history_message_tsv 
ON chat_history USING gin(message_tsv);

CREATE OR REPLACE FUNCTION chat_history_message_tsv_trigger() 
RETURNS trigger AS $$
BEGIN
    NEW.message_tsv := to_tsvector('english', COALESCE(NEW.message, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tsvector_update_chat_history 
BEFORE INSERT OR UPDATE ON chat_history
FOR EACH ROW EXECUTE FUNCTION chat_history_message_tsv_trigger();

UPDATE chat_history 
SET message_tsv = to_tsvector('english', COALESCE(message, ''))
WHERE message_tsv IS NULL;

-- ============================================================
-- 2. RL ACTIONS LOG TABLE (CRITICAL FOR RESEARCH)
-- ============================================================

CREATE TABLE IF NOT EXISTS actions_log (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_data JSONB DEFAULT '{}',
    state_before JSONB DEFAULT '{}',
    state_after JSONB DEFAULT '{}',
    reward FLOAT DEFAULT 0.0,
    feedback TEXT,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for RL analysis
CREATE INDEX IF NOT EXISTS idx_actions_log_user_id ON actions_log(user_id);
CREATE INDEX IF NOT EXISTS idx_actions_log_action_type ON actions_log(action_type);
CREATE INDEX IF NOT EXISTS idx_actions_log_created_at ON actions_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_actions_log_reward ON actions_log(reward DESC);

-- Composite index for user-specific RL queries
CREATE INDEX IF NOT EXISTS idx_actions_log_user_time ON actions_log(user_id, created_at DESC);

-- ============================================================
-- 3. EMBEDDINGS TABLE (FUTURE SCALING)
-- ============================================================

-- Separate embeddings table for better scaling and analytics
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,  -- 'behavioral_memory', 'chat_history', 'user_profile'
    entity_id INTEGER NOT NULL,
    embedding VECTOR(384) NOT NULL,
    model_version TEXT DEFAULT 'MiniLM-L6-v2',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vector index on embeddings table
CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Composite index for entity lookups
CREATE INDEX IF NOT EXISTS idx_embeddings_entity ON embeddings(entity_type, entity_id);

-- Analyze for optimization
ANALYZE embeddings;

-- ============================================================
-- 4. METADATA TABLE (FUTURE SCALING)
-- ============================================================

-- Separate metadata table for analytics and filtering
CREATE TABLE IF NOT EXISTS metadata_store (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    value_type TEXT DEFAULT 'string',  -- 'string', 'number', 'boolean', 'json'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for metadata queries
CREATE INDEX IF NOT EXISTS idx_metadata_entity ON metadata_store(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_metadata_key ON metadata_store(key);
CREATE INDEX IF NOT EXISTS idx_metadata_key_value ON metadata_store(key, value);

-- ============================================================
-- 5. BEHAVIORAL TRENDS TABLE (ANALYTICS)
-- ============================================================

CREATE TABLE IF NOT EXISTS behavioral_trends (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    period TEXT NOT NULL,  -- 'daily', 'weekly', 'monthly'
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for trend analysis
CREATE INDEX IF NOT EXISTS idx_behavioral_trends_user ON behavioral_trends(user_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_trends_metric ON behavioral_trends(metric_name);
CREATE INDEX IF NOT EXISTS idx_behavioral_trends_period ON behavioral_trends(period, period_start DESC);

-- ============================================================
-- 6. USER GOALS TABLE (ALIGNMENT TRACKING)
-- ============================================================

CREATE TABLE IF NOT EXISTS user_goals (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    goal_type TEXT NOT NULL,
    goal_description TEXT NOT NULL,
    target_value FLOAT,
    current_value FLOAT DEFAULT 0.0,
    progress FLOAT DEFAULT 0.0,
    status TEXT DEFAULT 'active',  -- 'active', 'completed', 'abandoned'
    priority INTEGER DEFAULT 5,
    deadline TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for goal tracking
CREATE INDEX IF NOT EXISTS idx_user_goals_user_id ON user_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_user_goals_status ON user_goals(status);
CREATE INDEX IF NOT EXISTS idx_user_goals_priority ON user_goals(priority DESC);

-- Trigger for updated_at
CREATE TRIGGER update_user_goals_updated_at
    BEFORE UPDATE ON user_goals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 7. PERFORMANCE MONITORING TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    metric_type TEXT NOT NULL,  -- 'query_time', 'insert_time', 'index_size', etc.
    metric_value FLOAT NOT NULL,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for performance analysis
CREATE INDEX IF NOT EXISTS idx_performance_metrics_type ON performance_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_created ON performance_metrics(created_at DESC);

-- ============================================================
-- 8. VIEWS FOR ANALYTICS
-- ============================================================

-- View for user behavioral summary
CREATE OR REPLACE VIEW user_behavioral_summary AS
SELECT 
    user_id,
    COUNT(*) as total_events,
    COUNT(DISTINCT type) as event_types,
    MIN(created_at) as first_event,
    MAX(created_at) as last_event,
    EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at))) / 86400 as days_active
FROM behavioral_memory
GROUP BY user_id;

-- View for RL performance
CREATE OR REPLACE VIEW rl_performance_summary AS
SELECT 
    user_id,
    action_type,
    COUNT(*) as action_count,
    AVG(reward) as avg_reward,
    STDDEV(reward) as reward_stddev,
    MIN(reward) as min_reward,
    MAX(reward) as max_reward
FROM actions_log
GROUP BY user_id, action_type;

-- View for recent high-value actions
CREATE OR REPLACE VIEW high_value_actions AS
SELECT 
    user_id,
    action_type,
    reward,
    action_data,
    created_at
FROM actions_log
WHERE reward > 0.5
ORDER BY created_at DESC
LIMIT 100;

-- ============================================================
-- 9. FUNCTIONS FOR HYBRID SEARCH
-- ============================================================

-- Function to perform hybrid search (vector + keyword)
CREATE OR REPLACE FUNCTION hybrid_search(
    p_user_id TEXT,
    p_query_embedding VECTOR(384),
    p_query_text TEXT,
    p_vector_weight FLOAT DEFAULT 0.7,
    p_keyword_weight FLOAT DEFAULT 0.3,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    id INTEGER,
    content TEXT,
    metadata JSONB,
    type TEXT,
    created_at TIMESTAMP,
    similarity_score FLOAT,
    keyword_score FLOAT,
    hybrid_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        bm.id,
        bm.content,
        bm.metadata,
        bm.type,
        bm.created_at,
        (1 - (bm.embedding <-> p_query_embedding)) AS similarity_score,
        ts_rank(bm.content_tsv, plainto_tsquery('english', p_query_text)) AS keyword_score,
        (
            (1 - (bm.embedding <-> p_query_embedding)) * p_vector_weight +
            ts_rank(bm.content_tsv, plainto_tsquery('english', p_query_text)) * p_keyword_weight
        ) AS hybrid_score
    FROM behavioral_memory bm
    WHERE bm.user_id = p_user_id
    ORDER BY hybrid_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function for dynamic index tuning recommendation
CREATE OR REPLACE FUNCTION recommend_index_lists()
RETURNS TABLE (
    table_name TEXT,
    current_rows BIGINT,
    recommended_lists INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'behavioral_memory'::TEXT,
        COUNT(*)::BIGINT,
        GREATEST(50, LEAST(1000, FLOOR(SQRT(COUNT(*)))::INTEGER))
    FROM behavioral_memory
    UNION ALL
    SELECT 
        'chat_history'::TEXT,
        COUNT(*)::BIGINT,
        GREATEST(50, LEAST(1000, FLOOR(SQRT(COUNT(*)))::INTEGER))
    FROM chat_history;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 10. ANALYZE ALL TABLES
-- ============================================================

ANALYZE behavioral_memory;
ANALYZE chat_history;
ANALYZE user_profiles;
ANALYZE sessions;
ANALYZE actions_log;
ANALYZE embeddings;
ANALYZE metadata_store;
ANALYZE behavioral_trends;
ANALYZE user_goals;
ANALYZE performance_metrics;

-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Elite upgrades migration completed successfully';
    RAISE NOTICE '- Hybrid search enabled (vector + keyword)';
    RAISE NOTICE '- RL actions_log table created';
    RAISE NOTICE '- Embeddings table for future scaling';
    RAISE NOTICE '- Metadata table for analytics';
    RAISE NOTICE '- Performance monitoring enabled';
    RAISE NOTICE '- Dynamic index tuning functions added';
END $$;
