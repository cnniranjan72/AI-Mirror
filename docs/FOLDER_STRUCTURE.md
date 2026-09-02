# AIMirror Folder Structure

## Overview

This document explains the complete folder structure of the AIMirror platform after the production architecture refactor.

## Root Structure

```
AI-Mirror/
├── backend/                 # Legacy backend (simple API)
├── behavioral-engine/       # Main behavioral intelligence engine
├── chrome-extension/        # Chrome extension for data collection
├── dashboard/              # React dashboard
├── docs/                   # Documentation
└── refs/                   # Reference materials and research
```

## Backend (Legacy - Simple API)

```
backend/
├── app/                    # Application code
│   ├── api/               # API endpoints
│   ├── models/            # Data models
│   └── services/          # Business logic
├── database.py            # Database connection
├── main.py               # FastAPI application
└── models.py             # Pydantic models
```

**Purpose**: Simple event storage API. Being gradually deprecated in favor of behavioral-engine.

## Behavioral Engine (Main Platform)

```
behavioral-engine/
├── app/
│   ├── api/                      # API Endpoints
│   │   ├── ingest.py            # Event ingestion
│   │   ├── query.py             # Query endpoint
│   │   ├── profile.py           # Profile endpoint
│   │   ├── chat.py              # Chat endpoint
│   │   ├── action.py            # Action suggestions
│   │   ├── alignment.py         # Goal alignment
│   │   └── feedback.py          # Feedback collection
│   │
│   ├── services/                 # Application Services
│   │   ├── embedding.py         # Embedding generation
│   │   ├── feature_engineering.py # Feature computation
│   │   ├── persona.py           # Persona generation (old)
│   │   ├── rag_engine.py        # RAG system
│   │   ├── vector_store.py      # Vector database
│   │   ├── trends.py            # Trend analysis
│   │   ├── action_engine.py     # Action suggestions
│   │   ├── alignment.py         # Goal alignment
│   │   ├── reward.py            # Reward modeling
│   │   ├── rl_bandit.py         # RL bandit
│   │   └── ...
│   │
│   ├── models/                   # Data Models (Old)
│   │   ├── schemas.py           # Pydantic schemas (deprecated)
│   │   └── rl_schemas.py        # RL schemas
│   │
│   ├── database.py              # Database connection
│   ├── main.py                  # FastAPI application
│   └── utils/                   # Utilities
│
├── backend/                      # NEW PRODUCTION ARCHITECTURE
│   │
│   ├── shared/                  # Shared Contracts
│   │   ├── __init__.py
│   │   └── contracts.py         # Strongly-typed models
│   │
│   ├── core/                    # Core Business Logic
│   │   ├── __init__.py
│   │   ├── behavior_gateway.py  # Event normalization gateway
│   │   └── event_normalizer.py  # Source-specific normalizers
│   │
│   ├── providers/               # Content Intelligence Layer
│   │   ├── __init__.py
│   │   ├── base_provider.py     # Provider interface
│   │   ├── playwright_provider.py # Playwright implementation
│   │   ├── scrapegraph_provider.py # ScrapeGraph (placeholder)
│   │   ├── firecrawl_provider.py # Firecrawl (placeholder)
│   │   └── browseruse_provider.py # BrowserUse (placeholder)
│   │
│   ├── engines/                 # Intelligence Engines
│   │   ├── __init__.py
│   │   ├── knowledge_consolidation.py # Deduplication & clustering
│   │   └── persona_engine.py    # Persona Engine V2 (placeholder)
│   │
│   ├── memory/                  # Behavioral Memory System
│   │   ├── __init__.py
│   │   ├── base_memory.py       # Memory interface
│   │   ├── episodic_memory.py   # Individual events
│   │   ├── semantic_memory.py   # Embeddings & knowledge
│   │   ├── behavioral_memory.py # Patterns & clusters
│   │   ├── goal_memory.py       # Goals & progress
│   │   └── reflection_memory.py # Reflections
│   │
│   ├── character/               # Virtual Character (Placeholder)
│   │   ├── __init__.py
│   │   └── character_engine.py  # Character management
│   │
│   ├── planner/                 # Planning Layer (Placeholder)
│   │   ├── __init__.py
│   │   ├── memory_planner.py    # Memory planning
│   │   ├── retrieval_planner.py # Query planning
│   │   ├── reflection_planner.py # Reflection scheduling
│   │   ├── recommendation_planner.py # Recommendation planning
│   │   └── rl_planner.py        # RL planning
│   │
│   ├── workers/                 # Background Workers (Placeholder)
│   │   ├── __init__.py
│   │   ├── consolidation_worker.py # Knowledge consolidation
│   │   ├── reflection_worker.py # Periodic reflections
│   │   └── trend_worker.py      # Trend detection
│   │
│   ├── db/                      # Database Layer (Placeholder)
│   │   ├── __init__.py
│   │   ├── postgres.py          # PostgreSQL connection
│   │   ├── vector_store.py      # Vector database
│   │   └── repositories/        # Data access objects
│   │
│   └── utils/                   # Utilities (Placeholder)
│       ├── __init__.py
│       ├── logging.py
│       └── config.py
│
├── migrations/                  # Database migrations
├── tests/                       # Test suite
├── chroma_db/                  # ChromaDB storage
├── requirements.txt            # Python dependencies
└── README.md                   # Documentation
```

## Chrome Extension

```
chrome-extension/
├── manifest.json              # Extension manifest
├── content.js                # Content script (Instagram observer)
├── background.js             # Service worker
├── popup/                    # Extension popup UI
│   ├── popup.html
│   ├── popup.js
│   └── popup.css
└── icons/                    # Extension icons
```

**Purpose**: Observes Instagram Reels, extracts behavioral data, sends to backend.

## Dashboard

```
dashboard/
├── src/
│   ├── components/           # React components
│   │   ├── Analytics/       # Analytics components
│   │   ├── Chat/           # Chat interface
│   │   ├── Profile/        # Profile components
│   │   └── ...
│   │
│   ├── pages/               # Page components
│   │   ├── Dashboard.jsx
│   │   ├── Analytics.jsx
│   │   ├── Profile.jsx
│   │   └── ...
│   │
│   ├── api/                 # API client
│   │   └── client.js
│   │
│   ├── utils/               # Utility functions
│   ├── App.jsx             # Main app component
│   └── main.jsx            # Entry point
│
├── public/                  # Static assets
├── package.json            # Node dependencies
├── vite.config.js          # Vite configuration
└── README.md              # Documentation
```

**Purpose**: User-facing dashboard for viewing behavioral insights.

## Documentation

```
docs/
├── Architecture.md          # Complete architecture guide
├── PRODUCTION_GUIDE.md      # Deployment and operations
├── FOLDER_STRUCTURE.md     # This document
└── adr/                    # Architecture decision records
```

## References

```
refs/
├── Scrapegraph-ai/         # ScrapeGraphAI repository (for research)
└── ...                     # Other reference materials
```

## Module Responsibilities

### Backend/Shared
**Responsibility**: Define universal contracts and data models
**Key Files**: `contracts.py`
**Dependencies**: None (foundation layer)

### Backend/Core
**Responsibility**: Core business logic and event processing
**Key Files**: `behavior_gateway.py`, `event_normalizer.py`
**Dependencies**: `shared`

### Backend/Providers
**Responsibility**: Content extraction from various sources
**Key Files**: `base_provider.py`, `playwright_provider.py`
**Dependencies**: `shared`

### Backend/Engines
**Responsibility**: Intelligence processing and analysis
**Key Files**: `knowledge_consolidation.py`, `persona_engine.py`
**Dependencies**: `shared`, `core`

### Backend/Memory
**Responsibility**: Memory storage and retrieval
**Key Files**: All memory modules
**Dependencies**: `shared`

### Backend/Character
**Responsibility**: Virtual character management
**Key Files**: `character_engine.py`
**Dependencies**: `shared`, `memory`

### Backend/Planner
**Responsibility**: Planning and scheduling
**Key Files**: All planner modules
**Dependencies**: `shared`, `memory`

### Backend/Workers
**Responsibility**: Background processing
**Key Files**: All worker modules
**Dependencies**: `shared`, `engines`, `memory`

### Backend/DB
**Responsibility**: Database access and management
**Key Files**: `postgres.py`, `vector_store.py`
**Dependencies**: `shared`

## Import Patterns

### Correct Import Pattern

```python
# Import from shared contracts
from backend.shared.contracts import BehaviorEvent, Persona

# Import from core
from backend.core.behavior_gateway import get_behavior_gateway

# Import from providers
from backend.providers import PlaywrightProvider

# Import from engines
from backend.engines import KnowledgeConsolidationEngine

# Import from memory
from backend.memory import get_episodic_memory
```

### Incorrect Import Pattern

```python
# Don't import from old models
from app.models.schemas import BehavioralEvent  # DEPRECATED

# Don't import implementation details
from backend.memory.episodic_memory import EpisodicMemory  # Use getter instead

# Don't skip layers
from backend.memory.base_memory import BaseMemory  # Internal use only
```

## File Naming Conventions

### Python Files
- **Modules**: `snake_case.py` (e.g., `behavior_gateway.py`)
- **Classes**: `PascalCase` (e.g., `BehaviorGateway`)
- **Functions**: `snake_case` (e.g., `get_behavior_gateway`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_BATCH_SIZE`)

### Documentation Files
- **Guides**: `UPPER_SNAKE_CASE.md` (e.g., `MIGRATION_GUIDE.md`)
- **Technical**: `PascalCase.md` (e.g., `Architecture.md`)

## Configuration Files

### Root Level
- `.env` - Environment variables (not in git)
- `.env.example` - Environment template
- `.gitignore` - Git ignore patterns
- `requirements.txt` - Python dependencies
- `package.json` - Node dependencies

### Module Level
- `__init__.py` - Package initialization
- `conftest.py` - Pytest configuration
- `README.md` - Module documentation

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_behavior_gateway.py
│   ├── test_knowledge_consolidation.py
│   └── ...
│
├── integration/             # Integration tests
│   ├── test_ingestion_flow.py
│   ├── test_query_flow.py
│   └── ...
│
├── regression/              # Regression tests
│   ├── test_api_compatibility.py
│   └── ...
│
└── fixtures/               # Test fixtures
    └── ...
```

## Data Storage

### ChromaDB
**Location**: `behavioral-engine/chroma_db/`
**Purpose**: Vector embeddings storage
**Type**: Persistent local storage

### PostgreSQL (Neon)
**Location**: Remote (cloud)
**Purpose**: Structured data storage
**Type**: Cloud database

### SQLite (Legacy)
**Location**: `backend/aimirror.db`
**Purpose**: Simple event storage
**Type**: Local database (deprecated)

## Logs

### Application Logs
**Location**: Console output (stdout)
**Format**: Structured JSON logs
**Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Access Logs
**Location**: FastAPI automatic logging
**Format**: HTTP request logs

## Environment Variables

### Required
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API key (for embeddings)

### Optional
- `CHROMA_DB_PATH` - ChromaDB storage path
- `LOG_LEVEL` - Logging level
- `CORS_ORIGINS` - CORS allowed origins

## Development Workflow

### 1. Local Development
```bash
cd behavioral-engine
python -m uvicorn app.main:app --reload
```

### 2. Testing
```bash
pytest tests/
```

### 3. Linting
```bash
flake8 backend/
black backend/
mypy backend/
```

### 4. Documentation
```bash
# Update docs/ as needed
```

## Deployment Structure

### Production
```
/opt/aimirror/
├── behavioral-engine/
├── dashboard/
├── logs/
└── data/
```

### Docker (Future)
```
docker/
├── Dockerfile.backend
├── Dockerfile.dashboard
└── docker-compose.yml
```

## Summary

The folder structure is organized into clear layers:

1. **Shared** - Universal contracts
2. **Core** - Business logic
3. **Providers** - External integrations
4. **Engines** - Intelligence processing
5. **Memory** - Data storage
6. **Character** - User representation
7. **Planner** - Planning logic
8. **Workers** - Background processing
9. **DB** - Database access
10. **API** - HTTP endpoints

Each layer has clear responsibilities and dependencies flow in one direction (no circular dependencies).
