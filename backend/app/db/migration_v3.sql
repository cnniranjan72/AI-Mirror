-- AIMirror V3 Architecture Migration
-- Tables for all core V3 entities
-- Run AFTER schema.sql

-- ==================== BEHAVIOR OBJECTS ====================
CREATE TABLE IF NOT EXISTS behavior_objects (
    id SERIAL PRIMARY KEY,
    unique_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    subtopics JSONB DEFAULT '[]',
    representative_embedding VECTOR(384),
    keywords JSONB DEFAULT '[]',
    creators JSONB DEFAULT '[]',
    creator_diversity_score FLOAT DEFAULT 0.0,
    engagement_statistics JSONB DEFAULT '{}',
    watch_statistics JSONB DEFAULT '{}',
    temporal_statistics JSONB DEFAULT '{}',
    trend_information JSONB DEFAULT '{}',
    lifecycle_state TEXT DEFAULT 'emerging',
    importance_score FLOAT DEFAULT 0.0,
    confidence_score FLOAT DEFAULT 0.0,
    stability_score FLOAT DEFAULT 0.0,
    evidence_references JSONB DEFAULT '[]',
    supporting_event_ids JSONB DEFAULT '[]',
    supporting_cluster_ids JSONB DEFAULT '[]',
    evolution_history JSONB DEFAULT '[]',
    version INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_behavior_objects_user ON behavior_objects(user_id);
CREATE INDEX IF NOT EXISTS idx_behavior_objects_topic ON behavior_objects(topic);
CREATE INDEX IF NOT EXISTS idx_behavior_objects_lifecycle ON behavior_objects(lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_behavior_objects_updated ON behavior_objects(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_behavior_objects_confidence ON behavior_objects(confidence_score DESC);

-- ==================== EVIDENCE ====================
CREATE TABLE IF NOT EXISTS evidence (
    id SERIAL PRIMARY KEY,
    evidence_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    supporting_events JSONB DEFAULT '[]',
    supporting_clusters JSONB DEFAULT '[]',
    supporting_behavior_objects JSONB DEFAULT '[]',
    confidence FLOAT NOT NULL DEFAULT 0.0,
    weight FLOAT NOT NULL DEFAULT 0.0,
    counter_evidence_ids JSONB DEFAULT '[]',
    conflicting_observations JSONB DEFAULT '[]',
    conflict_resolution TEXT,
    net_confidence FLOAT,
    explanation TEXT NOT NULL,
    key_metrics JSONB DEFAULT '{}',
    time_window_start TIMESTAMPTZ NOT NULL,
    time_window_end TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_user ON evidence(user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence(evidence_type);
CREATE INDEX IF NOT EXISTS idx_evidence_confidence ON evidence(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_evidence_created ON evidence(created_at DESC);

-- ==================== INFERENCES ====================
CREATE TABLE IF NOT EXISTS inferences (
    id SERIAL PRIMARY KEY,
    inference_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    inference_type TEXT NOT NULL,
    label TEXT NOT NULL,
    description TEXT NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.0,
    importance FLOAT NOT NULL DEFAULT 0.0,
    strength FLOAT NOT NULL DEFAULT 0.0,
    supporting_evidence JSONB DEFAULT '[]',
    evidence_summary TEXT,
    affected_topics JSONB DEFAULT '[]',
    affected_creators JSONB DEFAULT '[]',
    affected_behaviors JSONB DEFAULT '[]',
    recommendation_seed TEXT,
    suggested_actions JSONB DEFAULT '[]',
    inferred_at TIMESTAMPTZ NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    rule_name TEXT,
    context_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inferences_user ON inferences(user_id);
CREATE INDEX IF NOT EXISTS idx_inferences_type ON inferences(inference_type);
CREATE INDEX IF NOT EXISTS idx_inferences_strength ON inferences(strength DESC);
CREATE INDEX IF NOT EXISTS idx_inferences_created ON inferences(inferred_at DESC);
CREATE INDEX IF NOT EXISTS idx_inferences_rule ON inferences(rule_name);

-- ==================== IDENTITIES ====================
CREATE TABLE IF NOT EXISTS identities (
    id SERIAL PRIMARY KEY,
    identity_id TEXT UNIQUE NOT NULL,
    user_id TEXT UNIQUE NOT NULL,
    behavior_profile JSONB DEFAULT '{}',
    interest_graph JSONB DEFAULT '{}',
    creator_graph JSONB DEFAULT '{}',
    learning_style JSONB DEFAULT '{}',
    attention_profile JSONB DEFAULT '{}',
    exploration_profile JSONB DEFAULT '{}',
    consistency_profile JSONB DEFAULT '{}',
    habit_profile JSONB DEFAULT '{}',
    motivation_signals JSONB DEFAULT '{}',
    behavior_timeline JSONB DEFAULT '[]',
    dominant_topics JSONB DEFAULT '[]',
    emerging_topics JSONB DEFAULT '[]',
    declining_topics JSONB DEFAULT '[]',
    long_term_preferences JSONB DEFAULT '{}',
    overall_confidence FLOAT DEFAULT 0.0,
    identity_completeness FLOAT DEFAULT 0.0,
    identity_version INTEGER DEFAULT 1,
    evolution_history JSONB DEFAULT '[]',
    major_shifts JSONB DEFAULT '[]',
    source_behavior_objects JSONB DEFAULT '[]',
    source_inferences JSONB DEFAULT '[]',
    source_evidence JSONB DEFAULT '[]',
    source_reflections JSONB DEFAULT '[]',
    last_behavior_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_identities_user ON identities(user_id);
CREATE INDEX IF NOT EXISTS idx_identities_version ON identities(identity_version DESC);
CREATE INDEX IF NOT EXISTS idx_identities_confidence ON identities(overall_confidence DESC);

-- ==================== IDENTITY SNAPSHOTS ====================
CREATE TABLE IF NOT EXISTS identity_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_id TEXT UNIQUE NOT NULL,
    identity_id TEXT NOT NULL,
    identity_version INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    snapshot_data JSONB NOT NULL,
    overall_confidence FLOAT DEFAULT 0.0,
    identity_completeness FLOAT DEFAULT 0.0,
    dominant_topics JSONB DEFAULT '[]',
    emerging_topics JSONB DEFAULT '[]',
    declining_topics JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    valid_until TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    snapshot_timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_identity ON identity_snapshots(identity_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_user ON identity_snapshots(user_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_version ON identity_snapshots(identity_version DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_active ON identity_snapshots(is_active) WHERE is_active = TRUE;

-- ==================== SELF MODELS ====================
CREATE TABLE IF NOT EXISTS self_models (
    id SERIAL PRIMARY KEY,
    self_model_id TEXT UNIQUE NOT NULL,
    user_id TEXT UNIQUE NOT NULL,
    identity_snapshot_id TEXT NOT NULL,
    beliefs JSONB DEFAULT '[]',
    strong_beliefs JSONB DEFAULT '[]',
    uncertain_beliefs JSONB DEFAULT '[]',
    uncertainty_map JSONB DEFAULT '{}',
    overall_confidence FLOAT DEFAULT 0.0,
    model_completeness FLOAT DEFAULT 0.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_self_models_user ON self_models(user_id);
CREATE INDEX IF NOT EXISTS idx_self_models_snapshot ON self_models(identity_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_self_models_confidence ON self_models(overall_confidence DESC);

-- ==================== MEMORIES (unified) ====================
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    memory_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384),
    context JSONB DEFAULT '{}',
    tags JSONB DEFAULT '[]',
    importance_score FLOAT DEFAULT 0.0,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMPTZ,
    related_memory_ids JSONB DEFAULT '[]',
    source_event_ids JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMPTZ,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_memories_user_type ON memories(user_id, memory_type);

-- ==================== REFLECTIONS ====================
CREATE TABLE IF NOT EXISTS reflections (
    id SERIAL PRIMARY KEY,
    reflection_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    reflection_type TEXT NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    summary TEXT NOT NULL,
    key_insights JSONB DEFAULT '[]',
    metrics JSONB DEFAULT '{}',
    patterns_identified JSONB DEFAULT '[]',
    changes_detected JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    confidence FLOAT DEFAULT 0.0,
    event_count INTEGER DEFAULT 0,
    memory_refs JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reflections_user ON reflections(user_id);
CREATE INDEX IF NOT EXISTS idx_reflections_type ON reflections(reflection_type);
CREATE INDEX IF NOT EXISTS idx_reflections_created ON reflections(created_at DESC);

-- ==================== GOALS ====================
CREATE TABLE IF NOT EXISTS goals (
    id SERIAL PRIMARY KEY,
    goal_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    goal_description TEXT NOT NULL,
    goal_type TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    progress FLOAT DEFAULT 0.0,
    alignment_score FLOAT DEFAULT 0.0,
    supporting_behaviors JSONB DEFAULT '[]',
    conflicting_behaviors JSONB DEFAULT '[]',
    milestones JSONB DEFAULT '[]',
    related_event_ids JSONB DEFAULT '[]',
    target_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id);
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_type ON goals(goal_type);

-- ==================== RUNTIME METRICS ====================
CREATE TABLE IF NOT EXISTS runtime_metrics (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    build_latency_ms FLOAT DEFAULT 0.0,
    snapshot_version INTEGER DEFAULT 0,
    inference_count INTEGER DEFAULT 0,
    reflection_count INTEGER DEFAULT 0,
    goal_count INTEGER DEFAULT 0,
    memory_counts JSONB DEFAULT '{}',
    cache_hit BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_runtime_metrics_user ON runtime_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_runtime_metrics_created ON runtime_metrics(created_at DESC);

-- ==================== UPDATE TRIGGERS ====================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_behavior_objects_updated_at
    BEFORE UPDATE ON behavior_objects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_identities_updated_at
    BEFORE UPDATE ON identities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_self_models_updated_at
    BEFORE UPDATE ON self_models
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_goals_updated_at
    BEFORE UPDATE ON goals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==================== GIN INDEXES for JSONB query performance ====================
CREATE INDEX IF NOT EXISTS idx_behavior_objects_metadata_gin ON behavior_objects USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_behavior_objects_evidence_gin ON behavior_objects USING GIN (evidence_references);
CREATE INDEX IF NOT EXISTS idx_behavior_objects_keywords_gin ON behavior_objects USING GIN (keywords);
CREATE INDEX IF NOT EXISTS idx_behavior_objects_creators_gin ON behavior_objects USING GIN (creators);
CREATE INDEX IF NOT EXISTS idx_behavior_objects_tags_gin ON behavior_objects USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_behavior_objects_engagement_gin ON behavior_objects USING GIN (engagement_statistics);

CREATE INDEX IF NOT EXISTS idx_evidence_metadata_gin ON evidence USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_evidence_key_metrics_gin ON evidence USING GIN (key_metrics);
CREATE INDEX IF NOT EXISTS idx_evidence_counter_gin ON evidence USING GIN (counter_evidence_ids);

CREATE INDEX IF NOT EXISTS idx_inferences_metadata_gin ON inferences USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_inferences_affected_topics_gin ON inferences USING GIN (affected_topics);
CREATE INDEX IF NOT EXISTS idx_inferences_supporting_gin ON inferences USING GIN (supporting_evidence);

CREATE INDEX IF NOT EXISTS idx_identities_metadata_gin ON identities USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_identities_dominant_topics_gin ON identities USING GIN (dominant_topics);
CREATE INDEX IF NOT EXISTS idx_identities_behavior_profile_gin ON identities USING GIN (behavior_profile);
CREATE INDEX IF NOT EXISTS idx_identities_interest_graph_gin ON identities USING GIN (interest_graph);

CREATE INDEX IF NOT EXISTS idx_snapshots_metadata_gin ON identity_snapshots USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_self_models_beliefs_gin ON self_models USING GIN (beliefs);
CREATE INDEX IF NOT EXISTS idx_self_models_uncertainty_gin ON self_models USING GIN (uncertainty_map);

CREATE INDEX IF NOT EXISTS idx_reflections_insights_gin ON reflections USING GIN (key_insights);
CREATE INDEX IF NOT EXISTS idx_reflections_metrics_gin ON reflections USING GIN (metrics);

CREATE INDEX IF NOT EXISTS idx_goals_metadata_gin ON goals USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_goals_milestones_gin ON goals USING GIN (milestones);

CREATE INDEX IF NOT EXISTS idx_memories_tags_gin ON memories USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_memories_metadata_gin ON memories USING GIN (metadata);

-- ANALYZE new tables
ANALYZE behavior_objects;
ANALYZE evidence;
ANALYZE inferences;
ANALYZE identities;
ANALYZE identity_snapshots;
ANALYZE self_models;
ANALYZE memories;
ANALYZE reflections;
ANALYZE goals;
ANALYZE runtime_metrics;
