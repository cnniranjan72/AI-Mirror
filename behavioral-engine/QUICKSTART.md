# Behavioral Intelligence Engine - Quick Start Guide

## 🚀 Installation & Setup

### 1. Install Dependencies

```bash
cd behavioral-engine
pip install -r requirements.txt
```

**Note:** First run will download the sentence-transformers model (~80MB).

### 2. Start the Server

```bash
uvicorn app.main:app --reload --port 8000
```

Server will be available at: `http://localhost:8000`

### 3. Verify Installation

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "vector_store": "connected",
  "collection_count": 0
}
```

---

## 📡 API Endpoints

### 1. **POST /ingest** - Process Behavioral Events

**Purpose:** Ingest Instagram usage data, compute features, generate embeddings, detect trends.

**Request:**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "reel_id": "reel_123",
        "username": "creator1",
        "watch_time": 5.2,
        "liked": true,
        "timestamp": "2026-04-08T14:30:00.000Z",
        "session_id": "session_1"
      },
      {
        "reel_id": "reel_456",
        "username": "creator2",
        "watch_time": 2.1,
        "liked": false,
        "timestamp": "2026-04-08T14:31:00.000Z",
        "session_id": "session_1"
      }
    ]
  }'
```

**Response:**
```json
{
  "status": "success",
  "events_processed": 2,
  "summaries_created": 2,
  "embeddings_stored": 2,
  "message": "Successfully processed 2 events from 1 sessions"
}
```

**What Happens:**
1. Events grouped by session
2. Session summary computed (watch time, like ratio, etc.)
3. Behavioral traits calculated (attention, engagement, activity)
4. Trends detected (if ≥3 sessions)
5. Everything converted to embeddings
6. Stored in ChromaDB

---

### 2. **POST /query** - Retrieve Insights

**Purpose:** Ask questions about behavior and get AI-generated insights.

**Request:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are my behavior patterns?",
    "top_k": 5
  }'
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
        "session_id": "session_1",
        "timestamp": "2026-04-08T14:30:00.000Z"
      }
    }
  ],
  "query": "What are my behavior patterns?",
  "insight": {
    "insight": "Your behavioral pattern: rapid scroller. You scroll through content very quickly with minimal engagement.",
    "supporting_evidence": [...],
    "confidence": 0.8,
    "pattern_type": "rapid scroller"
  }
}
```

**Query Examples:**
- "What are my behavior patterns?"
- "How is my attention span?"
- "Am I engaging with content?"
- "How much time do I spend?"
- "Give me suggestions to improve"

---

### 3. **GET /profile** - Generate Behavioral Persona

**Purpose:** Get comprehensive behavioral profile and archetype.

**Request:**
```bash
curl http://localhost:8000/profile
```

**Response:**
```json
{
  "status": "success",
  "message": "Profile generated successfully",
  "persona": {
    "archetype": "Quick-Scroll Engager",
    "summary": "You scroll quickly through content but engage with what catches your eye. You're decisive about what you like despite brief viewing times.",
    "strengths": [
      "High engagement - you actively curate your feed",
      "Intentional usage - you know what you like"
    ],
    "weaknesses": [
      "Low attention span - consider watching fewer, higher-quality reels"
    ],
    "metrics": {
      "attention_score": 0.25,
      "engagement_score": 0.65,
      "activity_level": 12.5,
      "total_reels": 150,
      "total_sessions": 5
    },
    "confidence": 0.5
  }
}
```

**Persona Archetypes:**
- **Engaged Curator** - High attention + high engagement
- **Passive Observer** - High attention + low engagement
- **Quick-Scroll Engager** - Low attention + high engagement
- **Rapid Scroller** - Low attention + low engagement + high activity
- **Casual Browser** - Low activity overall
- **High-Volume Consumer** - Very high activity
- **Balanced User** - Moderate across all metrics

---

## 🧠 Intelligence Layer Features

### 1. **Session Summaries**
- Total watch time
- Average watch time per reel
- Like ratio
- Reels count
- Session duration

### 2. **Behavioral Traits**
- **Attention Score** (0-1): Normalized watch time
- **Engagement Score** (0-1): Like ratio
- **Activity Level**: Reels per minute

### 3. **Trend Detection**
- Attention trends (increasing/decreasing/stable)
- Engagement trends
- Activity spikes
- Behavioral drift detection

### 4. **Insight Generation** (No LLM Required)

Rule-based reasoning that analyzes:
- Behavioral patterns
- Attention levels
- Engagement patterns
- Time usage
- Actionable suggestions

### 5. **Persona Generation**

Creates behavioral archetypes with:
- Archetype classification
- Natural language summary
- Strengths identification
- Areas for improvement
- Confidence score

---

## 🔄 Complete Data Flow

```
Instagram Events
    ↓
POST /ingest
    ↓
Feature Engineering
    ├─ Session Summaries
    ├─ Behavioral Traits
    └─ Trend Detection
    ↓
Text Generation
    ↓
Embedding (sentence-transformers)
    ↓
ChromaDB Storage
    ↓
POST /query → Semantic Search → Insight Generation
GET /profile → Persona Generation
```

---

## 🧪 Testing the System

### Step 1: Ingest Sample Data

```bash
# Session 1 - High engagement
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"reel_id": "r1", "username": "user1", "watch_time": 8.5, "liked": true, "timestamp": "2026-04-08T10:00:00Z", "session_id": "s1"},
      {"reel_id": "r2", "username": "user2", "watch_time": 7.2, "liked": true, "timestamp": "2026-04-08T10:01:00Z", "session_id": "s1"},
      {"reel_id": "r3", "username": "user3", "watch_time": 9.1, "liked": false, "timestamp": "2026-04-08T10:02:00Z", "session_id": "s1"}
    ]
  }'

# Session 2 - Low engagement
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"reel_id": "r4", "username": "user4", "watch_time": 2.1, "liked": false, "timestamp": "2026-04-08T11:00:00Z", "session_id": "s2"},
      {"reel_id": "r5", "username": "user5", "watch_time": 1.8, "liked": false, "timestamp": "2026-04-08T11:01:00Z", "session_id": "s2"},
      {"reel_id": "r6", "username": "user6", "watch_time": 2.5, "liked": false, "timestamp": "2026-04-08T11:02:00Z", "session_id": "s2"}
    ]
  }'
```

### Step 2: Query Insights

```bash
# General behavior
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are my behavior patterns?", "top_k": 5}'

# Attention analysis
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How is my attention span?", "top_k": 3}'

# Get suggestions
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Give me suggestions to improve", "top_k": 5}'
```

### Step 3: Get Profile

```bash
curl http://localhost:8000/profile
```

---

## 📊 Expected Results

After ingesting the sample data above, you should see:

**Query Response:**
- Insight about mixed behavior patterns
- Evidence from both sessions
- Confidence score

**Profile Response:**
- Archetype: "Balanced User" or "Exploratory User"
- Strengths and weaknesses identified
- Metrics showing variation between sessions

---

## 🔧 Configuration

All settings in `app/main.py`:
- **CORS**: Currently allows all origins (`*`)
- **Logging**: INFO level to stdout
- **Model**: `all-MiniLM-L6-v2` (384-dim embeddings)
- **ChromaDB**: Persists to `./chroma_db/`

---

## 📝 Logging

Watch the console for detailed logs:

```
2026-04-08 14:30:00 - app.api.ingest - INFO - Received batch with 3 events
2026-04-08 14:30:00 - app.api.ingest - INFO - Grouped into 1 sessions
2026-04-08 14:30:01 - app.services.embedding - INFO - Loading embedding model: all-MiniLM-L6-v2
2026-04-08 14:30:05 - app.services.vector_store - INFO - ChromaDB collection 'behavioral_memory' ready
2026-04-08 14:30:05 - app.api.ingest - INFO - Stored 2 embeddings in ChromaDB
```

---

## 🎯 Integration with AIMirror

### Chrome Extension → Engine

```javascript
// In background.js
fetch('http://localhost:8000/ingest', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({events: batchedEvents})
});
```

### Dashboard → Engine

```javascript
// Query insights
const response = await fetch('http://localhost:8000/query', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({query: "What are my patterns?", top_k: 5})
});

// Get profile
const profile = await fetch('http://localhost:8000/profile');
```

---

## ✅ Success Checklist

- [ ] Server starts without errors
- [ ] Health endpoint returns "healthy"
- [ ] Can ingest events successfully
- [ ] Embeddings stored in ChromaDB
- [ ] Query returns relevant results
- [ ] Insights generated correctly
- [ ] Profile shows persona archetype
- [ ] Trends detected after 3+ sessions

---

## 🚨 Troubleshooting

**Issue:** Model download fails
- **Solution:** Check internet connection, model downloads on first run

**Issue:** ChromaDB errors
- **Solution:** Delete `chroma_db/` folder and restart

**Issue:** No insights generated
- **Solution:** Need at least 1 session of data, try ingesting sample data

**Issue:** Profile returns "no_data"
- **Solution:** Ingest events first via `/ingest` endpoint

---

## 🔥 Next Steps

1. ✅ Start the engine
2. ✅ Ingest test data
3. ✅ Query for insights
4. ✅ Generate profile
5. 🔄 Integrate with Chrome extension
6. 🔄 Build dashboard visualizations
7. 🔄 Deploy to production

---

**Built for AIMirror - Your Behavioral Digital Twin**
