-- AIMirror V4: Trace persistence, foreign keys, cascading deletes, metrics

-- ==================== PIPELINE TRACES ====================
CREATE TABLE IF NOT EXISTS pipeline_traces (
    id SERIAL PRIMARY KEY,
    trace_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    query TEXT,
    intent_type TEXT,
    intent_confidence FLOAT,
    reasoning_mode TEXT,
    plan_confidence FLOAT,
    runtime_load_ms FLOAT DEFAULT 0,
    planning_ms FLOAT DEFAULT 0,
    retrieval_ms FLOAT DEFAULT 0,
    ranking_ms FLOAT DEFAULT 0,
    fusion_ms FLOAT DEFAULT 0,
    decision_ms FLOAT DEFAULT 0,
    context_build_ms FLOAT DEFAULT 0,
    verbalization_ms FLOAT DEFAULT 0,
    total_ms FLOAT DEFAULT 0,
    snapshot_id TEXT,
    snapshot_version INTEGER,
    self_model_id TEXT,
    inference_count INTEGER DEFAULT 0,
    reflection_count INTEGER DEFAULT 0,
    behavior_object_count INTEGER DEFAULT 0,
    evidence_count INTEGER DEFAULT 0,
    retrieved_count INTEGER DEFAULT 0,
    facts_generated INTEGER DEFAULT 0,
    citations_created INTEGER DEFAULT 0,
    duplicates_removed INTEGER DEFAULT 0,
    aggregate_confidence FLOAT,
    decision_input_facts INTEGER DEFAULT 0,
    decision_output_facts INTEGER DEFAULT 0,
    decision_conflicts INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    response_length INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT FALSE,
    errors JSONB DEFAULT '[]',
    trace_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_traces_user ON pipeline_traces(user_id);
CREATE INDEX IF NOT EXISTS idx_traces_created ON pipeline_traces(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_traces_success ON pipeline_traces(success);
CREATE INDEX IF NOT EXISTS idx_traces_intent ON pipeline_traces(intent_type);

-- ==================== COGNITIVE METRICS ====================
CREATE TABLE IF NOT EXISTS cognitive_metrics (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_tags JSONB DEFAULT '{}',
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_user ON cognitive_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON cognitive_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded ON cognitive_metrics(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_user_name ON cognitive_metrics(user_id, metric_name);

-- ==================== FOREIGN KEY CLEANUP ====================
-- Ensure behavior_objects reference valid user_ids with proper cascade
ALTER TABLE behavior_objects DROP CONSTRAINT IF EXISTS fk_behavior_objects_user;
-- Note: user_id is TEXT not a FK to users table (no users table), so we add
-- cascading deletes at the application level instead.

-- Add cascading deletes from events to embeddings
ALTER TABLE embeddings DROP CONSTRAINT IF EXISTS embeddings_source_event_id_fkey;
ALTER TABLE embeddings ADD CONSTRAINT embeddings_source_event_id_fkey
    FOREIGN KEY (source_event_id) REFERENCES events(id) ON DELETE CASCADE;

-- Add foreign key from evidence to behavior_objects (logical link via unique_id)
-- This is a soft FK since evidence stores supporting_behavior_objects as JSONB

-- Add foreign key from identity_snapshots to identities
ALTER TABLE identity_snapshots DROP CONSTRAINT IF EXISTS fk_snapshots_identity;
ALTER TABLE identity_snapshots ADD CONSTRAINT fk_snapshots_identity
    FOREIGN KEY (identity_id) REFERENCES identities(identity_id) ON DELETE CASCADE;

-- Add foreign key from self_models to identity_snapshots
ALTER TABLE self_models DROP CONSTRAINT IF EXISTS fk_self_models_snapshot;
ALTER TABLE self_models ADD CONSTRAINT fk_self_models_snapshot
    FOREIGN KEY (identity_snapshot_id) REFERENCES identity_snapshots(snapshot_id) ON DELETE SET NULL;

-- Index for faster evidence lookups by user+type
CREATE INDEX IF NOT EXISTS idx_evidence_user_type ON evidence(user_id, evidence_type);

-- ANALYZE
ANALYZE pipeline_traces;
ANALYZE cognitive_metrics;
