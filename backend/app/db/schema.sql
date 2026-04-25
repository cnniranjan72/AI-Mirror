-- AIMirror Database Schema (Neon PostgreSQL + pgvector)

CREATE EXTENSION IF NOT EXISTS vector;

-- Raw events from Chrome Extension
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    reel_id TEXT NOT NULL,
    username TEXT,
    caption TEXT,
    hashtags JSONB DEFAULT '[]',
    audio TEXT,
    watch_time FLOAT NOT NULL DEFAULT 0,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id TEXT NOT NULL,
    raw_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_username ON events(username);

-- Enriched + expanded text embeddings
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    source_event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
    text TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    doc_type TEXT NOT NULL DEFAULT 'event',
    metadata JSONB DEFAULT '{}',
    content_tsv TSVECTOR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_user ON embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_type ON embeddings(doc_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_user_type ON embeddings(user_id, doc_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
    ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_embeddings_tsv ON embeddings USING gin(content_tsv);

-- Auto-populate tsvector on insert/update
CREATE OR REPLACE FUNCTION embeddings_tsv_trigger() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('english', COALESCE(NEW.text, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trig_embeddings_tsv ON embeddings;
CREATE TRIGGER trig_embeddings_tsv
    BEFORE INSERT OR UPDATE ON embeddings
    FOR EACH ROW EXECUTE FUNCTION embeddings_tsv_trigger();

-- Persona snapshots
CREATE TABLE IF NOT EXISTS personas (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    interest_vector JSONB DEFAULT '{}',
    behavior_vector JSONB DEFAULT '{}',
    persona_label TEXT,
    traits JSONB DEFAULT '{}',
    strengths JSONB DEFAULT '[]',
    weaknesses JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    confidence FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_personas_user ON personas(user_id);
CREATE INDEX IF NOT EXISTS idx_personas_created ON personas(created_at DESC);

-- RL actions log
CREATE TABLE IF NOT EXISTS actions_log (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_data JSONB DEFAULT '{}',
    state JSONB DEFAULT '{}',
    reward FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_actions_user ON actions_log(user_id);
CREATE INDEX IF NOT EXISTS idx_actions_created ON actions_log(created_at DESC);

ANALYZE events;
ANALYZE embeddings;
ANALYZE personas;
ANALYZE actions_log;
