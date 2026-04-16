# ChromaDB to Neon PostgreSQL Migration Guide

Complete guide for migrating AIMirror from ChromaDB to Neon PostgreSQL with pgvector.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Neon Setup](#neon-setup)
3. [Database Schema Setup](#database-schema-setup)
4. [Backend Migration](#backend-migration)
5. [Testing](#testing)
6. [Cleanup](#cleanup)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- Python 3.8+
- PostgreSQL client (optional, for manual queries)
- Neon account (free tier available)

### Required Python Packages
```bash
pip install asyncpg psycopg2-binary pgvector
```

---

## Neon Setup

### 1. Create Neon Project

1. Go to https://neon.tech
2. Sign up or log in
3. Click "Create Project"
4. Choose a name (e.g., "aimirror-production")
5. Select region closest to your users
6. Click "Create Project"

### 2. Enable pgvector Extension

In the Neon SQL Editor:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Get Connection String

1. In your Neon dashboard, click "Connection Details"
2. Copy the connection string (it looks like):
   ```
   postgresql://username:password@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

### 4. Update Environment Variables

Create or update `.env` file:

```bash
# Replace with your Neon connection string
DATABASE_URL=postgresql://username:password@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require

# Optional: OpenAI API key for chat features
OPENAI_API_KEY=your_openai_key_here
```

---

## Database Schema Setup

### 1. Run Migration Script

```bash
cd behavioral-engine

# Option 1: Using psql
psql $DATABASE_URL -f migrations/001_initial_schema.sql

# Option 2: Using Python
python -c "
import asyncio
from app.database import initialize_database
asyncio.run(initialize_database())
"
```

### 2. Verify Schema

```sql
-- Check tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

-- Expected tables:
-- behavioral_memory
-- chat_history
-- user_profiles
-- sessions

-- Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check indexes
SELECT indexname, tablename FROM pg_indexes 
WHERE schemaname = 'public';
```

---

## Backend Migration

### 1. Install New Dependencies

```bash
cd behavioral-engine
pip install -r requirements.txt
```

### 2. Update Import Statements

Replace old ChromaDB imports with PostgreSQL versions:

**Old (ChromaDB):**
```python
from app.services.vector_store import get_vector_store
from app.services.rag_engine import get_rag_engine
```

**New (PostgreSQL):**
```python
from app.services.vector_store_postgres import get_vector_store
from app.services.rag_engine_postgres import get_rag_engine
from app.services.ingest_service_postgres import get_ingest_service
```

### 3. Update API Endpoints

All API endpoints now require `user_id` parameter.

**Example: Ingest Endpoint**

```python
# Old
@app.post("/ingest")
async def ingest_event(event: BehavioralEvent):
    # ...

# New
@app.post("/ingest")
async def ingest_event(event: BehavioralEvent, user_id: str):
    ingest_service = await get_ingest_service()
    doc_id = await ingest_service.ingest_behavioral_event(
        user_id=user_id,
        event_data=event.dict()
    )
    return {"doc_id": doc_id}
```

**Example: Chat Endpoint**

```python
# Old
@app.post("/chat")
async def chat(query: str):
    # ...

# New
@app.post("/chat")
async def chat(query: str, user_id: str):
    rag_engine = await get_rag_engine()
    response = await rag_engine.generate_response(
        user_id=user_id,
        query=query
    )
    return response
```

### 4. Update Main Application

**app/main.py:**

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.database import init_db_pool, close_db_pool, initialize_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db_pool()
    await initialize_database()
    yield
    # Shutdown
    await close_db_pool()

app = FastAPI(lifespan=lifespan)

# Import routes
from app.api import ingest, query, profile, chat

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(profile.router)
app.include_router(chat.router)
```

---

## Testing

### 1. Test Database Connection

```python
import asyncio
from app.database import check_db_health

async def test_connection():
    health = await check_db_health()
    print(health)

asyncio.run(test_connection())
```

Expected output:
```json
{
  "status": "healthy",
  "connected": true,
  "pgvector_enabled": true,
  "tables_exist": ["behavioral_memory", "chat_history", "user_profiles", "sessions"],
  "pool_size": 5,
  "pool_free": 5
}
```

### 2. Test Data Insertion

```python
import asyncio
from app.services.ingest_service_postgres import get_ingest_service

async def test_insert():
    service = await get_ingest_service()
    
    # Test event
    event = {
        "reel_id": "test_123",
        "username": "test_user",
        "watch_time": 15.5,
        "liked": True,
        "caption": "Test caption",
        "hashtags": ["test", "demo"],
        "session_id": "session_123"
    }
    
    doc_id = await service.ingest_behavioral_event(
        user_id="user_123",
        event_data=event
    )
    
    print(f"Inserted document: {doc_id}")

asyncio.run(test_insert())
```

### 3. Test Similarity Search

```python
import asyncio
from app.services.vector_store_postgres import get_vector_store
from app.services.embedding import get_embedding_service

async def test_query():
    vector_store = await get_vector_store()
    embedding_service = get_embedding_service()
    
    # Generate query embedding
    query = "What are my watching patterns?"
    query_embedding = embedding_service.encode(query)
    
    # Search
    results = await vector_store.query(
        user_id="user_123",
        query_embedding=query_embedding,
        top_k=5
    )
    
    print(f"Found {len(results['documents'][0])} results")
    for i, doc in enumerate(results['documents'][0]):
        print(f"{i+1}. {doc[:100]}...")
        print(f"   Distance: {results['distances'][0][i]:.4f}")

asyncio.run(test_query())
```

### 4. Test Chat Endpoint

```bash
# Start server
uvicorn app.main:app --host localhost --port 8000

# Test chat
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are my behavioral patterns?",
    "user_id": "user_123"
  }'
```

### 5. Test Full Pipeline

```python
import asyncio
from app.services.ingest_service_postgres import get_ingest_service
from app.services.rag_engine_postgres import get_rag_engine

async def test_full_pipeline():
    # 1. Ingest data
    ingest_service = await get_ingest_service()
    
    events = [
        {
            "type": "behavioral_event",
            "reel_id": f"reel_{i}",
            "username": f"user_{i % 3}",
            "watch_time": 10 + i * 2,
            "liked": i % 2 == 0,
            "session_id": "session_test"
        }
        for i in range(10)
    ]
    
    doc_ids = await ingest_service.ingest_batch(
        user_id="test_user",
        events=events
    )
    print(f"Ingested {len(doc_ids)} events")
    
    # 2. Query with RAG
    rag_engine = await get_rag_engine()
    response = await rag_engine.generate_response(
        user_id="test_user",
        query="What content do I watch most?"
    )
    
    print("\nRAG Response:")
    print(response['fused_context'])

asyncio.run(test_full_pipeline())
```

---

## Cleanup

### 1. Remove ChromaDB Files

```bash
# Remove ChromaDB directory
rm -rf behavioral-engine/chroma_db

# Remove old vector store (keep as backup initially)
# mv app/services/vector_store.py app/services/vector_store_old.py
```

### 2. Update Imports Across Codebase

Search and replace:
- `from app.services.vector_store import` → `from app.services.vector_store_postgres import`
- `from app.services.rag_engine import` → `from app.services.rag_engine_postgres import`

### 3. Remove ChromaDB from requirements.txt

Already done - ChromaDB has been removed and replaced with:
- `asyncpg==0.29.0`
- `psycopg2-binary==2.9.9`
- `pgvector==0.2.5`

---

## Performance Optimization

### 1. Connection Pooling

Already configured in `app/database.py`:
- Min connections: 5
- Max connections: 20

Adjust based on load:
```python
await init_db_pool(min_size=10, max_size=50)
```

### 2. Batch Operations

Use batch inserts for better performance:
```python
# Instead of multiple single inserts
for event in events:
    await ingest_service.ingest_behavioral_event(user_id, event)

# Use batch insert
await ingest_service.ingest_batch(user_id, events)
```

### 3. Index Optimization

For large datasets, tune IVFFlat index:
```sql
-- Adjust lists parameter based on dataset size
-- Rule of thumb: lists = sqrt(total_rows)
DROP INDEX IF EXISTS idx_behavioral_memory_embedding;
CREATE INDEX idx_behavioral_memory_embedding ON behavioral_memory 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1000);
```

### 4. Query Optimization

Add composite indexes for common queries:
```sql
CREATE INDEX idx_user_type_created ON behavioral_memory(user_id, type, created_at DESC);
```

---

## Troubleshooting

### Issue: "relation 'behavioral_memory' does not exist"

**Solution:** Run migration script
```bash
psql $DATABASE_URL -f migrations/001_initial_schema.sql
```

### Issue: "extension 'vector' does not exist"

**Solution:** Enable pgvector in Neon dashboard or run:
```sql
CREATE EXTENSION vector;
```

### Issue: "connection pool exhausted"

**Solution:** Increase pool size
```python
await init_db_pool(min_size=10, max_size=50)
```

### Issue: Slow similarity search

**Solution:** 
1. Check if index exists:
   ```sql
   SELECT * FROM pg_indexes WHERE tablename = 'behavioral_memory';
   ```
2. Rebuild index with more lists:
   ```sql
   DROP INDEX idx_behavioral_memory_embedding;
   CREATE INDEX idx_behavioral_memory_embedding ON behavioral_memory 
   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1000);
   ```

### Issue: "asyncpg.exceptions.UndefinedColumnError"

**Solution:** Check column names match schema. Common issues:
- `user_id` vs `userId`
- `created_at` vs `createdAt`

### Issue: Import errors after migration

**Solution:** Update all imports to use new PostgreSQL modules:
```python
# Update these imports
from app.services.vector_store_postgres import get_vector_store
from app.services.rag_engine_postgres import get_rag_engine
from app.services.ingest_service_postgres import get_ingest_service
```

---

## Multi-User Support

All queries now filter by `user_id`:

```python
# Automatic user isolation
results = await vector_store.query(
    user_id="user_123",  # Only returns this user's data
    query_embedding=embedding,
    top_k=5
)
```

### User Data Management

```python
# Get user's document count
count = await vector_store.get_collection_count(user_id="user_123")

# Delete user's data (GDPR compliance)
deleted = await vector_store.delete_user_data(user_id="user_123")
```

---

## Production Checklist

- [ ] Neon project created
- [ ] pgvector extension enabled
- [ ] Migration script executed
- [ ] Tables and indexes created
- [ ] Environment variables set
- [ ] Dependencies installed
- [ ] Database connection tested
- [ ] Data insertion tested
- [ ] Similarity search tested
- [ ] Chat endpoint tested
- [ ] ChromaDB files removed
- [ ] All imports updated
- [ ] Performance optimized
- [ ] Monitoring configured

---

## Next Steps

1. **Monitor Performance:** Use Neon dashboard to monitor query performance
2. **Scale as Needed:** Upgrade Neon plan for more resources
3. **Backup Strategy:** Configure automated backups in Neon
4. **Security:** Review connection string security and access controls
5. **Documentation:** Update API documentation with user_id requirements

---

## Support

- **Neon Documentation:** https://neon.tech/docs
- **pgvector Documentation:** https://github.com/pgvector/pgvector
- **asyncpg Documentation:** https://magicstack.github.io/asyncpg/

---

**Migration Complete!** 🎉

Your AIMirror system is now running on Neon PostgreSQL with pgvector, providing:
- ✅ Multi-user support with user isolation
- ✅ Scalable vector similarity search
- ✅ Production-ready database infrastructure
- ✅ Better performance and reliability
