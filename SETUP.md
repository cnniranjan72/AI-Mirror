# AIMirror Setup Guide

Complete production-grade behavioral intelligence system.

## Architecture

```
Chrome Extension (DOM extraction)
    ↓
Backend FastAPI (enrich → expand → embed → store)
    ↓
Postgres + pgvector (embeddings + personas)
    ↓
RAG → Persona Engine → RL-ready Layer
```

---

## Quick Start (5 minutes)

### 1. Backend Setup

```powershell
# Navigate to backend
cd C:\Users\cnnir\Documents\AI-Mirror\backend

# Install dependencies
pip install -r requirements.txt

# Setup database (already done!)
python setup_db.py

# Start server
python -m uvicorn app.main:app --host localhost --port 8000 --reload
```

Open browser: http://localhost:8000/docs

---

### 2. Chrome Extension Setup

```powershell
# Extension is in chrome-extension folder
cd C:\Users\cnnir\Documents\AI-Mirror\chrome-extension

# Load in Chrome:
# 1. Open chrome://extensions
# 2. Enable "Developer mode"
# 3. Click "Load unpacked"
# 4. Select: chrome-extension folder
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/ingest` | POST | Full pipeline (events → embeddings) |
| `/query` | POST | RAG query with persona context |
| `/profile` | GET | Get user persona + alignment |

---

## Test Commands (PowerShell)

### Health Check
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" | ConvertTo-Json
```

### Ingest Events
```powershell
$body = @{
    user_id = "demo_user"
    events = @(
        @{
            reel_id = "reel_001"
            username = "finance_guru"
            caption = "How to start investing in stocks with small capital. Beginner friendly! #finance #investing #stocks"
            hashtags = @("#finance", "#investing", "#stocks")
            audio = "Trending Finance Audio"
            watch_time = 18.5
            timestamp = "2024-01-15T10:30:00Z"
            session_id = "sess_001"
        }
    )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:8000/ingest" -Method POST -ContentType "application/json" -Body $body
```

### Get Profile
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/profile?user_id=demo_user" | ConvertTo-Json -Depth 10
```

### RAG Query
```powershell
$body = @{
    user_id = "demo_user"
    query = "What content do I watch most?"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/query" -Method POST -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 10
```

---

## Pipeline Flow

When you send events to `/ingest`:

1. **Store** → Raw events saved to `events` table
2. **Enrich** → NLP analysis (topics, sentiment, intent)
3. **Expand** → Short caption → rich embeddable text
4. **Embed** → Generate 384-dim vector (MiniLM-L6-v2)
5. **Store** → Save to `embeddings` table (pgvector)
6. **Features** → Compute behavioral metrics
7. **Persona** → Map to archetype (Explorer/Focused Learner/etc)
8. **RL** → Compute alignment + suggest action

---

## Database Schema

### events
- `id`, `user_id`, `reel_id`, `username`, `caption`
- `hashtags` (JSONB), `audio`, `watch_time`, `timestamp`, `session_id`

### embeddings
- `id`, `user_id`, `text`, `embedding` (VECTOR(384))
- `doc_type`, `metadata` (JSONB), `content_tsv` (full-text search)

### personas
- `user_id`, `interest_vector`, `behavior_vector`
- `persona_label`, `traits`, `recommendations`, `confidence`

### actions_log (RL)
- `user_id`, `action_type`, `action_data`, `state`, `reward`

---

## File Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app
│   ├── api/
│   │   ├── ingest.py        # POST /ingest
│   │   ├── query.py         # POST /query
│   │   └── profile.py       # GET /profile
│   ├── services/
│   │   ├── enrichment.py    # NLP topics/sentiment/intent
│   │   ├── expansion.py     # Content expansion
│   │   ├── embedding.py     # MiniLM-L6-v2 encoder
│   │   ├── vector_store.py  # pgvector operations
│   │   ├── feature_engineering.py
│   │   ├── rag.py           # RAG with hybrid search
│   │   ├── persona.py       # Persona archetypes
│   │   └── rl_layer.py      # RL-ready state/actions
│   └── db/
│       ├── postgres.py      # Async connection pool
│       └── schema.sql       # Database schema
├── .env                     # DATABASE_URL
├── requirements.txt
└── setup_db.py              # Run schema

chrome-extension/
├── content.js               # Reel extraction + batching
├── manifest.json
└── icons/
```

---

## Environment Variables

Create `.env` in `backend/`:

```
DATABASE_URL=postgresql://user:pass@host/neondb?sslmode=require
PORT=8000
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

---

## Chrome Extension Features

- **Viewport detection** → Finds most visible video
- **Metadata extraction** → Username, caption, hashtags, audio
- **Watch tracking** → Start/stop times, session ID
- **Batching** → Send every 10 events OR 30 seconds
- **Retry logic** → Failed batches re-queued

---

## Persona Archetypes

| Archetype | Description |
|-----------|-------------|
| **Explorer** | Diverse content, high curiosity |
| **Focused Learner** | Deep engagement, educational content |
| **High-Stimulation Seeker** | Rapid scrolling, stimulation-seeking |
| **Passive Consumer** | Casual browsing, low engagement |

---

## Troubleshooting

### Server won't start
```powershell
# Check Python version (need 3.10+)
python --version

# Install missing dependencies
pip install -r requirements.txt --force-reinstall

# Check .env exists
cat .env
```

### Database connection error
```powershell
# Verify DATABASE_URL format
# Should be: postgresql://user:pass@host/db?sslmode=require

# Test connection
python -c "import asyncio; from app.db.postgres import health; print(asyncio.run(health()))"
```

### Extension not injecting
```powershell
# Check manifest.json loaded
# Check console for [AIMirror] logs
# Run in console: aimirrorDebug()
```

---

## Development Commands

```powershell
# Auto-reload server
python -m uvicorn app.main:app --reload

# Pre-load embedding model
python -c "from app.services.embedding import encode; print('Model ready')"

# Check database health
python -c "import asyncio; from app.db.postgres import health; print(asyncio.run(health()))"

# Reset database
python setup_db.py
```

---

## Production Deployment

```powershell
# Run without reload
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or using Gunicorn (Unix)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

---

## Full System Test

```powershell
# 1. Start server (in one terminal)
python -m uvicorn app.main:app --reload

# 2. Test health
Invoke-RestMethod http://localhost:8000/health

# 3. Send test events (5+ for persona detection)
$events = @()
for ($i=1; $i -le 5; $i++) {
    $events += @{
        reel_id = "reel_$i"
        username = "creator_$i"
        caption = "This is about technology and coding #tech #code"
        hashtags = @("#tech", "#code")
        audio = "Tech Audio"
        watch_time = 10 + $i
        timestamp = (Get-Date).ToString("o")
        session_id = "test_session"
    }
}

$body = @{ user_id = "test_user"; events = $events } | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "http://localhost:8000/ingest" -Method POST -ContentType "application/json" -Body $body

# 4. Check profile
Invoke-RestMethod "http://localhost:8000/profile?user_id=test_user" | ConvertTo-Json -Depth 10

# 5. Query insights
$q = @{ user_id = "test_user"; query = "What do I watch?" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/query" -Method POST -ContentType "application/json" -Body $q
```

---

## ✅ Success Indicators

- ✅ Server starts without errors
- ✅ `/health` returns healthy
- ✅ `/ingest` returns success with persona_label
- ✅ `/profile` returns persona + alignment scores
- ✅ `/query` returns contextual answer
- ✅ Extension console shows [AIMirror] logs

---

**System Ready!** 🚀

Your AIMirror is a production-grade behavioral intelligence pipeline:
- Chrome Extension extracts Instagram Reels data
- FastAPI processes through 8-layer pipeline
- Postgres + pgvector stores embeddings
- RAG provides contextual insights
- Persona Engine maps behavior to archetypes
- RL layer tracks actions for future training
