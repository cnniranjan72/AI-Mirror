# Behavioral Intelligence Engine

**Complete AI-powered behavioral analysis system with intelligence layer and persona generation**

## 🎯 Overview

The Behavioral Intelligence Engine is the core AI brain of AIMirror. It transforms raw Instagram usage data into:

- **Structured insights** - Session summaries and behavioral traits
- **Trend detection** - Identifies behavioral changes over time
- **Human-readable insights** - Explains patterns without LLMs
- **Behavioral personas** - Creates user archetypes
- **Semantic retrieval** - RAG-style query system

**No external APIs required - 100% local and private.**

## 🏗 Architecture

```
behavioral-engine/
│
├── app/
│   ├── main.py                          # FastAPI application
│   ├── api/
│   │   ├── ingest.py                    # POST /ingest - Process events
│   │   ├── query.py                     # POST /query - Retrieve insights
│   │   └── profile.py                   # GET /profile - Generate persona
│   ├── services/
│   │   ├── feature_engineering.py       # Session summaries & traits
│   │   ├── trends.py                    # Trend detection across sessions
│   │   ├── insight_engine.py            # Human-readable insight generation
│   │   ├── persona.py                   # Behavioral persona generation
│   │   ├── embedding.py                 # Sentence-transformers embeddings
│   │   └── vector_store.py              # ChromaDB vector storage
│   └── models/
│       └── schemas.py                   # Pydantic data models
│
├── chroma_db/                           # ChromaDB persistence (auto-created)
├── requirements.txt
└── README.md
```

## 📦 Installation

```bash
# Navigate to behavioral-engine directory
cd behavioral-engine

# Install dependencies
pip install -r requirements.txt
```

## 🚀 Running the Engine

```bash
# Start the server
uvicorn app.main:app --reload --port 8000

# Server will be available at:
# http://localhost:8000
```

## 📡 API Endpoints

### 1. Health Check

```bash
GET http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "vector_store": "connected",
  "collection_count": 42
}
```

### 2. Ingest Events

```bash
POST http://localhost:8000/ingest
```

**Request Body:**
```json
{
  "events": [
    {
      "reel_id": "C8xYz123",
      "username": "creator_name",
      "watch_time": 4.2,
      "liked": true,
      "timestamp": "2026-04-08T14:30:00.000Z",
      "session_id": "session_abc123"
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "events_processed": 1,
  "summaries_created": 2,
  "embeddings_stored": 2,
  "message": "Successfully processed 1 events from 1 sessions"
}
```

### 3. Query Insights

```bash
POST http://localhost:8000/query
```

**Request Body:**
```json
{
  "query": "What is my behavior pattern?",
  "top_k": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "text": "User watched 35 reels with average watch time 3.2 seconds...",
      "score": 0.8542,
      "metadata": {
        "type": "session_summary",
        "session_id": "session_abc123",
        "timestamp": "2026-04-08T14:30:00.000Z"
      }
    }
  ],
  "query": "What is my behavior pattern?"
}
```

## 🧠 How It Works

### 1. Feature Engineering

**Session Summary:**
- Total watch time
- Average watch time
- Like ratio
- Reels count
- Session duration

**Behavioral Traits:**
- Attention score (normalized watch time)
- Engagement score (like ratio)
- Activity level (reels per minute)

### 2. Embedding Generation

Uses `sentence-transformers` with `all-MiniLM-L6-v2` model:
- Lightweight (80MB)
- Fast inference
- 384-dimensional embeddings
- No external API calls

### 3. Vector Storage

ChromaDB stores:
- Embeddings (384-dim vectors)
- Original text descriptions
- Metadata (session_id, type, timestamp, metrics)

### 4. Semantic Retrieval

Query process:
1. Embed query text
2. Search ChromaDB for similar vectors
3. Return top-k results with similarity scores

## 🔧 Configuration

All configuration is in `app/main.py`:
- CORS settings
- Logging level
- Model selection

ChromaDB persistence directory: `./chroma_db`

## 📊 Example Usage

```python
import requests

# Ingest events
response = requests.post(
    "http://localhost:8000/ingest",
    json={
        "events": [
            {
                "reel_id": "reel_123",
                "username": "user1",
                "watch_time": 5.2,
                "liked": True,
                "timestamp": "2026-04-08T14:30:00.000Z",
                "session_id": "session_1"
            }
        ]
    }
)
print(response.json())

# Query insights
response = requests.post(
    "http://localhost:8000/query",
    json={
        "query": "Show me high engagement sessions",
        "top_k": 3
    }
)
print(response.json())
```

## 🧪 Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test ingest (with sample data)
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"events": [{"reel_id": "test", "username": "user", "watch_time": 3.0, "liked": false, "timestamp": "2026-04-08T14:30:00.000Z", "session_id": "test_session"}]}'

# Test query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are my behavior patterns?", "top_k": 5}'
```

## 📝 Logging

All operations are logged with timestamps:
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Failures with stack traces

Logs appear in console output.

## 🔒 Production Considerations

1. **CORS**: Update `allow_origins` in `main.py` for production
2. **Authentication**: Add API key validation
3. **Rate Limiting**: Add request throttling
4. **Monitoring**: Add metrics collection
5. **Persistence**: Backup `chroma_db/` directory regularly

## 🚀 Integration with AIMirror

This engine integrates with:
- **Chrome Extension**: Sends events via `/ingest`
- **Dashboard**: Queries insights via `/query`
- **Backend API**: Can forward events from main backend

## 📚 Dependencies

- **FastAPI**: Web framework
- **ChromaDB**: Vector database
- **sentence-transformers**: Embedding generation
- **Pydantic**: Data validation
- **uvicorn**: ASGI server

## 🎯 Success Criteria

✅ Events processed and stored
✅ Embeddings generated locally (no external APIs)
✅ Semantic search working
✅ Fast response times (<1s)
✅ Persistent storage

## 🔥 Next Steps

1. Start the engine: `uvicorn app.main:app --reload`
2. Send test events via `/ingest`
3. Query insights via `/query`
4. Integrate with Chrome extension
5. Build dashboard visualizations

---

**Built for AIMirror - Behavioral Digital Twin**
