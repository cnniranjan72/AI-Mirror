# AIMirror Production Architecture

## Overview

AIMirror has been refactored from a prototype into a production-grade Behavioral Intelligence Platform. This document describes the new modular architecture designed for AI research, long-term product development, enterprise deployment, and future multimodal intelligence.

## Architecture Principles

1. **Single Responsibility**: Every module has one clear purpose
2. **No Circular Dependencies**: Clean dependency graph
3. **No Duplicated Logic**: DRY principle throughout
4. **Strongly Typed**: Pydantic models as universal language
5. **Provider Agnostic**: Pluggable providers for all external services
6. **Memory Separation**: Different memory types in separate modules
7. **Clean Architecture**: Dependency inversion, interface segregation

## Folder Structure

```
backend/
├── api/                    # API endpoints (FastAPI routers)
│   ├── ingest.py          # Event ingestion endpoint
│   ├── query.py           # Query endpoint
│   ├── profile.py         # Profile endpoint
│   └── ...
│
├── core/                   # Core business logic
│   ├── behavior_gateway.py    # Unified event gateway
│   └── event_normalizer.py    # Source-specific normalization
│
├── providers/              # Content Intelligence Layer
│   ├── base_provider.py       # Provider interface
│   ├── playwright_provider.py # Playwright implementation
│   ├── scrapegraph_provider.py # ScrapeGraph placeholder
│   ├── firecrawl_provider.py  # Firecrawl placeholder
│   └── browseruse_provider.py # BrowserUse placeholder
│
├── engines/                # Intelligence Engines
│   ├── knowledge_consolidation.py  # Deduplication & clustering
│   └── persona_engine.py           # Persona Engine V2
│
├── memory/                 # Behavioral Memory System
│   ├── episodic_memory.py     # Individual events & sessions
│   ├── semantic_memory.py     # Embeddings & knowledge
│   ├── behavioral_memory.py   # Long-term habits & patterns
│   ├── goal_memory.py         # User goals & progress
│   └── reflection_memory.py   # Periodic reflections
│
├── character/              # Virtual Character
│   └── character_engine.py    # User's computational self
│
├── planner/                # Planning Layer
│   ├── memory_planner.py      # Memory retrieval planning
│   ├── retrieval_planner.py   # Query planning
│   ├── reflection_planner.py  # Reflection scheduling
│   ├── recommendation_planner.py # Recommendation planning
│   └── rl_planner.py          # RL planning (future)
│
├── workers/                # Background Workers
│   ├── consolidation_worker.py # Knowledge consolidation
│   ├── reflection_worker.py    # Periodic reflections
│   └── trend_worker.py         # Trend detection
│
├── db/                     # Database Layer
│   ├── postgres.py            # PostgreSQL connection
│   ├── vector_store.py        # Vector database
│   └── repositories/          # Data access objects
│
├── services/               # Application Services
│   ├── embedding_service.py   # Embedding generation
│   ├── nlp_service.py         # NLP processing
│   └── ...
│
├── shared/                 # Shared Contracts
│   └── contracts.py           # Strongly-typed models
│
├── models/                 # Legacy models (deprecated)
│   └── schemas.py             # Old schemas
│
└── utils/                  # Utilities
    ├── logging.py
    ├── config.py
    └── ...
```

## Data Flow

### 1. Event Ingestion Flow

```
Chrome Extension
    ↓
POST /ingest (API)
    ↓
Behavior Gateway
    ↓
Event Normalizer → BehaviorEvent (unified schema)
    ↓
Knowledge Consolidation Engine
    ↓
├─→ Episodic Memory (individual events)
├─→ Semantic Memory (embeddings)
└─→ Behavioral Memory (patterns & clusters)
    ↓
Persona Engine V2
    ↓
Character Update
```

### 2. Query Flow

```
User Query
    ↓
POST /query (API)
    ↓
Retrieval Planner
    ↓
├─→ Episodic Memory (recent events)
├─→ Semantic Memory (semantic search)
├─→ Behavioral Memory (patterns)
└─→ Goal Memory (goal alignment)
    ↓
Context Fusion
    ↓
RAG Engine
    ↓
Response
```

### 3. Reflection Flow

```
Reflection Worker (scheduled)
    ↓
Reflection Planner
    ↓
├─→ Episodic Memory (period events)
├─→ Behavioral Memory (patterns)
└─→ Goal Memory (goal progress)
    ↓
Reflection Engine
    ↓
Reflection Memory (store)
    ↓
Character Update
```

## Core Modules

### 1. Behavior Gateway

**Purpose**: Normalize all incoming events into unified `BehaviorEvent` schema

**Responsibilities**:
- Accept events from multiple sources (extension, dashboard, mobile, etc.)
- Normalize source-specific formats
- Validate event integrity
- Enrich with metadata
- Route to appropriate processors

**Key Contract**: `BehaviorEvent`

**Future Sources**:
- Chrome Extension ✅
- Dashboard (planned)
- Mobile App (planned)
- Saved Reels (planned)
- Browser Agents (planned)

### 2. Content Intelligence Layer

**Purpose**: Provider-agnostic content extraction and intelligence

**Architecture**: Provider pattern with pluggable implementations

**Providers**:
- `PlaywrightProvider`: Browser automation (implemented)
- `ScrapeGraphProvider`: LLM-powered extraction (placeholder)
- `FirecrawlProvider`: Managed scraping (placeholder)
- `BrowserUseProvider`: Agent-based extraction (placeholder)

**Key Contract**: `NormalizedContent`

**No provider-specific logic leaks outside this layer**

### 3. Knowledge Consolidation Engine

**Purpose**: Prevent repetitive memory through intelligent clustering

**Responsibilities**:
- Semantic deduplication
- Trend clustering
- Topic clustering
- Creator aggregation
- Behavior frequency analysis
- Memory compression
- Confidence estimation
- Temporal weighting

**Example**:
```
100 AI roadmap reels
    ↓
One evolving topic cluster
    ├─ frequency: 100
    ├─ engagement: 0.75
    ├─ growth: +15/day
    └─ confidence: 0.95
```

**Key Contract**: `BehaviorCluster`

### 4. Behavioral Memory System

**Architecture**: Separate memory modules for different types

#### 4.1 Episodic Memory
- Stores: Individual events, timestamps, watch sessions
- Purpose: Chronological behavioral history
- Retrieval: Time-based, session-based

#### 4.2 Semantic Memory
- Stores: Embeddings, expanded content, knowledge
- Purpose: Semantic search and retrieval
- Retrieval: Vector similarity

#### 4.3 Behavioral Memory
- Stores: Long-term habits, topic evolution, creator affinity, interest drift
- Purpose: Behavioral patterns and trends
- Retrieval: Pattern-based, cluster-based

#### 4.4 Goal Memory
- Stores: User goals, goal alignment, progress
- Purpose: Goal tracking and alignment
- Retrieval: Goal-based, status-based

#### 4.5 Reflection Memory
- Stores: Daily/weekly/monthly summaries, system reflections
- Purpose: Periodic introspection
- Retrieval: Period-based

**Key Contract**: `MemoryRecord`

### 5. Persona Engine V2

**Purpose**: Comprehensive behavioral modeling

**Persona Contains**:
- Identity (archetype, confidence)
- Interest Graph (primary, emerging, declining)
- Behavior Graph (patterns, frequencies)
- Attention Profile (span, consistency, peak times)
- Learning Style (preferences, content types)
- Exploration Score (exploration vs exploitation)
- Consistency Score (behavioral stability)
- Creator Affinity (creator preferences)
- Topic Affinity (topic preferences)
- Strengths & Weaknesses
- Confidence & Evolution Timeline

**Key Contract**: `Persona`

**Evolution**: Persona evolves continuously with new data

### 6. Virtual Character

**Purpose**: User's computational self (NOT chatbot logic)

**Character Contains**:
- Identity summary
- Behavioral signature
- Active goals
- Memory references (episodic, semantic, behavioral)
- Communication style
- Reflection state
- Current persona
- Character state

**Key Contract**: `Character`

### 7. Planning Layer

**Purpose**: Intelligent planning for various operations

**Planners** (architecture only, no implementation yet):
- `MemoryPlanner`: Plan memory storage and retrieval
- `RetrievalPlanner`: Plan query execution
- `ReflectionPlanner`: Schedule reflections
- `RecommendationPlanner`: Plan recommendations
- `RLPlanner`: Plan RL operations (future)

## Shared Contracts

All modules communicate using strongly-typed Pydantic models:

1. **BehaviorEvent**: Unified behavioral event
2. **NormalizedContent**: Provider-agnostic content
3. **BehaviorCluster**: Consolidated behavioral pattern
4. **Persona**: Comprehensive behavioral persona
5. **Character**: Virtual character state
6. **MemoryRecord**: Universal memory record
7. **GoalState**: User goal state
8. **Reflection**: System reflection

These models are the **universal language** of the platform.

## Backward Compatibility

### Existing APIs Preserved

- `POST /ingest` - Event ingestion (now uses Behavior Gateway)
- `POST /query` - Query behavioral data
- `GET /profile` - Get user profile
- `GET /health` - Health check

### Migration Strategy

1. **Phase 1**: New modules coexist with old code
2. **Phase 2**: Route through new modules while preserving old behavior
3. **Phase 3**: Gradually deprecate old code
4. **Phase 4**: Remove deprecated code

### Extension Compatibility

Chrome extension continues to work without changes. Behavior Gateway handles format conversion.

## Design Patterns

### 1. Provider Pattern
Used in Content Intelligence Layer for pluggable providers

### 2. Repository Pattern
Used in database layer for data access abstraction

### 3. Singleton Pattern
Used for service instances (embedding service, vector store, etc.)

### 4. Strategy Pattern
Used in memory modules for different retrieval strategies

### 5. Observer Pattern
Used for event propagation and notifications

## Coding Standards

Every module follows:

1. **Type Hints**: All functions have type annotations
2. **Docstrings**: Google-style docstrings
3. **Logging**: Structured logging with context
4. **Dependency Injection**: No global state
5. **Config Driven**: All configuration externalized
6. **SOLID Principles**: Single responsibility, open/closed, etc.
7. **Clean Architecture**: Dependency inversion

## Testing Strategy

### Unit Tests
- Test individual modules in isolation
- Mock dependencies
- Test edge cases

### Integration Tests
- Test module interactions
- Test data flow
- Test API endpoints

### End-to-End Tests
- Test complete pipeline
- Test extension → backend → database
- Test query flow

## Performance Considerations

### Scalability
- Async/await throughout
- Connection pooling
- Batch processing
- Background workers

### Optimization
- Vector indexing
- Query caching
- Memory compression
- Temporal weighting

## Security

### Data Privacy
- User data isolation
- Encryption at rest
- Encryption in transit
- Access control

### API Security
- Authentication
- Rate limiting
- Input validation
- CORS configuration

## Monitoring

### Metrics
- Event ingestion rate
- Query latency
- Memory usage
- Error rates

### Logging
- Structured logging
- Log levels
- Context propagation
- Error tracking

## Future Extensions

### Multimodal Intelligence
- Video content analysis
- Audio transcription
- Image understanding
- Cross-modal retrieval

### Advanced RL
- PPO implementation
- Reward modeling
- Policy optimization
- Exploration strategies

### Distributed System
- Horizontal scaling
- Load balancing
- Distributed caching
- Message queues

## Migration Notes

### From Old Architecture

1. **Event Ingestion**: Now goes through Behavior Gateway
2. **Memory Storage**: Now separated into 5 memory types
3. **Persona**: Upgraded to V2 with comprehensive modeling
4. **Content Extraction**: Now uses provider architecture

### Breaking Changes

None. All existing APIs preserved.

### Deprecations

- Old `BehavioralEvent` schema (use `BehaviorEvent` from shared.contracts)
- Direct vector store access (use memory modules)
- Monolithic persona (use Persona V2)

## Conclusion

This architecture provides a solid foundation for:
- Long-term product development
- Enterprise deployment
- AI research
- Future multimodal intelligence
- Extensibility and maintainability

The modular design ensures that new features can be added without disrupting existing functionality, and the strongly-typed contracts provide clear interfaces between modules.
