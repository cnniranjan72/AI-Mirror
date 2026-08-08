# AIMirror — Behavioral Digital Twin Engine

<p align="center">
  <img src="https://img.shields.io/badge/Version-3.0.0-6366f1?style=for-the-badge&logo=python" alt="Version">
  <img src="https://img.shields.io/badge/License-MIT-10b981?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react" alt="React">
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/pgvector-0.7-FF6B35?style=for-the-badge&logo=postgresql" alt="pgvector">
  <img src="https://img.shields.io/badge/Chrome_Extension-MV3-4285F4?style=for-the-badge&logo=googlechrome" alt="Chrome Extension">
  <img src="https://img.shields.io/badge/Instagram-%23E4405F?style=for-the-badge&logo=instagram" alt="Instagram">
  <img src="https://img.shields.io/badge/YouTube-%23FF0000?style=for-the-badge&logo=youtube" alt="YouTube">
</p>

<p align="center">
  <i>A production-grade cognitive digital twin engine that constructs, evolves, and explains a complete behavioral identity model from social media activity.</i>
</p>

<p align="center">
  <b>🌐 Live:</b> <a href="https://aimirror-dashboard.onrender.com">aimirror-dashboard.onrender.com</a>
  &nbsp;·&nbsp;
  <b>API:</b> <a href="https://aimirror-backend-cu00.onrender.com/docs">aimirror-backend-cu00.onrender.com/docs</a>
</p>

> Both run on Render's free tier — the backend spins down after ~15 min idle, so the first request after a quiet period takes 30-60s to wake up. Click "Load Demo Data" on the landing page for an instant look without installing anything; the Chrome extension is only needed to build a twin from your own browsing (see [Load Chrome Extension](#load-chrome-extension)).

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Cognitive Pipeline](#cognitive-pipeline)
- [Database Schema](#database-schema)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Quick Start](#quick-start)
- [User Guide](#user-guide)
- [API Reference](#api-reference)
- [Dashboard Pages](#dashboard-pages)
- [Configuration](#configuration)
- [Architecture Decisions](#architecture-decisions)
- [Production Hardening](#production-hardening)
- [Development](#development)
- [Glossary](#glossary)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

AIMirror is a **behavioral digital twin engine** that transforms raw social media activity into a structured, explainable cognitive identity model. It goes beyond simple analytics by constructing a multi-dimensional behavioral identity — spanning interests, creators, attention patterns, learning styles, and engagement habits — and evolving it over time through a deterministic cognitive pipeline.

### Core Capabilities

| Capability | Description |
|---|---|
| **Behavioral Ingestion** | Chrome Extension extracts activity from Instagram Reels and YouTube (Watch + Shorts) — watch time, engagement, metadata, content popularity |
| **Knowledge Consolidation** | Clusters raw events into hierarchically-organized behavior objects by topic, creator, and temporal pattern |
| **Multi-Dimensional Evidence** | Collects evidence across 5 dimensions: topical affinity, creator relationship, temporal consistency, interaction pattern, and engagement depth |
| **Rule-Based Inference** | Generates high-confidence inferences from evidence without statistical black boxes |
| **Identity Construction** | Builds a 9-sub-profile identity: behavior, interest graph, creator graph, learning style, attention, exploration, consistency, habit, and motivation |
| **Temporal Snapshotting** | Automatically captures identity snapshots when behavioral shifts cross configurable thresholds |
| **Self-Awareness Model** | Maintains a self-model with explicit beliefs, strong beliefs, and uncertainty domains |
| **Full Explainability** | Every decision, inference, and identity trait is traceable to its source evidence and behavior objects |
| **Online RL Layer** | Closed-loop contextual bandit learns personalized wellbeing interventions from alignment changes |
| **Multi-Provider LLM** | OpenAI, Anthropic, or Ollama — the LLM only verbalizes; never reasons or decides |

### Philosophy

- **Deterministic reasoning, not magic**: Every inference, identity trait, and decision follows explicit rules. No statistical black boxes.
- **Explainability by construction**: Every output has a complete, traversable reasoning chain back to raw events.
- **Privacy-first architecture**: Your data, your model. Complete export and deletion capabilities.
- **Transparency over optimization**: The system is designed to help you understand your behavior, not to optimize engagement.

---

## System Architecture

```mermaid
graph TB
    subgraph "Chrome Extension"
        IG[Instagram Reels<br/>content.js] --> BUF[Event Buffer<br/>10 events / 30s]
        YT[YouTube Watch + Shorts<br/>youtube-content.js] --> BUF
        BUF --> BW[Background Worker<br/>background.js]
    end

    subgraph "FastAPI Backend"
        BW -->|POST /ingest| GW[Behavior Gateway]
        GW --> V3[V3 Cognitive Pipeline]

        subgraph "V3 Cognitive Pipeline"
            KC[Knowledge<br/>Consolidation] --> BO[Behavior<br/>Objects]
            BO --> EE[Evidence<br/>Engine]
            EE --> IE[Inference<br/>Engine]
            IE --> IDE[Identity<br/>Engine]
            IDE --> SNAP[Snapshot]
            IDE --> SM[Self-Model]
        end

        subgraph "Query Pipeline"
            Q[Query] --> PL[Planner]
            PL --> RET[Retriever]
            RET --> RANK[Memory<br/>Ranker]
            RANK --> FE[Fusion<br/>Engine]
            FE --> DE[Decision<br/>Engine]
            DE --> CB[Context<br/>Builder]
            CB --> LLM[LLM<br/>Verbalizer]
            LLM --> DF[Deterministic<br/>Fallback]
        end

        subgraph "RL Layer"
            RL[Contextual Bandit<br/>ε-greedy Q-learning]
        end

        V3 --> PG[PostgreSQL + pgvector]
        Q --> PG
        RL --> PG
    end

    subgraph "React Dashboard"
        DASH[Dashboard App] --> PAGES[25 Pages]
        DASH --> COMP[Key Components]
        COMP --> EP[ExplainabilityPanel]
        COMP --> II[IdentityInspector]
        COMP --> ED[EvidenceDrawer]
        COMP --> DT[DecisionTree]
        COMP --> CC[CharacterCreature3D]
    end

    PG --> API[30+ API Endpoints]
    API --> DASH
```

### System Data Flow

```mermaid
sequenceDiagram
    participant Ext as Chrome Extension
    participant API as FastAPI Backend
    participant PL as V3 Pipeline
    participant DB as PostgreSQL
    participant DS as Dashboard

    Note over Ext: Instagram Reels or YouTube<br/>Watch/Shorts — DOM Observation

    Ext->>API: POST /ingest<br/>{user_id, events[], platform}

    API->>PL: Behavior Gateway<br/>(normalize events)

    PL->>PL: Knowledge Consolidation<br/>(cluster by topic)
    PL->>PL: Behavior Objects<br/>(topic, importance, creators)
    PL->>PL: Evidence Engine<br/>(5-dimension evidence)
    PL->>PL: Inference Engine<br/>(rule-based reasoning)
    PL->>PL: Identity Engine<br/>(9 sub-profiles)

    PL->>PL: Identity Snapshot<br/>(on significant shift)
    PL->>PL: Self-Model<br/>(beliefs, uncertainties)

    PL-->>DB: Store results
    API->>DB: Vector Embeddings<br/>(384-dim pgvector)

    Note over DS: User asks a question

    DS->>API: POST /query<br/>{user_id, query}

    API->>API: Planner<br/>(intent detection)
    API->>DB: Retriever<br/>(multi-source)
    API->>API: Memory Ranker<br/>(identity alignment)
    API->>API: Fusion Engine<br/>(dedup, citations)
    API->>API: Decision Engine<br/>(threshold, diversity)
    API->>API: Context Builder
    API->>API: LLM Verbalizer<br/>(format only)

    alt LLM unavailable
        API->>API: Deterministic Fallback
    end

    API-->>DS: Response + trace_id

    DS->>API: GET /explain/{trace_id}
    API-->>DS: Full reasoning chain
```

### Event Ingestion Flow

```mermaid
flowchart LR
    subgraph "Ingestion"
        IG[Instagram Reels<br/>content.js] -->|POST /ingest| BG[Behavior Gateway]
        YT[YouTube Watch + Shorts<br/>youtube-content.js] -->|POST /ingest| BG
        BG -->|Normalized Events| KC[Knowledge<br/>Consolidation]
    end

    subgraph "V3 Pipeline"
        KC -->|Topic Clusters| BO_B[Behavior Objects]
        BO_B -->|5-Dimensions| EV[Evidence Engine]
        EV -->|Rules| INF[Inference Engine]
        INF -->|9 Profiles| ID[Identity Engine]

        ID -->|Shift > Threshold| SS[Snapshot]
        ID -->|Beliefs| SELF[Self-Model]

        KC -->|Text| EMB[Embeddings<br/>384-dim]
    end

    subgraph "Storage"
        BO_B -->|Write| PG[(PostgreSQL<br/>+ pgvector)]
        EV --> PG
        INF --> PG
        ID --> PG
        SS --> PG
        SELF --> PG
        EMB --> PG
    end

    subgraph "RL Feedback"
        ID -->|Alignment Score| RL[Contextual Bandit]
        RL -->|Reward Signal| PG
    end
```

### Query Pipeline Flow

```mermaid
flowchart TB
    QRY[User Query] --> PLAN[Planner]

    subgraph "Planner"
        PLAN --> INT[Intent Classification]
        PLAN --> RM[Reasoning Mode]
        PLAN --> RD[Retrieval Directives]
    end

    INT --> RET[Retriever]

    subgraph "Retriever"
        RET --> BOQ[Behavior Objects]
        RET --> EVQ[Evidence]
        RET --> IDQ[Identity Snapshots]
        RET --> SMQ[Self-Models]
        RET --> GOQ[Goals]
        RET --> RFQ[Reflections]
        RET --> INQ[Inferences]
    end

    BOQ --> RANK[Memory Ranker]
    EVQ --> RANK
    IDQ --> RANK
    SMQ --> RANK
    GOQ --> RANK
    RFQ --> RANK
    INQ --> RANK

    RANK -->|Identity/Goal Alignment Score| FUSE[Fusion Engine]
    FUSE -->|Dedup + Citations| DEC[Decision Engine]

    DEC -->|Confidence Threshold| DEC
    DEC -->|Diversity Enforcement| DEC
    DEC -->|Goal Alignment| DEC
    DEC -->|Conflict Detection| DEC

    DEC -->|Fused Facts| CTX[Context Builder]
    CTX -->|CharacterContext| LLMV[LLM Verbalizer]

    LLMV -->|Format Only<br/>No Reasoning| RESP[Response]

    LLMV -->|Error/Circuit Break| FALLBACK[Deterministic Template]
    FALLBACK --> RESP

    RESP --> TRACE["Pipeline Trace<br/>(per-stage timing + state)"]
```

### Component Architecture

```mermaid
graph LR
    subgraph "Frontend (React Dashboard)"
        A[App Shell] --> B[Chat Page]
        A --> C[Dashboard Pages]
        A --> D[Explainability Components]
        A --> E[Visualization Components]

        B --> F[API Client<br/>axios]
        C --> F
        D --> F
        E --> F
    end

    subgraph "Backend (FastAPI)"
        F --> G[Ingest API]
        F --> H[Query API]
        F --> I[Profile API]
        F --> J[Explainability API]
        F --> K[Identity API]
        F --> L[RL API]
        F --> M[Guardian API]
        F --> N[Auth API]

        G --> O[V3 Pipeline Orchestrator]
        H --> P[Cognitive Pipeline]
        I --> Q[Persona Service]
        J --> R[DB Queries]
        K --> S[Identity Engine]
        L --> T[RL Layer]
        M --> U[Wellbeing Service]
    end

    subgraph "Data Layer"
        O --> V[(PostgreSQL<br/>+ pgvector)]
        P --> V
        Q --> V
        R --> V
        S --> V
        T --> V
        U --> V

        V --> W[vectors: 384-dim<br/>pgvector index]
        V --> X[full-text: TSVECTOR<br/>GIN index]
        V --> Y[JSONB: GIN indexes<br/>on metadata]
    end

    subgraph "External"
        N --> Z[PBKDF2 + HMAC Auth]
        P --> AA[LLM Provider<br/>OpenAI/Anthropic/Ollama]
        G --> AB[Chrome Extension<br/>content.js → background.js]
    end
```

---

## Cognitive Pipeline

### Stage 1: Behavior Gateway

Normalizes incoming events from any source into a unified `BehaviorEvent` schema.

| Input | Process | Output |
|---|---|---|
| Raw event payloads (extension, API, seed) | Field mapping, type coercion, dedup key generation | `List[BehaviorEvent]` with normalized `content_id`, `creator`, `caption`, `hashtags`, `watch_time`, etc. |

### Stage 2: Knowledge Consolidation

Clusters normalized events into hierarchically-organized behavior objects by topic, creator, and temporal pattern.

| Input | Process | Output |
|---|---|---|
| `List[BehaviorEvent]` | Topic extraction → Creator aggregation → Temporal clustering → Importance scoring | `List[BehaviorObject]` with topics, keywords, creators, importance_score, confidence, lifecycle_state, temporal trends |

### Stage 3: Evidence Collection

Collects evidence across 5 dimensions:

| Dimension | What It Measures |
|---|---|
| **Topical** | Strength of topic affinity based on watch time and frequency |
| **Creator** | Relationship depth with specific creators |
| **Temporal** | Consistency patterns across time of day, day of week |
| **Interaction** | Engagement signals (likes, saves, shares, comments) |
| **Engagement** | Watch time depth and completion patterns |

| Input | Process | Output |
|---|---|---|
| `List[BehaviorObject]` | 5-dimension scoring → Confidence weighting → Conflict resolution | `List[Evidence]` with type, confidence, weight, net_confidence, explanation, linked behavior objects |

### Stage 4: Inference Generation

Rule-driven reasoning engine that produces inferences from evidence + behavior objects.

| Rule Type | Examples |
|---|---|
| **High-Confidence** | Repeated high watch time on same topic → "Strong interest in [topic]" |
| **Low-Confidence** | New topic appearing → "Emerging interest in [topic]" |
| **Temporal** | Consistent evening usage → "Evening browsing pattern" |
| **Engagement** | High like+save ratio → "Curatorial behavior pattern" |
| **Diversity** | Broad topic spread → "Exploratory consumption style" |

| Input | Process | Output |
|---|---|---|
| `List[Evidence]` + `List[BehaviorObject]` | Rule matching → Confidence scoring → Dedup | `List[Inference]` with type, label, description, confidence, importance, strength, rule_name |

### Stage 5: Reflection

Periodic summarization that synthesizes patterns and detected changes across all cognitive state.

| Input | Process | Output |
|---|---|---|
| Inferences + Evidence + Behavior Objects | Pattern detection → Change identification → Summary generation | `List[Reflection]` with summary, key_insights, patterns_identified, recommendations |

### Stage 6: Identity Construction

Builds or evolves a 9-sub-profile behavioral identity:

```mermaid
flowchart TB
    subgraph "Identity Engine Inputs"
        INF[Inferences] --> ID[Identity Engine]
        EV[Evidence] --> ID
        BO[Behavior Objects] --> ID
        EXIST[Existing Identity] --> ID
    end

    subgraph "9 Sub-Profiles"
        ID --> BHV[Behavior Profile<br/>Watch time, sessions, engagement]

        ID --> IG[Interest Graph<br/>Topic hierarchy, affinity, decay]

        ID --> CG[Creator Graph<br/>Relationships, loyalty, discovery]

        ID --> LS[Learning Style<br/>Tutorial vs entertainment]

        ID --> AP[Attention Profile<br/>Session length, focus score]

        ID --> XP[Exploration Profile<br/>Discovery rate, switching]

        ID --> CP[Consistency Profile<br/>Routine strength, patterns]

        ID --> HP[Habit Profile<br/>Automatic vs intentional]

        ID --> MS[Motivation Signals<br/>Curiosity vs habit vs social]
    end

    subgraph "Identity Output"
        BHV --> CONF[Confidence Amalgamation]
        IG --> CONF
        CG --> CONF
        LS --> CONF
        AP --> CONF
        XP --> CONF
        CP --> CONF
        HP --> CONF
        MS --> CONF

        CONF --> VER[Version Increment]
        VER --> OUT[Identity<br/>overall_confidence<br/>identity_completeness<br/>identity_version]
    end
```

| Sub-Profile | Description |
|---|---|
| **Behavior Profile** | Watch time distributions, session patterns, engagement ratios |
| **Interest Graph** | Topic hierarchy with affinity scores, topic discovery/decay rates |
| **Creator Graph** | Creator relationships: frequency, loyalty, discovery patterns |
| **Learning Style** | Tutorial vs. entertainment ratio, depth vs. breadth preference |
| **Attention Profile** | Session length distribution, interruption resistance, focus score |
| **Exploration Profile** | New content discovery rate, topic switching frequency |
| **Consistency Profile** | Daily/weekly routine strength, time-of-day patterns |
| **Habit Profile** | Automatic vs. intentional usage patterns |
| **Motivation Signals** | Curiosity-driven vs. habit-driven vs. social-driven indicators |

| Input | Process | Output |
|---|---|---|
| Inferences + Evidence + Behavior Objects + existing identity | Sub-profile scoring → Confidence amalgamation → Version increment | `Identity` with 9 sub-profiles, overall_confidence, identity_completeness, version |

### Stage 7: Snapshot

Captures temporal snapshots of identity, persisted only when behavioral shift crosses a configurable threshold.

| Input | Process | Output |
|---|---|---|
| Identity | Shift detection → Snapshot serialization | `IdentitySnapshot` with dominant_topics, emerging_topics, overall_confidence, completeness |

### Stage 8: Self-Model

Constructs a self-awareness model with explicit belief representation.

| Component | Description |
|---|---|
| **Beliefs** | High-confidence identity traits the system is sure about |
| **Strong Beliefs** | Very high-confidence beliefs (repeatedly confirmed) |
| **Uncertain Beliefs** | Low-confidence traits needing more data |
| **Uncertainty Map** | Domains where the system knows it lacks data |

### Query Pipeline

```mermaid
flowchart LR
    Q[Query] --> RB[RuntimeBuilder]
    RB --> PL[Planner]

    subgraph "Planner"
        PL --> INT[Intent Classification]
        PL --> RM[Reasoning Mode]
        PL --> DIR[Retrieval Directives]
    end

    INT --> RET[Retriever]

    subgraph "Retriever"
        RET --> BO[Behavior Objects]
        RET --> EV[Evidence]
        RET --> ID[Identity Snapshots]
        RET --> SM[Self-Models]
        RET --> GO[Goals]
        RET --> RF[Reflections]
        RET --> INF[Inferences]
    end

    BO --> MR[MemoryRanker]
    EV --> MR
    ID --> MR
    SM --> MR
    GO --> MR
    RF --> MR
    INF --> MR

    MR --> FE[FusionEngine]
    FE --> DE[DecisionEngine]

    subgraph "Decision Engine"
        DE --> CT[Confidence Threshold]
        DE --> DV[Diversity Enforcement]
        DE --> GA[Goal Alignment]
        DE --> CD[Conflict Detection]
    end

    DE --> CB[ContextBuilder]
    CB --> LV[LLMVerbalizer]

    LV -->|Success| RESP[Response]
    LV -->|Fatal Error| FALL[Deterministic Fallback]
    FALL --> RESP
```

| Stage | Responsibility |
|---|---|
| **RuntimeBuilder** | Pre-loads identity snapshot + inferences from DB |
| **Planner** | Classifies intent, selects reasoning mode, plans retrieval directives |
| **Retriever** | Multi-source retrieval from 7 cognitive entity types |
| **MemoryRanker** | Ranks retrieved items by identity/goal alignment |
| **FusionEngine** | Deduplicates, cites sources, constructs `FusedFact`s |
| **DecisionEngine** | Applies confidence threshold, diversity enforcement, conflict detection |
| **ContextBuilder** | Assembles `CharacterContext` for verbalization |
| **LLMVerbalizer** | Formats response — NEVER reasons or decides. Falls back to deterministic template |

---

## Database Schema

```mermaid
erDiagram
    events ||--o{ embeddings : "source_event"
    identities ||--o{ identity_snapshots : "has"
    identities ||--o{ behavior_objects : "belongs_to"
    identity_snapshots ||--o{ self_models : "snapshot"
    identities ||--o{ evidence : "has"
    identities ||--o{ inferences : "has"
    identities ||--o{ memories : "has"
    identities ||--o{ reflections : "has"
    identities ||--o{ goals : "has"
    identities ||--o{ pipeline_traces : "has"

    events {
        bigint id PK
        text user_id FK
        text reel_id
        text username
        text caption
        jsonb hashtags
        text audio
        double watch_time
        timestamp timestamp
        text session_id
        jsonb raw_metadata
        bool liked
        bool saved
        bool shared
        bool commented
        bool following
        text audio_id
        text profile_url
        int like_count
        int comment_count
        int repost_count
        text platform
        text surface
        timestamp created_at
    }

    embeddings {
        bigint id PK
        text user_id FK
        bigint source_event_id FK
        text text
        vector embedding
        text doc_type
        jsonb metadata
        tsvector content_tsv
        timestamp created_at
    }

    behavior_objects {
        uuid unique_id PK
        text user_id FK
        text topic
        jsonb subtopics
        vector representative_embedding
        jsonb keywords
        jsonb creators
        double creator_diversity_score
        jsonb engagement_statistics
        jsonb watch_statistics
        jsonb temporal_statistics
        jsonb trend_information
        text lifecycle_state
        double importance_score
        double confidence_score
        double stability_score
        jsonb evidence_references
        jsonb supporting_event_ids
        jsonb supporting_cluster_ids
        jsonb evolution_history
        int version
        jsonb metadata
        jsonb tags
        timestamp created_at
        timestamp updated_at
        timestamp last_accessed
        int access_count
    }

    evidence {
        uuid evidence_id PK
        text user_id FK
        text evidence_type
        jsonb supporting_events
        jsonb supporting_clusters
        jsonb supporting_behavior_objects
        double confidence
        double weight
        jsonb counter_evidence_ids
        jsonb conflicting_observations
        text conflict_resolution
        double net_confidence
        text explanation
        jsonb key_metrics
        timestamp time_window_start
        timestamp time_window_end
        jsonb metadata
        timestamp created_at
    }

    inferences {
        uuid inference_id PK
        text user_id FK
        text inference_type
        text label
        text description
        double confidence
        double importance
        double strength
        jsonb supporting_evidence
        text evidence_summary
        jsonb affected_topics
        jsonb affected_creators
        jsonb affected_behaviors
        text recommendation_seed
        jsonb suggested_actions
        timestamp inferred_at
        timestamp valid_from
        timestamp valid_until
        text rule_name
        text context_id
        jsonb metadata
        timestamp created_at
    }

    identities {
        uuid identity_id PK
        text user_id UK
        jsonb behavior_profile
        jsonb interest_graph
        jsonb creator_graph
        jsonb learning_style
        jsonb attention_profile
        jsonb exploration_profile
        jsonb consistency_profile
        jsonb habit_profile
        jsonb motivation_signals
        jsonb behavior_timeline
        jsonb dominant_topics
        jsonb emerging_topics
        jsonb declining_topics
        jsonb long_term_preferences
        double overall_confidence
        double identity_completeness
        int identity_version
        jsonb evolution_history
        jsonb major_shifts
        jsonb source_behavior_objects
        jsonb source_inferences
        jsonb source_evidence
        jsonb source_reflections
        timestamp last_behavior_at
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }

    identity_snapshots {
        uuid snapshot_id PK
        uuid identity_id FK
        int identity_version
        text user_id
        jsonb snapshot_data
        double overall_confidence
        double identity_completeness
        jsonb dominant_topics
        jsonb emerging_topics
        jsonb declining_topics
        bool is_active
        timestamp valid_until
        jsonb metadata
        timestamp snapshot_timestamp
        timestamp created_at
    }

    self_models {
        uuid self_model_id PK
        text user_id UK
        uuid identity_snapshot_id FK
        jsonb beliefs
        jsonb strong_beliefs
        jsonb uncertain_beliefs
        jsonb uncertainty_map
        double overall_confidence
        double model_completeness
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }

    memories {
        uuid memory_id PK
        text user_id FK
        text memory_type
        text content
        vector embedding
        jsonb context
        jsonb tags
        double importance_score
        int access_count
        timestamp last_accessed
        jsonb related_memory_ids
        jsonb source_event_ids
        jsonb metadata
        timestamp expires_at
        timestamp timestamp
        timestamp created_at
    }

    reflections {
        uuid reflection_id PK
        text user_id FK
        text reflection_type
        timestamp period_start
        timestamp period_end
        text summary
        jsonb key_insights
        jsonb metrics
        jsonb patterns_identified
        jsonb changes_detected
        jsonb recommendations
        double confidence
        int event_count
        jsonb memory_refs
        jsonb metadata
        timestamp created_at
    }

    pipeline_traces {
        bigint id PK
        uuid trace_id UK
        text user_id FK
        text query
        text intent_type
        double intent_confidence
        text reasoning_mode
        double plan_confidence
        double runtime_load_ms
        double planning_ms
        double retrieval_ms
        double ranking_ms
        double fusion_ms
        double decision_ms
        double context_build_ms
        double verbalization_ms
        double total_ms
        uuid snapshot_id
        int snapshot_version
        uuid self_model_id
        int inference_count
        int reflection_count
        int behavior_object_count
        int evidence_count
        int retrieved_count
        int facts_generated
        int citations_created
        int duplicates_removed
        double aggregate_confidence
        int decision_input_facts
        int decision_output_facts
        int decision_conflicts
        int token_count
        int response_length
        bool success
        jsonb errors
        jsonb trace_data
        timestamp created_at
    }

    cognitive_metrics {
        bigint id PK
        text user_id FK
        text metric_name
        double metric_value
        jsonb metric_tags
        timestamp recorded_at
    }

    rl_policy {
        text context_key PK
        text action_id PK
        double q_value
        int n
        timestamp updated_at
    }

    chat_messages {
        bigint id PK
        text user_id FK
        text conversation_id
        text role
        text content
        uuid trace_id
        timestamp created_at
    }

    users {
        bigint id PK
        text username UK
        text email
        text password_hash
        text salt
        text display_name
        timestamp created_at
    }

    guardian_alerts {
        uuid alert_id PK
        text user_id FK
        text risk_level
        double risk_score
        jsonb risk_factors
        bool acknowledged
        timestamp created_at
    }
```

### Table Summary (23 Tables)

| Table | Rows Estimate | Purpose |
|---|---|---|
| `events` | Raw behavioral events from Chrome Extension | Source data for all downstream processing |
| `embeddings` | 384-dim pgvector embeddings for semantic search | Vector similarity + hybrid TSVECTOR search |
| `behavior_objects` | Topic-clustered behavioral patterns | Core knowledge representation |
| `evidence` | 5-dimension evidence items | Explainability backbone |
| `inferences` | Rule-driven behavioral inferences | High-level behavioral labels |
| `identities` | 9-sub-profile user identity (1 per user) | Canonical user model |
| `identity_snapshots` | Temporal identity snapshots | Evolution tracking |
| `self_models` | Self-awareness model (1 per user) | Explicit belief representation |
| `memories` | Unified memory store | Episodic, semantic, behavioral memory |
| `reflections` | Periodic system reflections | Pattern summarization |
| `goals` | User goals and milestones | Goal-oriented behavior tracking |
| `pipeline_traces` | Per-query pipeline execution traces | Full decision audit trail |
| `cognitive_metrics` | Named pipeline performance metrics | System monitoring |
| `rl_policy` | Contextual bandit Q-table | RL policy store |
| `chat_messages` | Conversation history | Chat continuity |
| `users` | Authentication | User accounts |
| `guardian_alerts` | Wellbeing risk alerts | Digital wellbeing |
| `personas` | V2 legacy persona snapshots | Backward compatibility |
| `actions_log` | V2 legacy RL action log | Backward compatibility |
| `runtime_metrics` | Character runtime build metrics | Performance monitoring |
| `error_events` | Unhandled exceptions + extension extraction failures | `GET /admin/errors` — replaces silent console-only failures |
| `organizations` | Org name/slug/owner | Seat/roster grouping — never joined against cognitive-data tables |
| `org_invites` | Invite codes with expiry/use-count | `POST /orgs/join` |

`users.org_id`/`users.org_role` and `users.research_opt_in` extend the existing `users` table rather than adding new per-user tables.

---

## Tech Stack

### Backend

| Category | Technology |
|---|---|
| **Runtime** | Python 3.11+ |
| **Framework** | FastAPI 0.115 with asyncpg |
| **Database** | PostgreSQL 16 + pgvector 0.7 |
| **Vector Embeddings** | sentence-transformers/all-MiniLM-L6-v2 (384-dim) |
| **LLM Providers** | OpenAI GPT-4o-mini, Anthropic Claude, Ollama (llama3.2) |
| **Content Extraction** | ScrapeGraphAI, Playwright |
| **Auth** | PBKDF2 + HMAC-signed tokens |
| **RL** | Custom online contextual bandit (ε-greedy Q-learning) |
| **Testing** | pytest, pytest-asyncio |

### Frontend (Dashboard)

| Category | Technology |
|---|---|
| **Framework** | React 18.2 + Vite 5 |
| **Routing** | react-router-dom 6.21 |
| **HTTP Client** | Axios 1.6 |
| **Charts** | Recharts 2.10 |
| **3D Visualization** | Three.js 0.185 + @react-three/fiber 8.18 + drei 9.122 |
| **Date Handling** | date-fns 3.0 |
| **CSS** | Custom design system (glassmorphism, dark theme) |

### Chrome Extension

| Component | Technology |
|---|---|
| **Manifest** | V3 — dual content scripts |
| **Instagram Content Script** | `content.js` — DOM observer, viewport detection, reel metadata extraction |
| **YouTube Content Script** | `youtube-content.js` — SPA URL detection, JSON/DOM dual-tier extraction, accumulated watch tracking |
| **Background** | `background.js` — Shared service worker (event batching, sync, backend status) |
| **Popup** | `popup.html/css/js` — Session/event/persona/connection status display |

```mermaid
flowchart TB
    subgraph "Platforms Tracked"
        IG[Instagram Reels<br/>content.js] -->|1s poll<br/>viewport detection| IG_VID[Identify Active Video]
        IG_VID -->|on change| IG_EXT[Extract Metadata<br/>username, caption, hashtags<br/>audio, likes, saves]
        IG_EXT --> BUF[Event Buffer]

        YT[YouTube Watch + Shorts<br/>youtube-content.js] -->|1s poll<br/>SPA URL detection| YT_TGT[Identify Target<br/>surface + videoId]
        YT_TGT -->|on change| YT_EXT[Extract Metadata<br/>Tier 1: JSON parse<br/>Tier 2: DOM selectors]
        YT_EXT --> YT_ENG[Extract Engagement<br/>likes, subscribe state]
        YT_ENG -->|watch time<br/>accumulation| BUF

        BUF -->|10 events OR 30s| SEND[chrome.runtime<br/>.sendMessage]
    end

    subgraph "Extension Background"
        SEND -->|SEND_EVENTS| BW[Background Worker<br/>background.js]
        BW -->|POST /ingest| API[FastAPI Backend<br/>:8000]
        BW -->|30s periodic sync| API
        BW -->|storage quota hit| API

        subgraph "Local Storage"
            LS[chrome.storage.local]
            LS -->|"sessions[]"| SI[Session Info]
            LS -->|userId| UID[User Identity]
        end

        BW --> LS
    end

    subgraph "Extension Popup"
        POP[popup.html/js] -->|GET_SESSION_INFO| BW
        POP -->|GET_BACKEND_STATUS| BW
        POP -->|SYNC_NOW| BW
        POP -->|CLEAR_DATA| BW
    end

    subgraph "Backend API"
        API -->|/health| HEALTH[Health Check]
        API -->|/cognitive/summary| SUMMARY[Cognitive Summary]
        API -->|/profile| PROFILE[Persona Profile]
        API -->|/ingest| INGEST[Event Ingestion]
    end
```

---

## Features

### Chrome Extension

| Feature | Description |
|---|---|
| **Instagram Reels Detection** | Automatic detection via DOM observer with viewport tracking (1s poll) |
| **YouTube Watch Detection** | SPA URL-based target identification for `/watch` pages |
| **YouTube Shorts Detection** | URL path matching for `/shorts/{id}` with scroll-based navigation |
| **Watch Time Tracking** | Per-video watch time (Instagram: 0.5s / YouTube: 2s min threshold) with scroll-based start/stop |
| **Metadata Extraction (Instagram)** | Username, caption, hashtags, audio info via DOM traversal |
| **Metadata Extraction (YouTube)** | Dual-tier: JSON parse from `ytInitialPlayerResponse` (Tier 1), DOM selectors fallback with hydration re-extraction (Tier 2) |
| **Engagement Signals** | Like/save/follow/subscribe state detection from DOM (both platforms) |
| **Content Popularity** | Like/comment/repost count extraction (best-effort, both platforms) |
| **YouTube Accumulated Watch** | Real playback detection (paused/seek/ads filtered) with per-tick accumulation |
| **SPA Navigation Handling** | `yt-navigate-finish` event listener for instant YouTube SPA target refresh |
| **Smart Batching** | Batch 10 events OR 30s interval, re-queue on failure (both scripts, shared background worker) |
| **CSP Bypass** | Background worker fetches bypass both Instagram's and YouTube's Content-Security-Policy |
| **Local Storage** | chrome.storage.local buffering with 1000-event limit |
| **Auto-Sync** | Periodic sync every 30s to backend |
| **Extension Popup** | Session/event/persona/backend connection status display |

### Cognitive Engine

| Feature | Description |
|---|---|
| **Behavior Gateway** | Multi-source event normalization with idempotency |
| **Knowledge Consolidation** | Topic clustering, creator aggregation, temporal trend detection |
| **5-Dimension Evidence** | Topical, creator, temporal, interaction, engagement evidence |
| **Rule-Based Inference** | 5 rule categories with confidence scoring |
| **9-Sub-Profile Identity** | Behavior, interest, creator, learning, attention, exploration, consistency, habit, motivation |
| **Temporal Snapshotting** | Automatic snapshots on configurable shift thresholds |
| **Self-Awareness Model** | Beliefs, strong beliefs, uncertain beliefs, uncertainty map |
| **Full Pipeline Tracing** | Every query records per-stage timing + intermediate state |
| **Global Search** | Unified search across 6 cognitive entity types |

### Dashboard

| Page | Route | Description |
|---|---|---|
| **Landing** | `/` | Hero with feature cards, demo seed, Instagram import CTA |
| **Dashboard** | `/dashboard` | Stats cards, radar chart, latency bars, topic pie, reflections |
| **Import** | `/import` | Live ingestion pulse, source-mix breakdown, demo seed, extraction-warning card |
| **Timeline** | `/timeline` | Chronological feed of every watch/like/save with real behavior-object and evidence linkage, replay modal |
| **Knowledge Graph** | `/graph` | Physics-driven 3D graph of topics and creators — node size, platform color, and edges all real |
| **Diary** | `/diary` | Deterministic weekly/monthly narrated summary, no LLM — same facts-to-prose pattern as the rest of the app |
| **Goals** | `/goals` | Set an intention, get an alignment score computed live against real behavior objects |
| **Organization** | `/org` | Create/join a workspace, generate invite codes, manage roster — never member cognitive data |
| **Identity** | `/identity` | 9 sub-profiles, evolution timeline, identity inspector, Identity Galaxy (3D) |
| **Memory** | `/memory` | Reflections, inferences, patterns with tab filters, Memory Tree (3D) |
| **Evidence** | `/evidence` | Evidence list, type distribution bar chart, detail drawer |
| **Behavior** | `/behavior` | Behavior objects by topic/creator, lifecycle state distribution, Filter Bubble Score |
| **Planning** | `/planning` | Pipeline planning breakdown, per-stage timing |
| **Decision** | `/decision` | Decision traces, tree visualization, explainability panel |
| **Pipeline** | `/pipeline` | Trace selector, per-stage timing bars, stage-highlighted view |
| **Trace** | `/trace/:id` | Single trace detail with full JSON inspector |
| **Analytics** | `/analytics` | Time-series metric trends, composition charts (explicit "not enough history" state instead of a fabricated flat line) |
| **Chat** | `/chat` | AI chat with streaming, explain button, follow-up chips |
| **Character** | `/character` | 3D orb, runtime state, memory references, RL policy |
| **Guardian** | `/guardian` | Wellbeing report, risk indicators, content alerts |
| **Insights** | `/insights` | Profile export, CSV download, campaign resonance |
| **Learning** | `/learning` | RL policy table, reward history per action type |
| **Settings** | `/settings` | Health check, data export, delete all data |
| **Guide** | `/guide` | Interactive feature tour with navigation |
| **Documentation** | `/documentation` | Full architecture docs with glossary |

### Explainability Features

```mermaid
flowchart TB
    subgraph "User Actions"
        CHAT[Chat Response] -->|Click Why?| EXP[ExplainabilityPanel]
        EVID[Evidence Item] -->|Click| DRAW[EvidenceDrawer]
        IDEN[Identity Card] -->|Click| INSP[IdentityInspector]
        DEC[Decision Item] -->|Click| TREE[DecisionTree]
        TR[Trace Item] -->|Click| TP[TracePage]
        STAGE[Pipeline Stage] -->|Click| PV[Pipeline Viewer]
    end

    subgraph "ExplainabilityPanel"
        EXP --> I[Identity Snapshot]
        EXP --> EV[Evidence Items]
        EXP --> M[Memories]
        EXP --> PL[Planner Data]
        EXP --> D[Decision Data]
        EXP --> CTX[Context Data]
        EXP --> L[LLM Data]
        EXP --> TRACE[Pipeline Trace]

        I -->|"GET /explain/{trace_id}"| API[Backend API]
        EV --> API
        M --> API
        PL --> API
        D --> API
        CTX --> API
        L --> API
        TRACE --> API
    end

    subgraph "EvidenceDrawer"
        DRAW --> ED[Evidence Detail]
        DRAW --> BO[Linked Behavior Objects]
        DRAW --> INF[Linked Inferences]
        DRAW --> MEM[Linked Memories]
        DRAW --> CE[Counter-Evidence]
        DRAW --> IDT[Identity Traits]

        ED -->|"GET /explain/evidence/{id}"| API
    end

    subgraph "IdentityInspector"
        INSP --> PROF[9 Sub-Profiles]
        INSP --> CONT[Contribution %]
        INSP --> SNAP[Snapshot History]
        INSP --> TOP[Topic Breakdown]

        PROF -->|"GET /explain/identity/{id}"| API
    end

    subgraph "DecisionTree"
        TREE --> Q[Query]
        TREE --> PLAN[Planner]
        TREE --> CAND[Candidates]
        TREE --> SEL[Selected]
        TREE --> CTX2[Context]
        TREE --> LLM2[LLM]
        TREE --> RESP[Response]
    end

    API --> DB[(PostgreSQL<br/>pipeline_traces<br/>evidence<br/>identities)]
```

| Feature | What It Shows |
|---|---|
| **ExplainabilityPanel** | Identity → Evidence → Memories → Planner → Decision → Context → LLM → Trace |
| **IdentityInspector** | 9 sub-profiles, contribution breakdown, linked behavior objects |
| **EvidenceDrawer** | Full evidence detail, linked BOs, inferences, memories, counter-evidence |
| **DecisionTree** | Query → Planner → Candidates → Selected → Context → LLM → Response |
| **Trace Page** | Per-stage timing breakdown, full trace JSON |
| **Pipeline Viewer** | Clickable stages with input/output/latency detail |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16 with pgvector extension
- Chrome Browser (Manifest V3)
- OpenAI API key (or Anthropic/Ollama)
- Instagram account (for Reels tracking)
- YouTube account (for Watch + Shorts tracking)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/AIMirror.git
cd AIMirror

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env        # Edit with your configuration
python setup_db.py          # Create database schema

# Dashboard setup
cd ../dashboard
npm install
cp .env.example ../.env     # Or create dashboard/.env

# Start services
cd ../backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal:
cd ../dashboard
npm run dev
```

### Configuration

```env
# backend/.env
DATABASE_URL=postgresql://user:pass@host:5432/dbname?sslmode=require
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=http://localhost:5173,chrome-extension://*
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LOG_LEVEL=INFO

# dashboard/.env
VITE_API_URL=http://localhost:8000
VITE_USER_ID=test_user_001
```

### Load Chrome Extension

Not published to the Chrome Web Store — load it unpacked:

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the `chrome-extension/` directory
5. The extension auto-detects Instagram Reels and YouTube (Watch + Shorts) — no manual switching needed

By default the extension points at the **deployed backend** (`https://aimirror-backend-cu00.onrender.com`), so it works immediately without any local setup. If you're running the backend locally instead (e.g. `npm run dev` / `uvicorn` on your own machine), open the extension popup → **⚙️ Connection settings** (or right-click the extension icon → Options) and point the Backend URL and Dashboard URL fields at `http://localhost:8000` / `http://localhost:5173`.

> **Note**: The extension uses two content scripts registered in the manifest:
> - `content.js` activates on `https://www.instagram.com/*` — Instagram Reels tracking
> - `youtube-content.js` activates on `https://www.youtube.com/*` — YouTube Watch + Shorts tracking
>
> Both scripts share the same background worker (`background.js`) for batching, sync, and CSP-bypassed backend communication. The backend/dashboard URLs are stored via `chrome.storage.local` (set through the Options page above) rather than hardcoded, so switching between local dev and the deployed instance never requires editing code.

### Verify Installation

| Service | URL | Expected |
|---|---|---|
| Backend Health | `http://localhost:8000/health` | `{"status": "healthy"}` |
| API Docs | `http://localhost:8000/docs` | Swagger UI |
| Dashboard | `http://localhost:5173` | Landing page |
| Extension Popup | Click extension icon | Session/event/persona display |

### Demo Data

Load 800 synthetic events through the full pipeline:
```bash
curl -X POST http://localhost:8000/seed
```

Or click "Load Demo Data" on the landing page.

### Getting Started by Persona

The landing page (`/`) has a dedicated entry point for each of these — the steps below are what those buttons actually do, if you'd rather drive it directly against the API.

**Individuals** — sign up, install the extension, browse normally:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "at-least-6-chars"}'
# -> {"token": "...", "user": {...}}
```
Load the Chrome extension (below), browse Instagram/YouTube for a bit, then open the dashboard — your identity, evidence, and reflections build up automatically as the pipeline processes what the extension captures. No import step required; `/seed` and "Load Demo Data" exist purely so you can see a full identity before you've generated one yourself.

**Organizations** — one account still equals one private twin; an org is a seat/roster layer on top, not a shared identity:
```bash
# 1. Register (or sign in), then create the org as its owner
curl -X POST http://localhost:8000/orgs -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"name": "Acme Research Labs"}'

# 2. Generate an invite code
curl -X POST http://localhost:8000/orgs/invites -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"max_uses": 5}'
# -> {"code": "CFbCib3ALf02", ...}

# 3. Each teammate registers their own account, then joins with the code
curl -X POST http://localhost:8000/orgs/join -H "Authorization: Bearer $MEMBER_TOKEN" \
  -H "Content-Type: application/json" -d '{"code": "CFbCib3ALf02"}'
```
Manage all of this from the **Organization** page in the dashboard instead — same endpoints, no curl required. See [Organizations](#organizations-1) below for exactly what an owner can and can't see about members.

**Researchers** — opt in from an existing account, then pull the bulk export:
```bash
curl -X POST http://localhost:8000/research/opt-in -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"opt_in": true}'

curl http://localhost:8000/research/export -H "Authorization: Bearer $TOKEN" > export.json
```
The export requires being signed in (any account — there's no separate approval gate) but only ever includes users who've explicitly opted in via Settings. See [Research Data Export](#research-data-export) below for the anonymization method and exact schema.

---

## User Guide

### User Journey Flow

```mermaid
flowchart TB
    START([Start]) --> CHOICE{What do you<br/>want to do?}

    CHOICE -->|"I want to track<br/>my own behavior"| SETUP[Install Chrome Extension]
    CHOICE -->|"I want to explore<br/>the system"| DEMO[Load Demo Data]

    SETUP --> EXT_LOAD[Load unpacked extension<br/>from chrome-extension/]
    EXT_LOAD --> VISIT[Visit instagram.com or<br/>youtube.com]
    VISIT --> TRACK[Extension auto-tracks<br/>in the background]
    TRACK --> DASH1[Open Dashboard<br/>at localhost:5173]

    DEMO --> CLICK[Click 'Load Demo Data'<br/>on Landing page]
    CLICK --> PIPELINE[6-stage pipeline animation<br/>runs automatically]
    PIPELINE --> DASH2[Auto-redirects to Dashboard]

    DASH1 --> EXPLORE[Explore your cognitive twin]
    DASH2 --> EXPLORE

    EXPLORE --> IDENT[View your Identity<br/>9 sub-profiles, evolution]
    EXPLORE --> EVID[Browse Evidence<br/>5 dimensions, linked objects]
    EXPLORE --> MEM[Explore Memories<br/>reflections, inferences]
    EXPLORE --> BEH[Review Behavior Objects<br/>topics, creators, importance]
    EXPLORE --> DEC[Inspect Decisions<br/>tree visualization, explainability]
    EXPLORE --> CHAT[Chat with your Twin<br/>ask about your patterns]

    CHAT -->|Click 'Why?'| EXPLAIN[ExplainabilityPanel<br/>full reasoning chain]
    CHAT -->|Click 'View Trace'| TRACE[Trace Page<br/>per-stage timing]

    EXPLORE -->|Cmd+K| SEARCH[Global Search<br/>6 cognitive entity types]
    EXPLORE --> ANALYTICS[Analytics Page<br/>time-series trends]
    EXPLORE --> GUARDIAN[Guardian Page<br/>wellbeing report, alerts]
```

### Quickstart Decision Tree

```mermaid
flowchart LR
    START([New User]) --> Q1{Have data?}

    Q1 -->|No| Q2{Want to track<br/>your own behavior?}
    Q1 -->|Yes, load demo| DEMO[POST /seed or<br/>click 'Load Demo Data']

    Q2 -->|Yes| INSTALL[Install Extension]
    Q2 -->|No| DEMO

    INSTALL --> VISIT[Browse Instagram/YouTube]
    VISIT --> AUTO[Extension collects data<br/>automatically]
    AUTO --> OPEN[Open Dashboard]

    DEMO --> OPEN
    OPEN --> LANDING{Seen landing page?}

    LANDING -->|First visit| HERO[Read about cognitive twin]
    LANDING -->|Returning| DASH[Go to Dashboard]

    HERO --> DASH
    DASH --> OVERVIEW[Overview: stats + charts]
    OVERVIEW --> DEEP[Deep dive into pages]

    DEEP --> IDENTITY[Identity: who you are]
    DEEP --> EVIDENCE[Evidence: what supports it]
    DEEP --> MEMORY[Memory: what you remember]
    DEEP --> BEHAVIOR[Behavior: what you watch]
    DEEP --> DECISION[Decision: how AI answers]
    DEEP --> CHAT[Chat: ask questions]

    CHAT --> EXPLAIN[Click 'Why?' → Full trace]
    CHAT --> FOLLOWUP[Follow-up suggestions]
```

### Dashboard Page Map

```mermaid
flowchart TB
    LANDING[Landing /] --> DASHBOARD[Dashboard /dashboard]

    DASHBOARD --> IMPORT[Import /import]
    DASHBOARD --> TIMELINE[Timeline /timeline]
    DASHBOARD --> GRAPH[Knowledge Graph /graph]
    DASHBOARD --> DIARY[Diary /diary]
    DASHBOARD --> GOALS[Goals /goals]
    DASHBOARD --> ORG[Organization /org]
    DASHBOARD --> IDENTITY[Identity /identity]
    DASHBOARD --> MEMORY[Memory /memory]
    DASHBOARD --> EVIDENCE[Evidence /evidence]
    DASHBOARD --> BEHAVIOR[Behavior /behavior]
    DASHBOARD --> PLANNING[Planning /planning]
    DASHBOARD --> DECISION[Decision /decision]
    DASHBOARD --> PIPELINE[Pipeline /pipeline]
    DASHBOARD --> ANALYTICS[Analytics /analytics]
    DASHBOARD --> CHAT[Chat /chat]
    DASHBOARD --> CHARACTER[Character /character]
    DASHBOARD --> GUARDIAN[Guardian /guardian]
    DASHBOARD --> INSIGHTS[Insights /insights]
    DASHBOARD --> LEARNING[Learning /learning]

    TIMELINE --> REPLAY[ReplayModal<br/>click any event]
    GRAPH --> GRAPH_NODE[Node detail panel<br/>click any topic/creator]
    GOALS --> GOAL_CARD[Live alignment scoring<br/>on every read]
    ORG --> ORG_INVITE[Invite code generator<br/>owner only]

    IDENTITY --> ID_INSPECTOR[IdentityInspector<br/>click any card]
    IDENTITY --> ID_EVOLUTION[IdentityEvolution<br/>timeline toggle]

    EVIDENCE --> EV_DRAWER[EvidenceDrawer<br/>click any item]

    DECISION --> DEC_TREE[DecisionTree<br/>click any trace]
    DECISION --> EXP_PANEL[ExplainabilityPanel<br/>click 'Why?']

    PIPELINE --> TRACE_PAGE[TracePage /trace/:id<br/>click any trace]
    PIPELINE --> PIPELINE_STAGE[PipelineStage<br/>click any stage]

    CHAT --> EXP_PANEL
    CHAT --> TRACE_PAGE

    SEARCH[Global Search ⌘K] --> IDENTITY
    SEARCH --> MEMORY
    SEARCH --> EVIDENCE
    SEARCH --> BEHAVIOR
    SEARCH --> DECISION
    SEARCH --> PIPELINE
```

### Navigation Highlights

| From | To | How |
|---|---|---|
| Landing | Dashboard | Click "Load Demo Data" or "Go to Dashboard" |
| Dashboard | Any page | Sidebar navigation (23 items) |
| Identity | IdentityInspector | Click any stat card or sub-profile |
| Identity | IdentityEvolution | Toggle "Evolution" tab |
| Evidence | EvidenceDrawer | Click any evidence row |
| Decision | DecisionTree | Click any decision trace |
| Decision | ExplainabilityPanel | Click "Why?" button on any trace |
| Chat | ExplainabilityPanel | Click "Why did the AI say this?" |
| Chat | TracePage | Click "View Trace" link |
| Pipeline | TracePage | Click any trace row |
| Any page | Global Search | `Cmd+K` / `Ctrl+K` |
| Settings | Data Export/Delete | Settings page buttons |

---

## API Reference

### Core Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | API root with version info |
| `GET` | `/health` | Health check (database, services) |

### Ingestion

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest` | Main event ingestion — accepts `platform` field (`instagram` | `youtube`) with content type inference (Reel → REEL, Watch → VIDEO, Shorts → REEL) |
| `POST` | `/extract` | URL-based content extraction via ScrapeGraphAI/Playwright |
| `POST` | `/seed` | Generate 800 demo events + run pipeline |

### Query

| Method | Path | Description |
|---|---|---|
| `POST` | `/query` | Cognitive pipeline query with full reasoning |
| `GET` | `/chat/history` | Get conversation history |
| `DELETE` | `/chat/history` | Clear conversation history |

### Profile

| Method | Path | Description |
|---|---|---|
| `GET` | `/profile` | Latest persona + alignment + RL suggestion |

### Identity & Reasoning

| Method | Path | Description |
|---|---|---|
| `GET` | `/identity/current` | Current identity with latest snapshot |
| `GET` | `/identity/snapshot` | Identity snapshot history |
| `GET` | `/identity/self-model` | Self-awareness model |
| `GET` | `/reasoning/evidence` | Evidence items (filterable by type) |
| `GET` | `/reasoning/inferences` | Rule-based inferences |
| `GET` | `/reasoning/reflections` | System reflections |
| `GET` | `/reasoning/behavior-objects` | Behavior objects |

### Explainability

| Method | Path | Description |
|---|---|---|
| `GET` | `/explain/{trace_id}` | Full reasoning chain for a query trace |
| `GET` | `/explain/evidence/{evidence_id}` | Evidence detail with all linked objects |
| `GET` | `/explain/identity/{identity_id}` | Identity breakdown with contribution analysis |
| `GET` | `/cognitive/summary` | Aggregate cognitive state summary |
| `GET` | `/cognitive/metrics` | Named pipeline performance metrics |

### Traces

| Method | Path | Description |
|---|---|---|
| `GET` | `/query/traces` | Pipeline trace list |
| `GET` | `/query/traces/{trace_id}` | Single trace detail |

### Search

| Method | Path | Description |
|---|---|---|
| `GET` | `/search` | Global search across 6 cognitive entity types |

### RL Layer

| Method | Path | Description |
|---|---|---|
| `GET` | `/rl/policy` | Learned Q-table |
| `GET` | `/rl/history` | Recent RL actions + rewards |
| `POST` | `/rl/feedback` | Explicit reward signal |

### Wellbeing (Guardian)

| Method | Path | Description |
|---|---|---|
| `GET` | `/guardian/report` | Full wellbeing report |
| `GET` | `/guardian/sessions` | Session timing patterns |
| `GET` | `/guardian/alerts` | Content alerts |
| `GET` | `/guardian/alert-log` | Persistent alert history |
| `POST` | `/guardian/alert-log/{alert_id}/acknowledge` | Acknowledge an alert |

### Character

| Method | Path | Description |
|---|---|---|
| `GET` | `/character/state` | Runtime character state |
| `GET` | `/character/activity` | Recent character turns |
| `GET` | `/character/learning-summary` | RL policy + last action |

### Insights & Privacy

| Method | Path | Description |
|---|---|---|
| `GET` | `/insights/profile` | Algorithmic Identity Profile (exportable) |
| `GET` | `/insights/export.csv` | CSV export of any cognitive table |
| `POST` | `/insights/campaign-resonance` | Score campaign text against identity |
| `GET` | `/privacy/export-all` | Export every data row for user |
| `POST` | `/privacy/delete-all-data` | Permanently delete all user data |

### Auth

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/register` | Register user (PBKDF2 password) |
| `POST` | `/auth/login` | Login, returns HMAC-signed token |
| `GET` | `/auth/me` | Current user from Bearer token |

Every other endpoint enforces `user_id` against the bearer token (see [Auth Enforcement](#auth-enforcement) below) — registering doesn't just get you a token, it's required to touch any `user_id` outside the public demo set.

### Admin

Local-debugging tooling — not per-user data endpoints, so `/admin/errors` has no auth. `/admin/reprocess` is destructive and always requires a token, even for public `user_id`s.

| Method | Path | Description |
|---|---|---|
| `GET` | `/admin/errors` | Recent unhandled exceptions and extension extraction failures |
| `POST` | `/admin/reprocess` | Rebuild a user's behavior_objects/evidence/inferences/identity from their real events (`dry_run` supported) |

### Organizations

Seat/roster grouping above individual accounts — every route requires a bearer token, no public-id exception. See [Organizations](#organizations-1) under Production Hardening for the privacy boundary this API deliberately stays inside.

| Method | Path | Description |
|---|---|---|
| `POST` | `/orgs` | Create an org (caller becomes owner) |
| `POST` | `/orgs/invites` | Generate an invite code (owner only) |
| `GET` | `/orgs/invites` | List this org's active invites (owner only) |
| `POST` | `/orgs/join` | Join an org via invite code |
| `GET` | `/orgs/me` | Current user's org, role, and member count |
| `GET` | `/orgs/members` | Roster — username, display name, role, join date only |
| `DELETE` | `/orgs/members/{username}` | Remove a member (owner only) |
| `POST` | `/orgs/leave` | Leave the org (owners blocked unless sole member) |

### Research

| Method | Path | Description |
|---|---|---|
| `GET` | `/research/status` | Current user's opt-in state |
| `POST` | `/research/opt-in` | Set opt-in state (`{opt_in: bool}`) |
| `GET` | `/research/export` | Bulk de-identified dataset across every opted-in user (any authenticated user) |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL connection string (required) |
| `PORT` | `8000` | HTTP server port |
| `HOST` | `0.0.0.0` | Bind address |
| `CORS_ORIGINS` | `http://localhost:5173,chrome-extension://*` | CORS allowlist |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model name |
| `LLM_PROVIDER` | — | `openai`, `anthropic`, or `ollama` |
| `LLM_MODEL` | — | Model name override |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama endpoint |
| `LLM_MODEL_OLLAMA` | `llama3.2` | Ollama model tag |
| `LLM_TIMEOUT` | `30` | LLM request timeout (seconds) |
| `LLM_MAX_RETRIES` | `0` | LLM SDK retries |
| `COGNITIVE_PIPELINE_TIMEOUT` | `120` | Pipeline timeout (seconds) |
| `RL_EPSILON` | `0.15` | RL exploration rate |
| `RL_ALPHA_MIN` | `0.05` | RL learning rate floor |
| `AUTH_SECRET` | `aimirror-dev-secret-change-me` | HMAC signing key |
| `AUTH_TOKEN_TTL` | `604800` (7 days) | Token expiry (seconds) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### Chrome Extension Config

Backend/dashboard URLs are set via the extension's **Options page** (`chrome-extension/options.html`, reachable from the popup's "⚙️ Connection settings" link) — stored in `chrome.storage.local`, not hardcoded, so no code edit or rebuild is needed to switch between local dev and the deployed instance:

| Setting | Storage key | Default | Description |
|---|---|---|---|
| Backend URL | `chrome.storage.local.backendUrl` | `https://aimirror-backend-cu00.onrender.com` | Where events are POSTed (`background.js`) |
| Dashboard URL | `chrome.storage.local.dashboardUrl` | `https://aimirror-dashboard.onrender.com` | Where the popup's "Dashboard" button opens |

Everything else stays as in-code constants (not exposed in the Options UI):

| Variable | Location | Default | Description |
|---|---|---|---|
| `SYNC_INTERVAL` | `background.js` | `30000` | Periodic sync interval (ms) |
| `MAX_STORAGE_EVENTS` | `background.js` | `1000` | Local storage event limit |
| `BATCH_SIZE` | `content.js` | `10` | Events per batch |
| `BATCH_INTERVAL` | `content.js` | `30000` | Max batch wait time (ms) |
| `USER_ID` | `content.js` | `test_user_001` | Default user ID (used for unauthenticated/demo tracking) |

---

## Architecture Decisions

### 1. Deterministic Over Stochastic

Every reasoning step in the cognitive pipeline follows explicit, deterministic rules. Inference generation, evidence collection, identity construction, and decision-making are all algorithmic — never statistical. The LLM is strictly a verbalizer: it formats pre-computed context into natural language but never reasons, infers, or decides. This ensures:

- **Reproducibility**: Same inputs always produce same outputs
- **Explainability**: Every output has a complete, traversable reasoning chain
- **Auditability**: Every decision can be traced to specific rules and evidence

### 2. Identity Over Persona

V3 replaces the V2 "Persona" archetype system with a rich 9-sub-profile Identity model. The persona is derived from the identity via an adapter for backward compatibility. This enables:

- Granular analysis of specific behavioral dimensions
- Detection of cross-dimension patterns (e.g., high exploration + low consistency)
- Finer-grained evolution tracking

### 3. Pipeline Tracing First

Every query pipeline execution records:
- Per-stage timing (planning, retrieval, ranking, fusion, decision, context build, verbalization)
- Intermediate state (retrieved items, evidence fused, decisions made)
- Full input/output snapshots

This enables the explainability system to reconstruct the complete reasoning chain for any response.

### 4. Online Learning via Contextual Bandit

```mermaid
flowchart TB
    subgraph "Ingestion Event"
        IE[New Events Ingested] --> FE[Feature Engineering]
        FE --> AL[Alignment Scoring]
    end

    subgraph "RL State"
        AL -->|4-dimension state| STATE[State Vector<br/>intentionality<br/>diversity<br/>depth<br/>wellbeing]
    end

    subgraph "Policy"
        STATE --> POLICY[ε-greedy Q-Learning]
        POLICY --> |explore| EXP[Random Action]
        POLICY --> |exploit| BEST[Best Q-Value Action]

        EXP --> ACTION[Selected Action]
        BEST --> ACTION
    end

    subgraph "Actions"
        ACTION --> A1[reduce_session]
        ACTION --> A2[diversify]
        ACTION --> A3[increase_engagement]
        ACTION --> A4[maintain_balance]
    end

    subgraph "Reward"
        ACTION --> DB[(rl_policy table)]
        DB --> NEXT[next ingest cycle]

        NEXT -->|alignment change| REWARD[Reward Signal]
        REWARD -->|Δ alignment| UPDATE[Q-Value Update]
        UPDATE --> POLICY
    end
```

The RL layer uses an online contextual bandit with ε-greedy Q-learning:
- **State**: 4 alignment dimensions (intentionality, diversity, depth, wellbeing)
- **Actions**: reduce_session, diversify, increase_engagement, maintain_balance
- **Reward**: Change in overall alignment score between ingests
- **Policy**: Stored in `rl_policy` table, persists across restarts

The RL loop closes naturally: each ingest rewards the previous action by how much alignment improved.

### 5. Multi-Provider LLM Abstraction

The `llm_provider.py` module abstracts across OpenAI, Anthropic, and Ollama via environment variable. Provider-agnostic callers must NOT send provider-specific model IDs. This enables:
- No vendor lock-in
- Offline-capable via Ollama
- Cost optimization (different providers for different workloads)

### 6. Idempotent Ingestion

Events are deduplicated by `(reel_id, session_id, timestamp)` to handle:
- Extension re-queueing on failed sends
- Background retry logic
- Concurrent batch arrivals

### 7. Snapshot-on-Shift

Identity snapshots are only persisted when the identity change crosses a configurable threshold. This prevents noise from generating meaningless snapshots while capturing genuine behavioral shifts.

### 8. Two-Schema Coexistence

The V1 SQLAlchemy schema (basic events/sessions) coexists with the V3 asyncpg schema (full cognitive pipeline). Both use the same PostgreSQL database but operate on different table sets. The V3 migration files are applied sequentially by `run_schema()`.

---

## Production Hardening

A dedicated pass making the system safe to run past a single testing session: authenticated data access, tests, real observability, and a process supervisor. All additive — the signed-out demo flow is unchanged.

### Auth Enforcement

Every endpoint that reads or writes `user_id`-scoped data now checks the bearer token (`app/api/deps.py`), not just the auth endpoints:

- **No token, public `user_id`** (`default`, `test_user_001`, `demo_*`) → allowed — today's signed-out demo behavior, unchanged.
- **No token, real `user_id`** → `401`.
- **Valid token matching `user_id`** → allowed.
- **Valid token, `user_id` is a public id** → allowed for *reads* (`enforce_user_match`) — a signed-in user can still browse the demo data.
- **Valid token, `user_id` belongs to someone else** → `403`.
- **Invalid/expired token** → `401`, even against a public id.
- **Mutating/destructive endpoints** (`enforce_write_match`: ingest, query, goals create/update/delete, privacy delete-all, admin reprocess) drop the public-id read bypass entirely — a token must match `user_id` exactly to write or delete anything, public id or not.

### Reprocess / Data Lifecycle

`POST /admin/reprocess` rebuilds a user's `behavior_objects`/`evidence`/`inferences`/`identities` from their real, already-ingested `events` — for when raw data and derived data have drifted (e.g. after a schema/linkage fix). Supports `dry_run` to preview row counts with no writes; idempotent on repeat calls.

### Observability

Unhandled exceptions are caught by the outermost request middleware (not `@app.exception_handler` — verified live that it doesn't reliably intercept exceptions raised deep in the stack) and recorded to an `error_events` table, queryable via `GET /admin/errors`. Every response still carries `X-Trace-Id` for correlating logs.

### Process Supervision

`scripts/start-all.ps1` runs the backend and dashboard under `scripts/supervise.ps1`, which restarts either on exit and keeps a real stdout/stderr log per attempt (never overwritten by the next restart) plus a `logs/supervisor.log` timeline of every start/exit/restart — replacing silent, unexplained process deaths with a real crash trace and automatic recovery.

```powershell
.\scripts\start-all.ps1     # supervised backend (8000) + dashboard (5173)
.\scripts\stop-all.ps1      # stops both, including child process trees
```

### Extension Failure Visibility

When a content script's DOM extraction fails (e.g. Instagram/YouTube changes their page structure and a selector goes stale), the event is dropped rather than recorded wrong — but the failure itself now flows through: content script → background worker → `POST /ingest` (`warnings` field) → `error_events` → a badge in the extension popup and a card on the Import page. Previously this was only a `console.log`, invisible unless devtools happened to be open at the exact moment.

### Organizations

`app/api/orgs.py` adds a seat/roster grouping layer above individual accounts — modeled on how Slack/Notion workspaces work, not on shared identity. This is a deliberate, load-bearing boundary, not an oversight:

- Every org query touches `users`/`organizations`/`org_invites` only. None of it ever joins against `behavior_objects`, `evidence`, `inferences`, `reflections`, `self_models`, or `identity_snapshots`.
- An org owner gets roster visibility (username, display name, role, join date) and seat management (invite, remove) — never a member's behavior, evidence, or identity data.
- Two roles: `owner` (the creator — can invite/remove members, single per org, no ownership transfer yet) and `member` (can view the roster, leave anytime).
- An owner can't leave while other members remain (avoids an orphaned org); leaving as the sole member deletes the org.

If a future feature ever needs to cross this line — an org-wide analytics rollup, say — it should be opt-in per member, the same way [research export](#research-data-export) is, not implied by org membership.

### Research Data Export

`app/api/research.py` + `app/services/research_export.py` — an opt-in, de-identified bulk export for behavioral-science research, gated behind `users.research_opt_in` (off by default; every user controls their own flag from Settings).

- **Anonymization**: `participant_id = HMAC-SHA256(RESEARCH_EXPORT_SALT, username)[:16]` — one-way, stable across export runs for the same user (so a longitudinal study can still join records for one participant), never reversible back to a username from the export alone. `RESEARCH_EXPORT_SALT` is a separate secret from `AUTH_SECRET` so the two can be rotated independently.
- **Fields**: allowlisted columns only, the same allowlist `insights_export.py`'s per-user CSV export already used — `behavior_objects` (topic, lifecycle_state, confidence/importance/stability scores, keywords), `evidence` (type, confidence, weight), `inferences` (type, label, confidence), `identity_snapshots` (version, overall_confidence, identity_completeness). No raw captions, no usernames, no emails.
- **Access**: `GET /research/export` requires being signed in (any account, no separate approval gate — self-serve like the rest of the product) so it isn't a fully anonymous scrape target, but participation is what actually gates the data, not the requester's identity.
- **Reversible opt-out, not retroactive**: turning `research_opt_in` back off removes a user from every future export immediately; it can't recall a dataset a researcher already downloaded.

### Tests

`backend/tests/` (pytest, gated behind a live `DATABASE_URL` via a session-scoped fixture — skips cleanly if unreachable) covers auth enforcement end-to-end, goals alignment scoring, the reprocess endpoint (including the write-vs-read auth bypass regression), the global exception handler, ingest warning handling, the full organizations lifecycle (create/invite/join/roster/remove/leave, including that the roster response never carries cognitive-data fields), and research export opt-in gating + de-identification.

```bash
cd backend
python -m pytest tests/ -v
```

---

## Development

### Project Structure

```
AIMirror/
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── main.py                   # FastAPI application entry point
│   │   ├── api/                      # API route handlers
│   │   │   ├── ingest.py            # POST /ingest, /extract
│   │   │   ├── query.py             # POST /query, /chat/history
│   │   │   ├── profile.py           # GET /profile
│   │   │   ├── explain.py           # Explainability, identity, reasoning, search
│   │   │   ├── seed.py              # POST /seed (demo data)
│   │   │   ├── rl.py                # RL policy/history/feedback
│   │   │   ├── auth_api.py          # Registration, login, me
│   │   │   ├── deps.py              # Per-request auth enforcement (resolve_user_id, enforce_write_match)
│   │   │   ├── admin.py             # GET /admin/errors, POST /admin/reprocess
│   │   │   ├── timeline.py          # GET /timeline
│   │   │   ├── graph.py             # GET /graph/knowledge
│   │   │   ├── diary.py             # GET /diary/story
│   │   │   └── goals.py             # Goals CRUD + live alignment scoring
│   │   ├── core/
│   │   │   └── error_tracking.py    # record_error() -> error_events table
│   │   ├── services/                 # Business logic services
│   │   │   ├── enrichment.py        # Topic/sentiment/intent extraction
│   │   │   ├── expansion.py         # Short caption → rich text
│   │   │   ├── embedding.py         # Sentence-transformers encoding
│   │   │   ├── vector_store.py      # pgvector operations
│   │   │   ├── feature_engineering.py
│   │   │   ├── persona.py           # V2 persona archetype engine
│   │   │   ├── persona_adapter.py   # V3 Identity → V2 Persona adapter
│   │   │   ├── rag.py               # Simple RAG fallback
│   │   │   ├── rl_layer.py          # Online contextual bandit
│   │   │   ├── auth.py              # PBKDF2 + HMAC auth
│   │   │   ├── wellbeing.py         # Guardian risk analysis
│   │   │   ├── chat_memory.py       # Conversation persistence
│   │   │   └── data_privacy.py      # GDPR export/delete
│   │   └── db/
│   │       ├── postgres.py          # asyncpg pool + schema runner
│   │       ├── schema.sql           # V1 core tables
│   │       └── migration_v*.sql     # V3-V12 incremental migrations
│   ├── cognitive_pipeline/          # Query-time pipeline
│   │   └── pipeline.py             # Pipeline orchestrator
│   ├── cognitive_planning/          # Planner subsystem
│   │   ├── planner_orchestrator.py
│   │   ├── intent_planner.py
│   │   ├── reasoning_planner.py
│   │   ├── retrieval_planner.py
│   │   └── response_planner.py
│   ├── core/                        # Core ingestion
│   │   ├── behavior_gateway.py     # Event normalization
│   │   └── event_normalizer.py
│   ├── engines/                     # Knowledge consolidation
│   │   └── knowledge_consolidation.py
│   ├── identity/                    # Identity engine
│   │   ├── identity_engine.py
│   │   ├── identity_evolution.py
│   │   ├── identity_snapshot.py
│   │   └── self_model.py
│   ├── reasoning/                   # Reasoning engines
│   │   ├── evidence_engine.py
│   │   ├── inference_engine.py
│   │   ├── reflection_engine.py
│   │   └── rules.py
│   ├── memory/                      # Memory module
│   ├── rag/                         # Retrieval pipeline
│   │   ├── retriever.py
│   │   ├── memory_ranker.py
│   │   ├── fusion.py
│   │   └── context_builder.py
│   ├── verbalizer/                  # LLM verbalization
│   │   ├── verbalizer.py
│   │   └── llm_provider.py
│   ├── character/                   # Character runtime
│   │   ├── runtime_builder.py
│   │   └── core.py
│   ├── providers/                   # Content extraction providers
│   ├── shared/                      # Shared contracts
│   │   └── contracts.py            # Pydantic models
│   ├── database.py                  # V1 SQLAlchemy models
│   ├── start.py                     # Dev server entry point
│   ├── setup_db.py                  # Schema initialization
│   ├── pytest.ini                   # asyncio_mode, db marker for tests needing a live DATABASE_URL
│   └── tests/                       # pytest suite — auth, goals scoring, reprocess, error handling, ingest warnings
│
├── dashboard/                       # React frontend
│   ├── src/
│   │   ├── pages/                  # 25 page components (lazy-loaded per route)
│   │   ├── components/             # UI components
│   │   │   ├── ui/                # Primitives (StatCard, GlassCard, Badge, AsyncState, etc.)
│   │   │   ├── layout/            # AppShell, Sidebar
│   │   │   └── ...                # Feature components
│   │   ├── api/
│   │   │   └── client.js          # Axios client + all API methods
│   │   ├── hooks/
│   │   │   └── useApi.js          # Generic data-fetching hook ({data, loading, error, refetch})
│   │   └── App.jsx                 # Root component
│   ├── index.html
│   ├── vite.config.js              # manualChunks: vendor-three / vendor-graph / vendor-charts / vendor-react
│   └── package.json
│
├── chrome-extension/               # Chrome extension
│   ├── manifest.json               # Manifest V3 — dual content scripts
│   ├── content.js                  # Instagram Reels DOM observer
│   ├── youtube-content.js          # YouTube Watch + Shorts tracker
│   ├── background.js               # Shared service worker
│   └── popup/                      # Extension popup UI
│       ├── popup.html
│       ├── popup.js
│       └── popup.css
│
├── scripts/                        # Process supervision (see Production Hardening)
│   ├── supervise.ps1                # Generic restart-on-exit wrapper with per-attempt crash logs
│   ├── start-all.ps1                # Launches backend + dashboard, each supervised
│   └── stop-all.ps1                 # Stops both, including child process trees
│
├── behavioral-engine/              # Legacy behavioral engine
├── refs/                           # Reference materials
└── docs/                           # Additional documentation
```

### Deployment Architecture

```mermaid
flowchart TB
    subgraph "Development Environment"
        DEV_EXT[Chrome Extension<br/>Loaded unpacked] -->|POST /ingest :8000| DEV_BE[FastAPI Backend<br/>uvicorn --reload]
        DEV_BE --> DEV_DB[(PostgreSQL 16<br/>+ pgvector)]
        DEV_DASH[Dashboard<br/>Vite Dev Server :5173] -->|GET/POST :8000| DEV_BE
    end

    subgraph "Production Environment"
        PROD_EXT[Chrome Extension<br/>Chrome Web Store] -->|POST /ingest| PROXY[Reverse Proxy<br/>nginx / Caddy]
        PROXY -->|backend.example.com| PROD_BE[FastAPI Backend<br/>gunicorn + uvicorn]
        PROD_BE --> PROD_DB[(Neon PostgreSQL<br/>+ pgvector)]
        PROD_DASH[Dashboard<br/>Vite Build → static] -->|CDN| WWW[Users]
        WWW -->|cloudflare.com| PROXY
    end

    subgraph "Database (Neon)"
        PROD_DB --> SCHEMA[Schema: V1-V10]
        PROD_DB --> VECTOR[pgvector extension]
        PROD_DB --> BACKUP[Point-in-time recovery]
    end

    subgraph "Observability"
        PROD_BE --> LOGS[Structured JSON Logs]
        PROD_BE --> METRICS[Cognitive Metrics Table]
        PROD_BE --> TRACES[Pipeline Traces Table]
    end

    subgraph "LLM Providers"
        PROD_BE -->|openai| GPT[OpenAI GPT-4o-mini]
        PROD_BE -->|anthropic| CLAUDE[Anthropic Claude]
        PROD_BE -->|ollama| OLLAMA[Ollama llama3.2<br/>self-hosted]
    end
```

### Commands

```bash
# Backend
cd backend
python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python setup_db.py
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
python -m pytest tests/

# Dashboard
cd dashboard
npm install
npm run dev        # http://localhost:5173
npm run build      # Production build → dist/
npm run preview    # Preview production build

# Extension
# Load unpacked from chrome-extension/ in chrome://extensions/
```

---

## Performance

| Metric | Target | Measured |
|---|---|---|
| Event ingestion (batch of 10) | < 500ms | ~320ms |
| V3 pipeline (800 events) | < 30s | ~18s |
| Query pipeline (cold) | < 3s | ~1.8s |
| Query pipeline (cached) | < 500ms | ~280ms |
| Vector similarity search | < 50ms | ~15ms |
| Embedding generation (single) | < 200ms | ~85ms |
| Dashboard load (initial) | < 2s | ~1.2s |
| Dashboard load (cached) | < 500ms | ~300ms |
| Extension memory | < 10MB | ~4MB |
| API throughput | 1000+ req/s | ~850 req/s (single instance) |

---

## Glossary

| Term | Definition |
|---|---|
| **Behavior Object** | A consolidated behavioral pattern clustered by topic, containing importance/confidence scores, keywords, creator list, temporal trends, and lifecycle state |
| **Behavior Gateway** | The normalization layer that converts raw events from any source (extension, API, seed) into a unified `BehaviorEvent` schema |
| **Content Type** | Enumeration distinguishing content format: `REEL` (short-form, e.g., Instagram Reels, YouTube Shorts) vs `VIDEO` (long-form, e.g., YouTube Watch) |
| **Cognitive Pipeline** | The event-time processing pipeline: Knowledge Consolidation → Evidence → Inference → Identity → Snapshot → Self-Model |
| **Deterministic Fallback** | Template-based response generator used when the LLM is unavailable, ensuring the system never hangs on LLM dependency |
| **Evidence** | A scored observation across 5 dimensions (topical, creator, temporal, interaction, engagement) that supports or contradicts identity traits |
| **ExplainabilityPanel** | Dashboard component that displays the full reasoning chain for any AI response: Identity → Evidence → Memories → Planner → Decision → Context → LLM |
| **Fused Fact** | A deduplicated, cited evidence fact produced by the FusionEngine during query processing |
| **Identity** | The canonical user model consisting of 9 sub-profiles: behavior, interest graph, creator graph, learning style, attention, exploration, consistency, habit, motivation |
| **Identity Snapshot** | A point-in-time capture of the identity, persisted only when behavioral change crosses a configurable threshold |
| **Inference** | A rule-driven behavioral label (e.g., "Strong interest in AI") with associated confidence, importance, and strength scores |
| **Knowledge Consolidation** | The engine that clusters raw events into hierarchically-organized behavior objects by topic, creator, and temporal pattern |
| **LLM Verbalizer** | The pipeline stage that formats pre-computed context into natural language — NEVER reasons, infers, or decides |
| **Memory** | A unified store of episodic, semantic, and behavioral records with importance scoring, embedding, and expiry |
| **Memory Ranker** | The query-pipeline stage that ranks retrieved items by their alignment to the user's identity and goals |
| **Persona** | Legacy V2 archetype model (Explorer, Focused Learner, etc.) — now derived from Identity via PersonaAdapter for backward compatibility |
| **Pipeline Trace** | A complete recording of a query pipeline execution, including per-stage timing, retrieved items, decisions made, and intermediate state |
| **Planner** | The query-pipeline stage that classifies intent, selects reasoning mode, and plans retrieval directives |
| **Query Pipeline** | The query-time processing pipeline: RuntimeBuilder → Planner → Retriever → MemoryRanker → FusionEngine → DecisionEngine → ContextBuilder → Verbalizer |
| **Reflection** | A periodic system-generated summary that synthesizes detected patterns, changes, and recommendations across the cognitive state |
| **RL Layer** | Online contextual bandit with ε-greedy Q-learning that learns personalized wellbeing interventions from alignment changes |
| **Self-Model** | A meta-cognitive model containing the system's explicit beliefs, strong beliefs, uncertain beliefs, and uncertainty domains about the user |
| **SPA Navigation** | Single-Page Application navigation — YouTube loads new video content via XHR without a full page reload, requiring URL-based target detection |
| **Tier 1 Extraction** | YouTube metadata extraction via JSON parsing of `ytInitialPlayerResponse` — fast and complete, but only available on hard page loads |
| **Tier 2 Extraction** | YouTube metadata extraction via DOM selectors — fallback method used when Tier 1 is absent or stale after SPA navigation |
| **V3 Pipeline** | The third-generation cognitive pipeline that replaced V2's Persona archetype system with the full Identity → Evidence → Inference → Reflection architecture |

## Troubleshooting

### Backend Won't Start

```
ModuleNotFoundError: No module named 'asyncpg'
```
→ Activate the virtual environment and install dependencies:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```
ModuleNotFoundError: No module named 'backend'
```
→ Run from the project root or set PYTHONPATH:
```powershell
cd C:\Users\cnnir\Documents\AI-Mirror
$env:PYTHONPATH = "C:\Users\cnnir\Documents\AI-Mirror"
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Database Connection

```
asyncpg.exceptions.InvalidAuthorizationSpecificationError
```
→ Verify `DATABASE_URL` in `backend/.env` is correct. For local SQLite fallback, the system uses `aimirror.db` automatically.

### Dashboard Shows No Data

| Cause | Solution |
|---|---|
| Backend not running | Start backend on port 8000 |
| Wrong API URL | Check `VITE_API_URL` in `dashboard/.env` |
| No user data | Load demo data via "Load Demo Data" button or `POST /seed` |
| CORS error | Check `CORS_ORIGINS` in backend `.env` includes `http://localhost:5173` |

### Extension Not Tracking

| Symptom | Cause | Solution |
|---|---|---|
| Popup shows "Offline" | Backend not running | Start backend, click Sync |
| No events recorded | Not on Instagram/YouTube | Navigate to instagram.com or youtube.com |
| "No active tracking" | Content script not injected | Reload the page, check console for `[AIMirror]` logs |
| Batch send fails | CSP or network error | Check background worker console, verify backend URL in `background.js` |

### LLM Not Responding

| Symptom | Cause | Solution |
|---|---|---|
| Chat returns template response | LLM provider not configured | Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in backend `.env` |
| Chat returns error | API key invalid or quota exhausted | Verify key has access to the configured model |
| Slow responses | LLM timeout too short | Increase `LLM_TIMEOUT` in backend `.env` |

### Performance Issues

| Issue | Possible Fix |
|---|---|
| Slow identity loading | Reduce `identity_snapshots` retention via `keep_count` in `ingest.py` |
| Slow query responses | Check `COGNITIVE_PIPELINE_TIMEOUT` setting |
| High memory usage | Reduce `MAX_STORAGE_EVENTS` in extension `background.js` |
| Dashboard slow | Enable `--reload` only in development; use `npm run build` for production |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <i>Built for transparency, powered by deterministic intelligence.</i>
</p>
