# AIMirror — Master Execution Plan

> Generated: 2026-07-20
> Architecture: **FROZEN** — no redesign, no renaming, no pipeline simplification
> Objective: Fully functional cognitive pipeline → production dashboard → IEEE demo

---

## Step 1 — Pipeline Stage Trace

### Stage 1: Instagram Events → Behavior Gateway

| Property | Value |
|----------|-------|
| File | `chrome-extension/content.js` + `backend/core/behavior_gateway.py` |
| Status | **Partial** — extension extracts DOM data correctly; gateway normalizes events |
| Input | Raw DOM data from Instagram Reels (username, caption, hashtags, watch_time) |
| Output | `List[BehaviorEvent]` (normalized contract) |
| Dependencies | `backend/core/event_normalizer.py`, `backend/shared/contracts.py` |
| Database | Writes to `events` table (backend V3 schema) |
| API | `POST /ingest` consumes gateway output |
| Frontend | Extension sends to backend; no frontend for this stage |
| Issues | 1. `ingest_from_dashboard()`, `ingest_from_mobile()`, `ingest_from_saved_reels()`, `ingest_from_browser_agent()` all return empty lists (not implemented) 2. `source_url` support recently added but enrichment runs after DB insert 3. `raw_metadata["original_payload"]` stores entire event — could be large |
| Fix | **Not urgent** — extension flow works. Other source handlers can be stubs until multi-platform support is needed. |

### Stage 2: Content Intelligence (Enrichment)

| Property | Value |
|----------|-------|
| File | `backend/app/services/enrichment.py`, `backend/app/services/expansion.py` |
| Status | **Partial** — keyword-based enrichment works; no ML/NLP integration |
| Input | Caption string + hashtags list |
| Output | Dict with topics, sentiment, intent |
| Dependencies | Keyword maps (hardcoded) |
| Database | None (stateless) |
| API | Called inline in `POST /ingest` |
| Frontend | None (backend internal) |
| Issues | 1. Keyword-based only — no semantic understanding 2. Limited topic coverage (8 categories) 3. Sentiment detection is naive (word counting) 4. Intent detection is simplistic 5. `expansion.py` is a stub (returns same text) |
| Fix | **Phase 2** — replace with embedding-based classification or LLM enrichment |

### Stage 3: Knowledge Consolidation

| Property | Value |
|----------|-------|
| File | `backend/engines/knowledge_consolidation.py` |
| Status | **Implemented but partially wired** — has real logic with Sentence-BERT clustering |
| Input | `List[BehaviorEvent]` |
| Output | `List[BehaviorCluster]` clustered events |
| Dependencies | `sentence-transformers`, `scikit-learn` (cosine_similarity), `numpy` |
| Database | Reads existing behavior objects; writes new/updated ones |
| API | Called by `V3Pipeline._consolidate_events()` in `POST /ingest` |
| Frontend | None (backend internal) |
| Issues | 1. `scikit-learn` dependency not in requirements.txt (only transitive via sentence-transformers) 2. 790-line file has no error recovery for embedding failures 3. `existing_clusters=[]` hardcoded — not loading from DB 4. Representative embedding falls back to `[0.0]*384` |
| Fix | **Phase 1** — add explicit sklearn dep, fix cluster loading |

### Stage 4: Behavior Objects

| Property | Value |
|----------|-------|
| File | `backend/reasoning/behavior_object.py` |
| Status | **Implemented** — full model with lifecycle, statistics, evolution history |
| Input | KnowledgeConsolidation clusters |
| Output | `BehaviorObject` instances |
| Dependencies | `backend/shared/contracts.py`, `pydantic` |
| Database | `behavior_objects` table (V3 schema) — upserted by orchestrator |
| API | Called by `V3Pipeline._consolidate_events()` |
| Frontend | Not directly consumed |
| Issues | 1. Lifecycle state machine is a simple Enum, not a state machine with transition rules 2. `representative_embedding` may be all zeros if cluster has no embedding 3. No validation that lifecycle transitions are valid |
| Fix | **Phase 2** — add lifecycle transition validation |

### Stage 5: Evidence Engine

| Property | Value |
|----------|-------|
| File | `backend/reasoning/evidence_engine.py` |
| Status | **Implemented but not fully integrated** — has real logic |
| Input | Events + behavior objects |
| Output | `List[Evidence]` with supporting/countervailing evidence, net confidence |
| Dependencies | `backend/shared/contracts.py` |
| Database | `evidence` table (V3 schema) |
| API | Called by `V3Pipeline._collect_evidence()` |
| Frontend | Not directly consumed |
| Issues | 1. 8 evidence types instead of paper's described 5 dimensions 2. Counter-evidence tracking exists in schema but logic is basic 3. `net_confidence` formula needs verification against paper's Eq. 4. Evidence collection only runs for topic + creator — not the 5 dimensions claimed |
| Fix | **Phase 1** — align with paper's 5 evidence dimensions |

### Stage 6: Inference Engine

| Property | Value |
|----------|-------|
| File | `backend/reasoning/inference_engine.py`, `backend/reasoning/rules.py` |
| Status | **Implemented** — rule-based inference generation |
| Input | Evidence + behavior objects within ReasoningContext |
| Output | `List[Inference]` |
| Dependencies | `backend/reasoning/reasoning_context.py`, `backend/reasoning/rules.py` |
| Database | `inferences` table (V3 schema) |
| API | Called by `V3Pipeline._generate_inferences()` |
| Frontend | Not directly consumed |
| Issues | 1. Rule engine is basic keyword matching 2. No confidence calibration for inferences 3. Temporal context is hardcoded (30-day window, "morning" time_of_day) |
| Fix | **Phase 2** — improve rule coverage, dynamic temporal context |

### Stage 7: Reflection Engine

| Property | Value |
|----------|-------|
| File | **Missing** — paper describes it but no file named `reflection_engine.py` exists |
| Status | **Missing** — ReflectionEngine is not found in any active code path |
| Input | Should accept behavior objects, evidence, inferences |
| Output | Should produce periodic behavioral journals |
| Dependencies | N/A |
| Database | `reflections` table (V3 schema) exists but is never written to |
| API | Not called |
| Frontend | Not consumed |
| Issues | 1. **CRITICAL GAP** — entire engine is missing 2. `reflections` table in DB is dead — never written, never read |
| Fix | **Phase 1** — implement minimal reflection (aggregate insights → generate summary) |

### Stage 8: Identity Engine

| Property | Value |
|----------|-------|
| File | `backend/identity/identity_engine.py` |
| Status | **Implemented** — constructs Identity with 9 sub-profiles |
| Input | Behavior objects + inferences + evidence |
| Output | `Identity` with 9 sub-profiles (BehaviorProfile, InterestGraph, CreatorGraph, etc.) |
| Dependencies | `backend/reasoning/behavior_object.py`, `backend/reasoning/evidence_engine.py` |
| Database | `identities` table (V3 schema) — upserted |
| API | Called by `V3Pipeline._construct_identity()` |
| Frontend | Not directly consumed |
| Issues | 1. 9 sub-profiles are constructed but many get default/zero values 2. No normalization across sub-profiles 3. Identity version monotonically increments but no semantic meaning |
| Fix | **Phase 2** — improve sub-profile construction quality |

### Stage 9: Identity Snapshot

| Property | Value |
|----------|-------|
| File | `backend/identity/identity_snapshot.py` |
| Status | **Implemented** — snapshot creation logic exists |
| Input | `Identity` |
| Output | `IdentitySnapshot` (frozen, versioned) |
| Dependencies | `backend/identity/identity_engine.py` |
| Database | `identity_snapshots` table (V3 schema) |
| API | Called by `V3Pipeline._construct_identity()` and `SnapshotManager.create_snapshot()` |
| Frontend | Not directly consumed |
| Issues | 1. Threshold check from paper Eq. 2 (`||I_{t+1} - I_t||_2 > τ_identity`) is NOT implemented — snapshots are created unconditionally 2. Rollback feature claimed in paper is NOT implemented 3. Snapshot metadata lacks meaningful diff data |
| Fix | **Phase 1** — add threshold-based snapshot creation; **Phase 2** — add rollback |

### Stage 10: Self Model

| Property | Value |
|----------|-------|
| File | `backend/identity/self_model.py` |
| Status | **Implemented** — belief tracking with uncertainty |
| Input | Identity snapshot + inferences + evidence |
| Output | `SelfModel` with beliefs, uncertainty map |
| Dependencies | `backend/identity/identity_snapshot.py` |
| Database | `self_models` table (V3 schema) |
| API | Called by `V3Pipeline._construct_identity()` |
| Frontend | Not directly consumed |
| Issues | 1. Uncertainty quantification is ad-hoc (no formal uncertainty estimation) 2. Belief strength/confidence not calibrated 3. No temporal decay of beliefs |
| Fix | **Phase 2** — improve uncertainty modeling |

### Stage 11: Character Runtime

| Property | Value |
|----------|-------|
| File | `backend/character/runtime_builder.py`, `backend/character/character_state.py`, `backend/character/character_core.py` |
| Status | **Partial** — files exist with real logic but NOT wired into any query path |
| Input | User ID, identity snapshot |
| Output | `RuntimeBuildResult` with CharacterCore + CharacterState |
| Dependencies | `backend/identity/*`, `backend/memory/*`, `backend/shared/contracts.py` |
| Database | Reads from identities, snapshots, memories tables |
| API | Called by `CognitivePipeline.process_query()` (which is NOT wired to the query endpoint) |
| Frontend | Not consumed |
| Issues | 1. **NOT WIRED** — query endpoint (`backend/app/api/query.py`) uses simple RAG, not RuntimeBuilder 2. `_load_memory_ids()` loads string IDs from DB but never instantiates memory module classes 3. Thread executor workaround for async/sync mismatch |
| Fix | **Phase 1** — wire RuntimeBuilder into the query endpoint |

### Stage 12: Cognitive Planning (4 planners)

| Property | Value |
|----------|-------|
| File | `backend/cognitive_planning/intent_planner.py`, `retrieval_planner.py`, `reasoning_planner.py`, `response_planner.py`, `planner_orchestrator.py` |
| Status | **Implemented but not wired** — 8 files with real logic, imports succeed |
| Input | User query + CharacterPlan context |
| Output | `CharacterPlan` with intent, retrieval, reasoning, response sub-plans |
| Dependencies | `backend/shared/contracts.py` |
| Database | None (stateless) |
| API | Called by `CognitivePipeline.process_query()` only — NOT by the live `/query` endpoint |
| Frontend | Not consumed |
| Issues | 1. **NOT WIRED** — `/query` endpoint bypasses all planners 2. Intent planner tested (0.82 F1 in paper) but only in playground 3. Reasoning planner uses template-based mode selection |
| Fix | **Phase 1** — wire planners into `/query` endpoint |

### Stage 13: Character RAG / Retrieval

| Property | Value |
|----------|-------|
| File | `backend/rag/retriever.py`, `backend/rag/memory_ranker.py`, `backend/rag/fusion.py` |
| Status | **Partial** — retriever and ranker have real logic; fusion exists |
| Input | RetrievalPlan + context |
| Output | `RetrievalResult` → `RankedObject[]` → `FusedEvidence` |
| Dependencies | `backend/rag/citation_manager.py` |
| Database | Reads from behavior_objects, evidence, inferences, identities, snapshots, self_models, goals, reflections (via `_load_retrieval_context()`) |
| API | Called by `CognitivePipeline.process_query()` only |
| Frontend | Not consumed |
| Issues | 1. **NOT WIRED** to live query endpoint 2. `data_sources.py` is DEAD CODE — bypassed by `_load_retrieval_context()` 3. Citation manager exists but citations not exposed to frontend 4. Fusion engine has basic duplicate detection but no semantic dedup |
| Fix | **Phase 1** — wire into query endpoint; **Phase 2** — improve fusion |

### Stage 14: Decision Engine

| Property | Value |
|----------|-------|
| File | `backend/cognitive_pipeline/decision_engine.py` |
| Status | **Implemented** — 574 lines of production-quality deterministic scoring |
| Input | FusedEvidence + CharacterPlan + RetrievalResult + RankedObjects |
| Output | `FinalContext` with selected facts, scores, conflicts |
| Dependencies | `backend/rag/fusion.py`, `backend/cognitive_planning/planner_models.py` |
| Database | Reads identity snapshot + self model from context (passed in) |
| API | Called by `CognitivePipeline.process_query()` only |
| Frontend | Not consumed |
| Issues | 1. **NOT WIRED** to live query endpoint 2. Conflict detection is word-overlap-based (naive) 3. Diversity enforcement is per-topic only 4. Empty plan not handled gracefully 5. Weights are hardcoded in dataclass (but match paper) |
| Fix | **Phase 1** — wire into query endpoint; **Phase 2** — improve conflict detection |

### Stage 15: Context Builder

| Property | Value |
|----------|-------|
| File | `backend/rag/context_builder.py` |
| Status | **Implemented** — builds CharacterContext for verbalization |
| Input | FinalContext + plan + retrieval result |
| Output | `CharacterContext` |
| Dependencies | `backend/shared/contracts.py` |
| Database | None (stateless assembly) |
| API | Called by `CognitivePipeline.process_query()` only |
| Frontend | Not consumed |
| Issues | 1. **NOT WIRED** to live query endpoint 2. Context ID generated but not stored/cached |
| Fix | **Phase 1** — wire into query endpoint |

### Stage 16: LLM Verbalizer

| Property | Value |
|----------|-------|
| File | `backend/verbalizer/verbalizer.py` |
| Status | **Partial** — well-architected prompt templates but NO real LLM call |
| Input | `CharacterContext` + `CharacterPlan` |
| Output | `VerbalizerResponse` with content and token count |
| Dependencies | None (fallback is string concatenation) |
| Database | None |
| API | Called by `CognitivePipeline.process_query()` only |
| Frontend | Returns response text to chat UI |
| Issues | 1. **FALLBACK ONLY** — singleton instance has no `llm_call`, so always uses `_fallback_verbalization()` (simple string builder) 2. Prompt architecture is solid but never sent to any LLM 3. No token counting or context window management 4. No structured output parsing (if LLM called, response could be malformed) |
| Fix | **Phase 1** — implement real LLM provider (OpenAI/Anthropic) and wire into verbalizer |

### Stage 17: Dashboard (Frontend)

| Property | Value |
|----------|-------|
| Files | `dashboard/src/pages/*.jsx`, `dashboard/src/api/client.js` |
| Status | **Broken** — 2 of 5 pages completely non-functional; fake data in 1 page |
| Input | Backend API responses |
| Output | React UI |
| Dependencies | Axios → backend API |
| Database | Indirect via API |
| Frontend | All 5 pages |
| Issues | 1. `Sessions.jsx` and `SessionDetail.jsx` call API methods that DON'T EXIST in `client.js` — **BROKEN** 2. `Overview.jsx` uses FAKE chart data (synthetic creators, derived engagement) 3. Wrong default API port (`8000` vs `3000`) 4. No auth (hardcoded `user_123`) 5. No TypeScript 6. No error boundaries 7. No loading skeletons |
| Fix | **Phase 1** — add missing API methods, fix port, remove fake data |

---

## Step 2 — Complete Data Flow

```
Instagram Reels (DOM)
    │ content.js extracts metadata
    ▼
Chrome Extension (batched POST /ingest)
    │ background.js relays to backend
    ▼
┌──────────────────────────────────────────────────────────────┐
│                   BACKEND (backend/app/main.py)               │
│                                                              │
│  POST /ingest                                                │
│    │                                                        │
│    ▼                                                        │
│  BehaviorGateway.normalize                           [WORKS] │
│    │                                                        │
│    ▼                                                        │
│  Store events in DB (events table)                  [WORKS] │
│    │                                                        │
│    ├──► URL enrichment via ProviderManager          [NEW]    │
│    │      (if source_url provided)                           │
│    │                                                        │
│    ▼                                                        │
│  Keyword enrichment + expansion                      [WORKS] │
│    │                                                        │
│    ▼                                                        │
│  Generate embeddings + store vector                  [WORKS] │
│    │                                                        │
│    ▼                                                        │
│  V3Pipeline.run()                                            │
│    │  ┌────────────────────────────────────────────────────┐ │
│    ├──┤ KnowledgeConsolidation → BehaviorObjects   [PARTIAL]│ │
│    ├──┤ Evidence Collection                        [PARTIAL]│ │
│    ├──┤ Inference Generation                       [PARTIAL]│ │
│    ├──┤ Identity Construction                     [WIRED]*  │ │
│    ├──┤ Identity Snapshot                        [WIRED]*   │ │
│    └──┤ Self Model                               [WIRED]*   │ │
│       └────────────────────────────────────────────────────┘ │
│    │  * Wired in orchestrator, but sub-profile quality low   │
│    ▼                                                        │
│  PersonaAdapter (backward compat)                    [WORKS] │
│    │                                                        │
│    ▼                                                        │
│  Feature engineering + RL alignment                  [WORKS] │
│    │                                                        │
│    ▼                                                        │
│  Return IngestResponse                               [WORKS] │
│                                                              │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│                                                              │
│  POST /query                                    [BROKEN/PLAN]│
│    │  Currently uses: rag.py + persona.py                    │
│    │  Should use: CognitivePipeline (not wired)              │
│    ▼                                                        │
│  Current: RAG template response (no identity, no planning)   │
│  Target:  RuntimeBuilder → Planner → RAG → Fusion →         │
│           DecisionEngine → ContextBuilder → Verbalizer       │
│                                                              │
│  GET /profile                                        [WORKS] │
│    │  Returns persona + behavioral data                      │
│    ▼                                                        │
│  Persona data (from DB, post-ingest)                         │
│                                                              │
│  POST /extract                                        [NEW]  │
│    │  URL content extraction via ProviderManager             │
│    ▼                                                        │
│  ScrapeGraphAI / Playwright → NormalizedContent              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│                   DASHBOARD (React + Vite)                    │
│                                                              │
│  GET  / → Overview.jsx                          [PARTIAL]   │
│    │   Stat cards: real data from /profile                  │
│    │   Charts: FAKE synthetic data                          │
│    │                                                        │
│  GET  /sessions → Sessions.jsx                   [BROKEN]   │
│    │   API method api.getSessions() DOES NOT EXIST          │
│    │                                                        │
│  GET  /sessions/:id → SessionDetail.jsx         [BROKEN]   │
│    │   API methods api.getSession()/getSessionEvents() MISS │
│    │                                                        │
│  GET  /analytics → Analytics.jsx                  [WORKS]   │
│    │   Real data from /profile endpoint                     │
│    │                                                        │
│  GET  /chat → Chat.jsx                            [WORKS]   │
│    │   Real data from /chat/history + POST /chat            │
│    │                                                        │
└──────────────────────────────────────────────────────────────┘

BROKEN LINKS (highlighted):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❶ CognitivePipeline / DecisionEngine / Planner → NOT WIRED to /query
❷ Sessions.jsx → api.getSessions() missing from client.js
❸ SessionDetail.jsx → api.getSession() / getSessionEvents() missing
❹ Overview.jsx charts → FAKE DATA (not backed by any endpoint)
❻ ProviderManager → only ScrapeGraph is real; Playwright returns empty; Firecrawl/BrowserUse are stubs
❼ Verbalizer → no real LLM connection (always uses fallback)
❽ Reflection Engine → entire engine missing from codebase
❾ Dashboard API port → defaults to 8000 but backend runs on 3000
❿ Hardcoded user_123 → no auth across any layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 3 — Backend Feature Matrix

| Feature | Implemented | Working | Tested | Connected | Frontend Used | Production Ready |
|---------|:-----------:|:-------:|:------:|:---------:|:-------------:|:----------------:|
| Event ingestion (POST /ingest) | ✅ | ✅ | ✅ | ✅ | ✅ (via extension) | ⚠️ (no auth) |
| Behavior Gateway normalization | ✅ | ✅ | ❌ | ✅ | ❌ | ⚠️ |
| Keyword enrichment | ✅ | ✅ | ❌ | ✅ | ❌ | ⚠️ |
| Content expansion | ⚠️ (stub) | ❌ | ❌ | ✅ | ❌ | ❌ |
| Embedding generation | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Vector storage (pgvector) | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| Knowledge consolidation | ✅ | ⚠️ (partial) | ❌ | ✅ | ❌ | ❌ |
| Behavior objects | ✅ | ⚠️ (partial) | ❌ | ✅ | ❌ | ❌ |
| Evidence engine | ✅ | ⚠️ (partial) | ❌ | ✅ | ❌ | ❌ |
| Inference engine | ✅ | ⚠️ (partial) | ❌ | ✅ | ❌ | ❌ |
| Reflection engine | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Identity engine | ✅ | ⚠️ (partial) | ❌ | ✅ | ❌ | ❌ |
| Identity snapshot | ✅ | ⚠️ | ❌ | ✅ | ❌ | ❌ |
| Self model | ✅ | ⚠️ | ❌ | ✅ | ❌ | ❌ |
| Identity → Persona adapter | ✅ | ✅ | ❌ | ✅ | ✅ | ⚠️ |
| Feature engineering | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| RL alignment | ✅ | ✅ | ❌ | ✅ | ❌ | ⚠️ |
| Cognitive planning (4 planners) | ✅ | ⚠️ | ✅ (isolated) | ❌ | ❌ | ❌ |
| Runtime builder | ✅ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| Retriever / Memory ranker | ✅ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| Fusion engine | ✅ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| Decision engine | ✅ | ✅ | ✅ (isolated) | ❌ | ❌ | ❌ |
| Context builder | ✅ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| LLM verbalizer | ⚠️ (fallback only) | ⚠️ | ❌ | ❌ | ✅ (chat) | ❌ |
| Content extraction (ScrapeGraph) | ✅ (NEW) | ⚠️ (needs install) | ❌ | ✅ | ❌ | ⚠️ |
| Chat history | ✅ | ✅ | ❌ | ✅ | ✅ | ⚠️ |
| Session management (legacy backend) | ✅ | ✅ | ❌ | ✅ | ⚠️ (broken) | ⚠️ |
| Analytics aggregation | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| Health check | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| Evaluation scripts (playground) | ✅ | ✅ | N/A | ❌ | ❌ | ❌ |

---

## Step 4 — Frontend Feature Matrix

### Pages

| Page | Route | Status | Backend Endpoint | Real Data | Loading State | Error State | Empty State |
|------|-------|--------|-----------------|:---------:|:-------------:|:-----------:|:-----------:|
| Overview | `/` | **Partial (fake charts)** | `GET /profile` | ✅ (stats) / ❌ (charts) | ✅ (text) | ✅ | ✅ |
| Sessions | `/sessions` | **BROKEN** | `GET ???` (missing method) | ❌ | ✅ | ✅ | ✅ |
| SessionDetail | `/sessions/:id` | **BROKEN** | `GET ???` (2 missing methods) | ❌ | ✅ | ✅ | ✅ |
| Analytics | `/analytics` | **Working** | `GET /profile` | ✅ | ✅ | ✅ | ✅ |
| Chat | `/chat` | **Working** | `GET /chat/history`, `POST /chat` | ✅ | ✅ (typing) | ⚠️ (inline message) | ✅ |

### Missing API Methods in `client.js`

| Method Called By | Missing From client.js | Impact |
|-----------------|----------------------|--------|
| `api.getSessions()` | Sessions.jsx | Page always shows error |
| `api.deleteSession(id)` | Sessions.jsx | Delete button never works |
| `api.getSession(id)` | SessionDetail.jsx | Page always shows error |
| `api.getSessionEvents(id)` | SessionDetail.jsx | Page always shows error |

### Data Quality Across Widgets

| Page | Widget | Data Status | Issue |
|------|--------|:-----------:|-------|
| Overview | Total Sessions stat | ✅ Real | — |
| Overview | Total Reels stat | ✅ Real | — |
| Overview | Attention Score stat | ✅ Real | — |
| Overview | Engagement Score stat | ✅ Real | — |
| Overview | Avg Watch Time stat | ✅ Real | — |
| Overview | Archetype stat | ✅ Real | Falls back to "Unknown" |
| Overview | Top Creators bar chart | ❌ **FAKE** | 5 synthetic creators created in code |
| Overview | Engagement pie chart | ⚠️ **Derived** | Computed from engagement_score * total_reels |
| Sessions | All widgets | ❌ **BROKEN** | API method doesn't exist |
| SessionDetail | All widgets | ❌ **BROKEN** | API methods don't exist |
| Analytics | All metrics | ✅ Real | Working correctly |
| Analytics | Most Watched Creators table | ✅ Real | Empty state if none |
| Chat | Messages list | ✅ Real | Working correctly |
| Chat | Send message | ✅ Real | Working correctly |

### UI Polish Level

| Component | Polish Level | Notes |
|-----------|:-----------:|-------|
| Navbar | Medium | Basic links, no active state highlighting |
| Footer | Low | Static text |
| Stat cards | Medium | Animated entrance, gradient colors |
| Charts | Medium | Recharts with custom tooltips |
| Tables | Low | Basic HTML tables, no sorting/filtering |
| Chat | High | Typing indicator, scroll-to-bottom, timezone support |
| Theme | Medium | Dark glassmorphism with particle background |
| Mobile | Low | Some breakpoints but not truly responsive |

---

## Step 5 — Database Mapping

### All Tables

```
BEHAVIORAL-ENGINE SCHEMA (V1/V2)          BACKEND SCHEMA (V3)
═══════════════════════════════           ═══════════════════════
behavioral_memory      ──→  (shared DB)  events (V3)
chat_history           ──→  (shared DB)  embeddings (V3)
user_profiles                             personas
sessions (BE_v1)                          behavior_objects
actions_log (BE_v1)  ←── CONFLICT ──→   actions_log (V3, different columns)
embeddings (BE_v2)   ←── CONFLICT ──→   embeddings (V3, different columns)
metadata_store                            evidence
behavioral_trends                         inferences
user_goals                                identities
performance_metrics                       identity_snapshots
                                          self_models
                                          memories
                                          reflections
                                          goals (V3)
                                          runtime_metrics

SQLALCHEMY SCHEMA (legacy backend/main.py)
═══════════════════════════════
sessions (SQLAlchemy)
events (SQLAlchemy)
```

### Entity Relationship Summary

```
events ──→ embeddings (FK: source_event_id)
  │
  ├──→ behavior_objects (logical: user_id)
  │       └──→ evidence (logical: behavior_object references)
  │               └──→ inferences (logical: evidence references)
  │                       └──→ identities (logical: inference references)
  │                               ├──→ identity_snapshots (logical: identity_id)
  │                               └──→ self_models (logical: snapshot_id)
  │
  ├──→ personas (logical: user_id)
  └──→ actions_log (logical: user_id)
```

### Key Database Issues

| Issue | Severity | Details |
|-------|----------|---------|
| Shared DB between two backends | **Critical** | Both `backend/` and `behavioral-engine/` point to same Neon URL. `actions_log` and `embeddings` table names collide with different column definitions. |
| Only 1 FK constraint | Low | `embeddings.source_event_id → events.id`. All other relationships are logical. |
| No migrations | **High** | Tables created ad-hoc via schema.sql and migration_v3.sql. No Alembic. |
| Dead tables (never written) | **High** | `metadata_store`, `behavioral_trends`, `user_goals`, `performance_metrics`, `user_profiles`, `embeddings` (BE_v2), `memories`, `reflections` (written but never read), `runtime_metrics` |
| Missing indexes | Medium | No GIN indexes on JSONB fields that are queried |
| pgvector index not tuned | Low | IVFFLAT with lists=100 — may need tuning for production scale |

---

## Step 6 — API Mapping

### Endpoint Inventory

| Method | Path | Backend Source | Service Layer | DB Table | Frontend Consumer | Status |
|--------|------|---------------|--------------|----------|:-----------------:|:------:|
| POST | `/api/events` | `backend/main.py` | SQLAlchemy ORM | sessions, events | ❌ (legacy) | Working |
| GET | `/api/sessions` | `backend/main.py` | SQLAlchemy ORM | sessions | `Sessions.jsx` (BROKEN) | Working API, broken frontend |
| GET | `/api/sessions/{id}` | `backend/main.py` | SQLAlchemy ORM | sessions | `SessionDetail.jsx` (BROKEN) | Working API, broken frontend |
| GET | `/api/sessions/{id}/events` | `backend/main.py` | SQLAlchemy ORM | events | `SessionDetail.jsx` (BROKEN) | Working API, broken frontend |
| GET | `/api/events` | `backend/main.py` | SQLAlchemy ORM | events | ❌ | Working |
| GET | `/api/analytics` | `backend/main.py` | SQLAlchemy ORM | sessions, events | `Analytics.jsx` | Working |
| DELETE | `/api/sessions/{id}` | `backend/main.py` | SQLAlchemy ORM | sessions, events | `Sessions.jsx` (BROKEN) | Working API, broken frontend |
| POST | `/ingest` | `backend/app/api/ingest.py` | V3Pipeline + V2 services | events, embeddings, personas, behavior_objects, evidence, inferences, identities, snapshots, self_models, actions_log | Chrome extension | **Working** |
| POST | `/query` | `backend/app/api/query.py` | rag.py (simple RAG) | embeddings, personas | `Chat.jsx` | **Working (simple)** |
| GET | `/profile` | `backend/app/api/profile.py` | persona_svc | personas | `Overview.jsx`, `Analytics.jsx` | **Working** |
| POST | `/extract` | `backend/app/api/ingest.py` | ProviderManager → ScrapeGraphAI | None | ❌ | **NEW** |
| GET | `/health` | Both backends | DB health check | None | ❌ | **Working** |
| POST | `/chat` | `behavioral-engine/app/api/chat.py` | rag_engine + virtual_character | behavioral_memory | `Chat.jsx` | **Working** |
| GET | `/chat/history/{id}` | `behavioral-engine/app/api/chat.py` | chat_memory (JSON file) | chat_data/conversations.json | `Chat.jsx` | **Working (file-based)** |
| DELETE | `/chat/history` | `behavioral-engine/app/api/chat.py` | chat_memory | chat_data/conversations.json | ❌ | Working |
| POST | `/action` | `behavioral-engine/app/api/action.py` | action_engine | behavioral_memory, actions_log | ❌ (client.js has it) | Working |
| POST | `/feedback` | `behavioral-engine/app/api/feedback.py` | rl_logger | actions_log | ❌ (client.js has it) | Working |
| POST | `/alignment` | `behavioral-engine/app/api/alignment.py` | alignment (JSON file) | alignment_data/goals.json | ❌ (client.js has it) | Working |
| GET | `/alignment/{id}` | `behavioral-engine/app/api/alignment.py` | alignment | alignment_data/goals.json | ❌ | Working |

### API Issues

| Issue | Severity | Details |
|-------|----------|---------|
| Two backends, same port intent | **High** | Both want port 8000. `backend/main.py` uses 3000, `backend/app/main.py` uses 8000, `behavioral-engine/app/main.py` uses 8000. Extension hardcodes 8000. |
| `client.js` port wrong | **High** | Defaults to 8000 but backend is on 3000 |
| Frontend calls non-existent API methods | **High** | `getSessions`, `getSession`, `getSessionEvents`, `deleteSession` — these methods don't exist in client.js |
| Cognitive pipeline not exposed | **High** | Planning, decision engine, verbalizer — all exist in code but no API endpoint calls them |
| No auth on any endpoint | **High** | Any endpoint is open to anyone |
| Behavioral-engine + backend share ingest responsibilities | **Medium** | Both have `/ingest` endpoints but write to different tables |
| JSON-file-based storage | **Medium** | Chat history and alignment goals stored in JSON files, not database |

---

## Step 7 — Dashboard Mapping

### Screen Inventory

```
OVERVIEW (/)
├── Page Header: "Overview" + subtitle
├── Stats Grid (6 AnimatedStatCards):
│   ├── Total Sessions       [REAL — from /profile]
│   ├── Total Reels          [REAL — from /profile]
│   ├── Attention Score      [REAL — from /profile]
│   ├── Engagement Score     [REAL — from /profile]
│   ├── Avg Watch Time       [REAL — from /profile]
│   └── Your Archetype       [REAL — from /profile, fallback "Unknown"]
├── Bar Chart: Top 5 Most Watched Creators  [FAKE — synthetic data]
└── Pie Chart: Engagement Distribution      [DERIVED — computed from score]

SESSIONS (/sessions)
├── Page Header: "Sessions" + count
└── Sessions Table:
    ├── Session ID (truncated)     [BROKEN — API method missing]
    ├── Start Time                 [BROKEN]
    ├── Duration                   [BROKEN]
    ├── Total Events badge         [BROKEN]
    ├── Total Watch Time           [BROKEN]
    └── Delete button per row      [BROKEN]

SESSION DETAIL (/sessions/:id)
├── Page Header: "Session Details"
├── Stats Grid (6 inline stats):
│   ├── Start Time            [BROKEN]
│   ├── Duration              [BROKEN]
│   ├── Total Reels           [BROKEN]
│   ├── Watch Time            [BROKEN]
│   ├── Like Ratio            [BROKEN]
│   └── Avg Watch Time        [BROKEN]
├── Line Chart: Watch Time Timeline  [BROKEN]
└── Events Table (8 columns)         [BROKEN]

ANALYTICS (/analytics)
├── Page Header: "Analytics" + subtitle
├── Card: Overall Statistics
│   ├── Total Sessions        [REAL]
│   ├── Total Reels Watched   [REAL]
│   ├── Total Watch Time      [REAL]
│   └── Total Replays         [REAL]
├── Card: Time Metrics
│   ├── Avg Watch Time per Reel     [REAL]
│   ├── Avg Watch Time per Session  [REAL]
│   └── Reels per Session           [REAL]
├── Card: Engagement Metrics
│   ├── Like Ratio + detail    [REAL]
│   └── Avg Scroll Speed       [REAL]
└── Table: Most Watched Creators (rank, username, views, watch time) [REAL]

CHAT (/chat)
├── Page Header: "AI Mirror Chat" + TimezoneSelector
├── Chat Messages:
│   ├── Message bubbles (user/assistant)  [REAL]
│   └── Typing indicator                   [REAL — UI only]
├── Chat Input (text + send button)        [REAL]
├── Clear Chat button                      [REAL — clears local state only]
└── Empty state: "Start a Conversation"    [REAL]
```

### Widget Status Summary

| Widget Count | Status |
|:-----------:|--------|
| 28 | Total widgets across all pages |
| 16 | **Real data** (from backend API) |
| 2 | **Fake/synthetic data** (Overview charts) |
| 1 | **Derived data** (Engagement pie chart) |
| 9 | **Broken** (Sessions + SessionDetail pages) |
| 0 | Loading skeletons (text "Loading..." only) |

---

## Step 8 — Technical Debt (Safe to Delete/Consolidate)

### Dead Code (Not Imported or Used Anywhere)

| File | Lines | Reason to Delete |
|------|-------|-----------------|
| `backend/engines/trend_detection.py` | 700+ | Not imported anywhere — orphaned |
| `backend/cognitive_pipeline/data_sources.py` | 227 | Bypassed by pipeline's `_load_retrieval_context()` — dead code |
| `backend/memory/episodic_memory.py` | ~150 | Not imported, in-memory only, no DB integration |
| `backend/memory/semantic_memory.py` | ~150 | Same — dead class |
| `backend/memory/behavioral_memory.py` | ~150 | Same — dead class |
| `backend/memory/goal_memory.py` | ~100 | Same — dead class |
| `backend/memory/reflection_memory.py` | ~100 | Same — dead class |
| `backend/memory/base_memory.py` | ~200 | Only used by the above dead classes |
| `backend/memory/__init__.py` | ~10 | Only exports dead classes |
| `backend/database.py` (root) | ~60 | SQLAlchemy ORM for legacy backend — not used by V3 pipeline |
| `backend/models.py` | ~60 | Pydantic models for legacy backend |
| `backend/app/services/expansion.py` | ~50 | Stub — returns text unchanged |
| `backend/providers/firecrawl_provider.py` | 87 | Raises NotImplementedError |
| `backend/providers/browseruse_provider.py` | 87 | Raises NotImplementedError |

### Duplicate Code (Same Purpose, Different Locations)

| What | Location A | Location B | Conflict |
|------|-----------|-----------|----------|
| Event ingestion | `backend/app/api/ingest.py` | `behavioral-engine/app/api/ingest.py` | Different backends, different tables |
| RAG query | `backend/app/services/rag.py` | `behavioral-engine/app/services/rag_engine.py` + `rag_engine_postgres.py` | 3 implementations |
| Embedding service | `backend/app/services/embedding.py` | `behavioral-engine/app/services/embedding.py` | Duplicate |
| Vector store | `backend/app/services/vector_store.py` | `behavioral-engine/app/services/vector_store.py` + `vector_store_postgres.py` | 3 implementations |
| Persona service | `backend/app/services/persona.py` | `behavioral-engine/app/services/persona.py` | Duplicate |
| Feature engineering | `backend/app/services/feature_engineering.py` | `behavioral-engine/app/services/feature_engineering.py` | Duplicate |
| RL layer | `backend/app/services/rl_layer.py` | `behavioral-engine/app/services/rl_logger.py`, `rl_bandit.py`, `reward.py` | Multiple implementations |
| Database connection | `backend/app/db/postgres.py` | `behavioral-engine/app/database.py` | Two connection pools to same DB |
| Three backends | `backend/main.py` (port 3000) | `backend/app/main.py` (port 8000) | `behavioral-engine/app/main.py` (port 8000) |

### Stale/Misleading Documentation

| File | Issue |
|------|-------|
| `README.md` | Claims ChromaDB, port 8000, features that don't exist |
| `SETUP.md` | Points to legacy backend setup, wrong port |
| `ARCHITECTURE_REFACTOR_COMPLETE.md` | Claims completion that isn't real |
| `docs/SPRINT_1_SUMMARY.md` through `SPRINT_3_FINAL_SUMMARY.md` | Aspirational — describe future state as done |
| `docs/PHASE_4_PROGRESS.md` | Claims 10% complete of unimplemented features |
| `docs/PRODUCTION_GUIDE.md` | 770 lines referencing non-existent endpoints |
| `docs/MIGRATION_GUIDE.md` | Migration scripts never executed |

### Old/Unused Frontend Code

| File | Issue |
|------|-------|
| `dashboard/src/pages/Sessions.jsx` | Calls non-existent API methods — dead page |
| `dashboard/src/pages/SessionDetail.jsx` | Same — dead page |
| `chrome-extension/popup/popup.html/css/js` | Works but references `http://localhost:5173` |

---

## Step 9 — Prioritized Implementation Tasks

### P0 — Pipeline Must Work

| ID | Title | Files | Deps | Effort | Expected Result |
|----|-------|-------|------|--------|-----------------|
| P0-01 | Add missing API methods to client.js | `dashboard/src/api/client.js` | None | 1h | Sessions + SessionDetail pages work |
| P0-02 | Fix default API port in client.js | `dashboard/src/api/client.js` | None | 10m | Dashboard connects on correct port |
| P0-03 | Wire cognitive pipeline into /query endpoint | `backend/app/api/query.py`, `backend/cognitive_pipeline/pipeline.py` | P0-04, P0-05 | 4h | /query uses RuntimeBuilder + Planner + Retriever + DecisionEngine + Verbalizer |
| P0-04 | Implement real LLM provider for verbalizer | `backend/verbalizer/verbalizer.py` | OpenAI/Anthropic SDK | 3h | Verbalizer sends prompts to real LLM instead of fallback |
| P0-05 | Remove fake chart data from Overview | `dashboard/src/pages/Overview.jsx` | P0-01 | 1h | Charts show real data or empty state |
| P0-06 | Add scikit-learn to requirements.txt | `backend/requirements.txt` | None | 5m | Knowledge consolidation dependency explicit |
| P0-07 | Implement Reflection Engine (minimal) | New: `backend/reasoning/reflection_engine.py` | Evidence, Inference engines | 3h | Reflections table populated on ingest |

### P1 — Core Quality

| ID | Title | Files | Deps | Effort |
|----|-------|-------|------|--------|
| P1-01 | Implement identity snapshot threshold (Eq. 2) | `backend/identity/identity_evolution.py` | P0-03 | 2h |
| P1-02 | Align evidence engine with paper's 5 dimensions | `backend/reasoning/evidence_engine.py` | None | 3h |
| P1-03 | Add pipeline timeout to cognitive pipeline | `backend/cognitive_pipeline/pipeline.py` | None | 30m |
| P1-04 | Add loading skeletons to dashboard | `dashboard/src/pages/*.jsx` | None | 2h |
| P1-05 | Add error boundaries to dashboard | `dashboard/src/App.jsx` (new ErrorBoundary) | None | 1h |
| P1-06 | Remove fake data from Overview charts | `dashboard/src/pages/Overview.jsx` | P0-01 | 30m |
| P1-07 | Fix hardcoded user_123 → dynamic user | `dashboard/src/api/client.js`, `dashboard/src/pages/Chat.jsx` | Auth system | 4h |
| P1-08 | Add missing DB indexes (JSONB GIN) | `backend/app/db/migration_v3.sql` | None | 1h |

### P2 — Dashboard Quality

| ID | Title | Files | Deps | Effort |
|----|-------|-------|------|--------|
| P2-01 | Identity visualization (sub-profiles) | `dashboard/src/pages/Identity.jsx` (new) | P0-03 | 4h |
| P2-02 | Evidence explorer UI | `dashboard/src/pages/Evidence.jsx` (new) | P0-03 | 4h |
| P2-03 | Decision trace visualization | `dashboard/src/components/DecisionTrace.jsx` (new) | P0-03 | 3h |
| P2-04 | Memory explorer | `dashboard/src/pages/Memory.jsx` (new) | P0-03 | 4h |
| P2-05 | Behavior timeline visualization | `dashboard/src/components/BehaviorTimeline.jsx` (new) | P0-03 | 3h |
| P2-06 | Pipeline visualizer | `dashboard/src/components/PipelineVisualizer.jsx` (new) | None (frontend-only) | 3h |

### P3 — Explainability

| ID | Title | Files | Deps | Effort |
|----|-------|-------|------|--------|
| P3-01 | "Show reasoning" toggle on chat responses | `dashboard/src/pages/Chat.jsx` | P0-03, P0-04 | 3h |
| P3-02 | Evidence provenance display | `dashboard/src/components/EvidenceProvenance.jsx` (new) | P0-03 | 3h |
| P3-03 | Decision score breakdown UI | `dashboard/src/components/DecisionScores.jsx` (new) | P0-03 | 2h |
| P3-04 | Identity snapshot diff viewer | `dashboard/src/components/SnapshotDiff.jsx` (new) | Identity versioning | 4h |

### P4 — Production

| ID | Title | Files | Deps | Effort |
|----|-------|-------|------|--------|
| P4-01 | API key authentication | All endpoints | None | 4h |
| P4-02 | Docker + docker-compose | New root files | None | 3h |
| P4-03 | CI/CD (GitHub Actions) | New `.github/workflows/` | P4-02 | 3h |
| P4-04 | Alembic migrations | New `backend/alembic/` | None | 3h |
| P4-05 | Rate limiting | `backend/app/main.py` | None | 1h |
| P4-06 | Structured logging (structlog) | All backends | None | 2h |
| P4-07 | Sentry error tracking | All backends + frontend | None | 1h |

### P5 — IEEE Demo Polish

| ID | Title | Files | Deps | Effort |
|----|-------|-------|------|--------|
| P5-01 | Interactive architecture diagram | `dashboard/src/pages/Architecture.jsx` (new) | None | 4h |
| P5-02 | Pipeline animation | `dashboard/src/components/PipelineAnimation.jsx` (new) | None | 3h |
| P5-03 | Demo mode with sample data | `dashboard/src/utils/demoData.js` (new) | None | 3h |
| P5-04 | Metrics dashboard (latency, counts) | `dashboard/src/pages/Metrics.jsx` (new) | P0-03 | 3h |
| P5-05 | Evaluation results page | `dashboard/src/pages/Evaluation.jsx` (new) | Playground scripts | 4h |

---

## Step 10 — Phase Breakdown

### Phase 1: Functional Pipeline (Effort: ~3-4 days)

**Goal**: Every feature works correctly. No fake data. No broken pages.

**Tasks**:
- P0-01: Add missing API methods to client.js
- P0-02: Fix default API port
- P0-03: Wire cognitive pipeline into /query endpoint
- P0-04: Implement real LLM verbalizer
- P0-05: Remove fake chart data from Overview
- P0-06: Add explicit dependencies
- P0-07: Implement minimal Reflection Engine
- P1-01: Identity snapshot threshold
- P1-02: Align evidence with paper dimensions
- P1-03: Pipeline timeout

**Completion Criteria**:
- `/ingest` → full V3 pipeline completes (events → behavior objects → evidence → inferences → identity → snapshot → self model)
- `/query` → uses CognitivePipeline (RuntimeBuilder → Planner → Retriever → Ranker → Fusion → DecisionEngine → ContextBuilder → Verbalizer)
- Dashboard: All 5 pages show real data, no broken pages, no fake charts
- Chat sends prompts to real LLM and displays responses
- Reflection Engine produces at least a basic summary per ingest batch

---

### Phase 2: Backend Completion (Effort: ~2-3 days)

**Goal**: Deepen pipeline quality. Add missing mechanics.

**Tasks**:
- P1-04 through P1-08 (loading skeletons, error boundaries, dynamic user, DB indexes)
- Improve Behavior Object lifecycle transitions
- Improve sub-profile construction quality in Identity Engine
- Improve uncertainty quantification in Self Model
- Wire TrendDetection into pipeline (or delete)
- Consolidate duplicate services (choose backend/ or behavioral-engine/)

**Completion Criteria**:
- Identity sub-profiles have meaningful values (not zeros)
- Behavior Objects follow lifecycle rules
- Self Model beliefs have calibrated uncertainty
- Only one active backend code path (behavioral-engine deprecated or aligned)
- Dashboard has loading skeletons + error boundaries

---

### Phase 3: Premium Dashboard (Effort: ~3-4 days)

**Goal**: Dashboard becomes a Cognitive Intelligence Dashboard.

**Tasks**:
- P2-01 through P2-06 (Identity viz, Evidence explorer, Decision trace, Memory explorer, Behavior timeline, Pipeline visualizer)
- Convert to TypeScript
- Add responsive design
- Add real-time updates (WebSocket polling)

**Completion Criteria**:
- Dashboard feels like exploring an AI's cognition
- Identity card shows 9 sub-profiles with confidence
- Evidence explorer shows supporting/countervailing evidence
- Decision trace shows what was selected and why
- Pipeline visualizer shows live stage-by-stage execution

---

### Phase 4: Explainability (Effort: ~2-3 days)

**Goal**: Every response answers Why, How, Evidence, Confidence.

**Tasks**:
- P3-01 through P3-04 (Show reasoning, Evidence provenance, Decision scores, Snapshot diff)
- Add "Explain this response" button to every chat message
- Show planner's intent classification, retrieval directives, reasoning mode
- Show decision engine scores per fact

**Completion Criteria**:
- Every chat response has a collapsible "Show reasoning" section
- Evidence provenance shows exactly which events support each claim
- Decision scores show the 7-dimension breakdown
- Identity version shown per response

---

### Phase 5: Production Features (Effort: ~3-4 days)

**Goal**: Deployable, secure, monitored.

**Tasks**:
- P4-01 through P4-07 (Auth, Docker, CI/CD, Alembic, Rate limiting, Logging, Sentry)
- Fix CORS to specific origins
- Add request validation
- Add health check with detailed status

**Completion Criteria**:
- Docker images build successfully
- CI pipeline runs on every push
- API authenticated with keys
- Database migrations managed by Alembic
- Error tracking in Sentry
- Structured JSON logging

---

### Phase 6: IEEE Demo Polish (Effort: ~2-3 days)

**Goal**: Conference-quality demo that impresses reviewers.

**Tasks**:
- P5-01 through P5-05 (Architecture diagram, Pipeline animation, Demo mode, Metrics dashboard, Evaluation results)
- Seed demo dataset with sample user behaviors
- Add "demo mode" toggle that loads curated data
- Create presentation-ready screenshots

**Completion Criteria**:
- Interactive architecture diagram matches paper's Figure 1
- Live pipeline animation shows data flowing through stages
- Metrics dashboard shows latency, throughput, pipeline traces
- Demo mode loads with 3 sample users showing diverse behaviors
- Evaluation results page shows 0.82 F1, latency table, determinism proof

---

## Step 11 — Execution Order

The execution order is designed to minimize merge conflicts by targeting independent modules first, then integrating.

### Batch 1 (Parallel — No Dependencies)
```
Order  │ Task    │ Files
───────┼─────────┼────────────────────────────────
  1    │ P0-02   │ dashboard/src/api/client.js (fix port)
  1    │ P0-06   │ backend/requirements.txt
  1    │ P1-03   │ backend/cognitive_pipeline/pipeline.py
  1    │ P1-04   │ dashboard/src/pages/*.jsx (loading skeletons)
  1    │ P1-05   │ dashboard/src/App.jsx (ErrorBoundary)
```

### Batch 2 (Requires Batch 1)
```
Order  │ Task    │ Files
───────┼─────────┼────────────────────────────────
  2    │ P0-01   │ dashboard/src/api/client.js (add missing methods)
  2    │ P0-05   │ dashboard/src/pages/Overview.jsx (remove fake data)
  2    │ P0-07   │ backend/reasoning/reflection_engine.py (new)
  2    │ P1-02   │ backend/reasoning/evidence_engine.py
  2    │ P1-08   │ backend/app/db/migration_v3.sql (indexes)
```

### Batch 3 (Cognitive Pipeline Integration)
```
Order  │ Task    │ Files
───────┼─────────┼────────────────────────────────
  3    │ P0-04   │ backend/verbalizer/verbalizer.py (real LLM)
  3    │ P0-03   │ backend/app/api/query.py (wire cognitive pipeline)
  3    │ P1-01   │ backend/identity/identity_evolution.py (threshold)
  3    │ P1-07   │ dashboard/src/api/client.js + Chat.jsx (dynamic user)
```

### Batch 4 (Dashboard Deepening)
```
Order  │ Task    │ Files
───────┼─────────┼────────────────────────────────
  4    │ P2-01   │ dashboard/src/pages/Identity.jsx (new)
  4    │ P2-02   │ dashboard/src/pages/Evidence.jsx (new)
  4    │ P2-04   │ dashboard/src/pages/Memory.jsx (new)
```

### Batch 5 (Visualization)
```
Order  │ Task    │ Files
───────┼─────────┼────────────────────────────────
  5    │ P2-03   │ dashboard/src/components/DecisionTrace.jsx (new)
  5    │ P2-05   │ dashboard/src/components/BehaviorTimeline.jsx (new)
  5    │ P2-06   │ dashboard/src/components/PipelineVisualizer.jsx (new)
```

### Batch 6 (Explainability)
```
Order  │ Task    │ Files
───────┼─────────┼────────────────────────────────
  6    │ P3-01   │ dashboard/src/pages/Chat.jsx (show reasoning)
  6    │ P3-02   │ dashboard/src/components/EvidenceProvenance.jsx (new)
  6    │ P3-03   │ dashboard/src/components/DecisionScores.jsx (new)
  6    │ P3-04   │ dashboard/src/components/SnapshotDiff.jsx (new)
```

### Batch 7 (Production)
```
Order  │ Task    │ Files
───────┼─────────┼────────────────────────────────
  7    │ P4-01   │ All endpoints (auth middleware)
  7    │ P4-02   │ Dockerfile + docker-compose.yml
  7    │ P4-03   │ .github/workflows/ci.yml
  7    │ P4-04   │ backend/alembic/ (new)
  7    │ P4-05   │ backend/app/main.py (rate limiting)
  7    │ P4-06   │ All backends (structured logging)
  7    │ P4-07   │ Sentry.init() in all entry points
```

### Batch 8 (IEEE Polish)
```
Order  │ Task    │ Files
───────┼─────────┼────────────────────────────────
  8    │ P5-01   │ dashboard/src/pages/Architecture.jsx (new)
  8    │ P5-02   │ dashboard/src/components/PipelineAnimation.jsx (new)
  8    │ P5-03   │ dashboard/src/utils/demoData.js (new)
  8    │ P5-04   │ dashboard/src/pages/Metrics.jsx (new)
  8    │ P5-05   │ dashboard/src/pages/Evaluation.jsx (new)
```

---

## Step 12 — Risk Analysis

### High-Risk Changes

| Risk | Task | Why | Mitigation |
|------|------|-----|-----------|
| Wiring cognitive pipeline into /query (P0-03) | Replaces working simple RAG with complex 8-stage pipeline | Can break chat entirely if any stage fails | Add fallback: if CognitivePipeline fails, fall back to simple RAG. Ship with feature flag. |
| Real LLM verbalizer (P0-04) | Adds new dependency on external API | Cost, latency, API failures, rate limits | Implement with retry + fallback to template. Make provider configurable. |
| Shared DB collision | Both backends write to same DB with conflicting schemas | Data corruption on `actions_log` and `embeddings` tables | Drop or rename behavioral-engine's duplicate tables. Add migration script. |

### Low-Risk Changes (Safe to Do Anytime)

| Task | Reason |
|------|--------|
| P0-01 (add API methods to client.js) | Pure addition, no deletion |
| P0-02 (fix default port) | Single constant change |
| P0-05 (remove fake chart data) | Removing code is safe |
| P0-06 (add dependency) | Pure addition |
| P1-03 (pipeline timeout) | Adding guardrail, not changing logic |
| P1-04/05 (loading skeletons, error boundaries) | UI wrapping, no logic change |
| P2-01 through P2-06 (new dashboard pages) | New pages don't affect existing ones |

### Breaking Changes

| Task | Breaks | Migration |
|------|--------|-----------|
| P0-03 (wire cognitive pipeline) | Existing /query response format changes | Version API or add response_format field |
| P4-01 (auth on all endpoints) | All existing clients (extension, dashboard) stop working | Add gradual rollout: require auth header but accept requests without it during transition |
| P4-04 (Alembic migrations) | Existing schema.sql-based setup | Run `alembic stamp head` on existing DB before enabling migrations |

### Rollback Strategy

1. **Per-task**: Every task should be a single commit/PR. Rollback = revert the commit.
2. **P0-03 (pipeline wiring)**: Keep old `rag.py` and `query.py` endpoints as `/query/v1`. New pipeline is `/query/v2`. Switch default with feature flag.
3. **P4-01 (auth)**: Add auth middleware in "report-only" mode first (log missing auth tokens), then enforce.
4. **Database changes**: Always create new columns, never drop old ones in the same migration. Two-phase: add → migrate data → drop old.

---

## Step 13 — Final Master Checklist

### Backend
- [ ] P0-06: Add scikit-learn to requirements.txt
- [ ] P1-03: Add timeout to CognitivePipeline.process_query()
- [ ] P0-07: Implement ReflectionEngine (minimal)
- [ ] P1-02: Align EvidenceEngine with paper's 5 dimensions
- [ ] P0-04: Implement real LLM provider for Verbalizer
- [ ] P4-01: Add authentication middleware to all endpoints
- [ ] P4-04: Set up Alembic migrations
- [ ] P4-05: Add rate limiting
- [ ] P4-06: Add structured JSON logging
- [ ] P4-07: Add Sentry error tracking

### Pipeline
- [ ] P0-03: Wire CognitivePipeline into /query endpoint
- [ ] P1-01: Implement identity snapshot threshold (paper Eq. 2)
- [ ] Verify V3Pipeline runs end-to-end (events → identity)
- [ ] Verify CognitivePipeline runs end-to-end (query → response)
- [ ] Add pipeline tracing to API responses
- [ ] Verify 5 invariant principles are enforced in code

### AI
- [ ] P0-04: Connect real LLM to verbalizer
- [ ] Add LLM provider abstraction (OpenAI/Anthropic/local)
- [ ] Add token counting and context window management
- [ ] Add hallucination guardrails (output validation)
- [ ] Add prompt versioning

### Database
- [ ] P1-08: Add GIN indexes on JSONB columns
- [ ] P4-04: Create Alembic migration baseline
- [ ] Consolidate duplicate tables between backends
- [ ] Add missing foreign key constraints
- [ ] Drop dead tables (metadata_store, behavioral_trends, etc.)
- [ ] Verify pgvector index tuning (IVFFLAT lists)

### Frontend
- [ ] P0-02: Fix default API port in client.js
- [ ] P0-01: Add missing API methods to client.js
- [ ] P0-05: Remove fake chart data from Overview.jsx
- [ ] P1-04: Add loading skeletons to all pages
- [ ] P1-05: Add React ErrorBoundary
- [ ] P1-07: Replace hardcoded user_123 with dynamic user ID
- [ ] P2-01: Create Identity visualization page
- [ ] P2-02: Create Evidence explorer page
- [ ] P2-04: Create Memory explorer page
- [ ] P2-03: Create DecisionTrace component
- [ ] P2-05: Create BehaviorTimeline component
- [ ] P2-06: Create PipelineVisualizer component
- [ ] P3-01: Add "Show reasoning" toggle to Chat
- [ ] P3-02: Add EvidenceProvenance component
- [ ] P3-03: Add DecisionScores component
- [ ] P3-04: Add SnapshotDiff component
- [ ] Convert to TypeScript
- [ ] Add responsive CSS
- [ ] Add WebSocket for real-time updates

### Dashboard
- [ ] Verify Sessions.jsx works end-to-end
- [ ] Verify SessionDetail.jsx works end-to-end
- [ ] Every widget shows real data (no mock, no fake)
- [ ] Every API error shown in toast/snackbar
- [ ] Empty states on all data-dependent pages
- [ ] P5-01: Interactive architecture diagram
- [ ] P5-02: Pipeline animation
- [ ] P5-03: Demo mode with sample data
- [ ] P5-04: Metrics dashboard (latency, counts, throughput)
- [ ] P5-05: Evaluation results page

### UI/UX
- [ ] Add onboarding flow for first-time users
- [ ] Add privacy notice / data consent
- [ ] Add mobile-responsive layout
- [ ] Add keyboard navigation / accessibility
- [ ] Add theme persistence
- [ ] Add data export functionality

### Research
- [ ] Verify all paper claims are reproducible via live system
- [ ] Add inline evaluation endpoint (run intent/e2e tests)
- [ ] Verify Decision Engine weights match paper Eq. 1
- [ ] Verify identity evolution threshold matches paper Eq. 2
- [ ] Run latency benchmarks and compare to paper Table 3
- [ ] Run determinism validation (same input → same output)

### Production
- [ ] P4-02: Create Dockerfile + docker-compose.yml
- [ ] P4-03: Set up GitHub Actions CI/CD
- [ ] Fix CORS to specific origins
- [ ] Add HTTPS/TLS
- [ ] Add health check with full status
- [ ] Add request validation middleware
- [ ] Add backup/restore documentation
- [ ] Load test with k6/locust

### Testing
- [ ] Add pytest tests for all backend endpoints
- [ ] Add Vitest tests for all frontend components
- [ ] Add integration tests for full pipeline
- [ ] Add snapshot tests for pipeline outputs
- [ ] Add mock LLM provider for testing
- [ ] Set coverage target (80%+)
- [ ] Add pre-commit hooks (lint + format)

### Documentation
- [ ] Update README.md to match actual architecture
- [ ] Update SETUP.md with correct ports and commands
- [ ] Add API documentation with examples
- [ ] Remove stale sprint summary docs
- [ ] Add CONTRIBUTING.md
- [ ] Add ARCHITECTURE.md matching actual code

### Deployment
- [ ] Choose and document deployment target (Vercel/Fly/Railway)
- [ ] Set up staging environment
- [ ] Configure secrets management
- [ ] Set up monitoring (Grafana/Datadog)
- [ ] Create runbook for common failures
- [ ] Document rollback procedure

---

## Appendix: Key File Paths Reference

### Core Pipeline (backend/)
```
backend/
├── main.py                          # Legacy V1 API (port 3000, SQLAlchemy)
├── app/
│   ├── main.py                      # V2/V3 API (port 8000, asyncpg)
│   ├── api/
│   │   ├── ingest.py                # POST /ingest (V3 pipeline entry)
│   │   ├── query.py                 # POST /query (simple RAG — to be replaced)
│   │   └── profile.py              # GET /profile
│   ├── services/
│   │   ├── enrichment.py            # Keyword NLP
│   │   ├── expansion.py             # Stub
│   │   ├── embedding.py             # Sentence-BERT
│   │   ├── vector_store.py          # pgvector operations
│   │   ├── rag.py                   # Template-based RAG
│   │   ├── persona.py               # Persona lookup
│   │   ├── persona_adapter.py       # Identity → Persona
│   │   ├── feature_engineering.py   # Behavioral metrics
│   │   └── rl_layer.py             # RL alignment
│   └── db/
│       ├── postgres.py              # asyncpg connection pool
│       ├── schema.sql               # V3 base tables
│       └── migration_v3.sql         # V3 cognitive tables
├── cognitive_pipeline/
│   ├── pipeline.py                  # CognitivePipeline orchestrator
│   ├── decision_engine.py           # Deterministic scoring (7 dims)
│   ├── trace.py                     # Pipeline tracing
│   └── data_sources.py              # DEAD CODE
├── cognitive_planning/
│   ├── planner_orchestrator.py      # 4-planner coordinator
│   ├── intent_planner.py            # Intent classification
│   ├── retrieval_planner.py         # Retrieval directive planning
│   ├── reasoning_planner.py         # Reasoning mode selection
│   └── response_planner.py         # Response structure planning
├── pipeline/
│   └── orchestrator.py              # V3Pipeline ingest orchestrator
├── reasoning/
│   ├── behavior_object.py           # BehaviorObject model
│   ├── evidence_engine.py           # Evidence with counter-evidence
│   ├── inference_engine.py          # Rule-based inference
│   ├── reasoning_context.py         # Context model
│   └── rules.py                     # Rule definitions
├── identity/
│   ├── identity_engine.py           # 9 sub-profile construction
│   ├── identity_evolution.py        # Identity evolution + threshold
│   ├── identity_snapshot.py         # Snapshot freeze + versioning
│   └── self_model.py                # Belief tracking + uncertainty
├── rag/
│   ├── retriever.py                 # Multi-source retrieval
│   ├── memory_ranker.py             # Identity-aware ranking
│   ├── fusion.py                    # Evidence fusion
│   ├── context_builder.py           # Context assembly
│   └── citation_manager.py          # Citation tracking
├── verbalizer/
│   └── verbalizer.py                # LLM verbalizer (prompt builder)
├── character/
│   ├── runtime_builder.py           # Runtime state loader
│   ├── character_state.py           # State management
│   ├── character_core.py            # Core character model
│   └── runtime_validation.py        # State validation
├── engines/
│   ├── knowledge_consolidation.py   # Event clustering (790 lines)
│   └── trend_detection.py           # DEAD CODE (700+ lines)
├── memory/
│   ├── base_memory.py               # DEAD CODE
│   ├── episodic_memory.py           # DEAD CODE
│   ├── semantic_memory.py           # DEAD CODE
│   ├── behavioral_memory.py         # DEAD CODE
│   ├── goal_memory.py               # DEAD CODE
│   └── reflection_memory.py         # DEAD CODE
├── providers/
│   ├── base_provider.py             # Abstract interface
│   ├── scrapegraph_provider.py      # LIVE — ScrapeGraphAI integration
│   ├── playwright_provider.py       # PARTIAL — returns mocked data
│   ├── firecrawl_provider.py        # STUB — NotImplementedError
│   ├── browseruse_provider.py       # STUB — NotImplementedError
│   └── provider_manager.py          # NEW — fallback chain
├── core/
│   ├── behavior_gateway.py          # Event normalization + routing
│   └── event_normalizer.py          # Source-specific normalizers
└── shared/
    └── contracts.py                 # Strongly-typed Pydantic models
```

### Frontend (dashboard/)
```
dashboard/src/
├── App.jsx                          # Router + Nav
├── main.jsx                         # Entry point
├── api/client.js                    # Axios API client (MISSING METHODS)
├── pages/
│   ├── Overview.jsx                 # FAKE CHART DATA
│   ├── Sessions.jsx                 # BROKEN
│   ├── SessionDetail.jsx            # BROKEN
│   ├── Analytics.jsx                # WORKING
│   └── Chat.jsx                     # WORKING
├── components/
│   ├── AnimatedStatCard.jsx         # Presentational
│   ├── EnhancedChart.jsx            # Recharts wrapper
│   └── TimezoneSelector.jsx         # UTC/IST toggle
└── utils/
    ├── formatters.js                # Date/number formatting
    └── timezone.js                  # Timezone utilities
```

### Chrome Extension (chrome-extension/)
```
chrome-extension/
├── manifest.json                    # Manifest V3
├── content.js                       # DOM extraction (290 lines, WORKING)
├── background.js                    # Service worker (228 lines, WORKING)
└── popup/
    ├── popup.html                   # Popup UI
    ├── popup.js                     # Popup logic
    └── popup.css                    # Popup styling
```

### Research Paper
```
aimirror_ieee_paper.tex             # IEEE paper (403 lines, 19 refs)
```

---

*End of Master Execution Plan*
