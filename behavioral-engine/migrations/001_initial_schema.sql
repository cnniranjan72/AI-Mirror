-- Migration: Initial PostgreSQL Schema with pgvector
-- Description: Replace ChromaDB with Neon PostgreSQL + pgvector

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create behavioral_memory table for vector storage
CREATE TABLE IF NOT EXISTS behavioral_memory (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_behavioral_memory_user_id ON behavioral_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_memory_type ON behavioral_memory(type);
CREATE INDEX IF NOT EXISTS idx_behavioral_memory_created_at ON behavioral_memory(created_at DESC);

-- Create vector similarity search index (IVFFlat for fast approximate search)
-- lists = 100 for small-medium datasets (adjust to sqrt(total_rows) for large datasets)
CREATE INDEX IF NOT EXISTS idx_behavioral_memory_embedding ON behavioral_memory 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- CRITICAL: Analyze table for index optimization
ANALYZE behavioral_memory;

-- Create composite index for user-specific queries
CREATE INDEX IF NOT EXISTS idx_behavioral_memory_user_type ON behavioral_memory(user_id, type);

-- Create chat_history table for conversation storage
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    message TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    embedding VECTOR(384),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for chat_history
CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_history_embedding ON chat_history 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- CRITICAL: Analyze table for index optimization
ANALYZE chat_history;

-- Create user_profiles table for persona storage
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    persona_vector VECTOR(384),
    archetype TEXT,
    behavioral_traits JSONB DEFAULT '{}',
    goals JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index for user_profiles
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- Create sessions table for session tracking
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT UNIQUE NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    total_watch_time FLOAT DEFAULT 0,
    reels_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time DESC);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_behavioral_memory_updated_at
    BEFORE UPDATE ON behavioral_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create view for recent behavioral data
CREATE OR REPLACE VIEW recent_behavioral_data AS
SELECT 
    user_id,
    type,
    content,
    metadata,
    created_at
FROM behavioral_memory
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;
