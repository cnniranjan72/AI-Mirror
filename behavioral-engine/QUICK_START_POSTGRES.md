# Quick Start: PostgreSQL Migration

Fast-track guide to get AIMirror running with Neon PostgreSQL.

---

## 🚀 5-Minute Setup

### 1. Get Neon Connection String

```bash
# Sign up at https://neon.tech
# Create project → Copy connection string
# Example: postgresql://user:pass@ep-name.region.aws.neon.tech/dbname
```

### 2. Set Environment Variable

```bash
# Create .env file
echo "DATABASE_URL=your_neon_connection_string_here" > .env
```

### 3. Install Dependencies

```bash
cd behavioral-engine
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
# Run migration
python -c "
import asyncio
from app.database import initialize_database
asyncio.run(initialize_database())
print('✅ Database initialized!')
"
```

### 5. Test Migration

```bash
# Run test suite
python test_migration.py
```

### 6. Start Server

```bash
uvicorn app.main:app --host localhost --port 8000 --reload
```

---

## ✅ Verification

Visit http://localhost:8000/docs to see API documentation.

Test health endpoint:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": {
    "connected": true,
    "pgvector_enabled": true
  }
}
```

---

## 📝 Key Changes

### All endpoints now require `user_id`

**Before (ChromaDB):**
```python
POST /ingest
{
  "reel_id": "123",
  "watch_time": 15
}
```

**After (PostgreSQL):**
```python
POST /ingest?user_id=user_123
{
  "reel_id": "123",
  "watch_time": 15
}
```

### Import Changes

**Old:**
```python
from app.services.vector_store import get_vector_store
```

**New:**
```python
from app.services.vector_store_postgres import get_vector_store
```

---

## 🔧 Common Issues

### "Cannot connect to database"
- Check DATABASE_URL in .env
- Verify Neon project is active
- Check network connectivity

### "Extension 'vector' does not exist"
- Enable pgvector in Neon SQL Editor:
  ```sql
  CREATE EXTENSION vector;
  ```

### "Table does not exist"
- Run migration script:
  ```bash
  python -c "import asyncio; from app.database import initialize_database; asyncio.run(initialize_database())"
  ```

---

## 📚 Full Documentation

See `MIGRATION_GUIDE.md` for complete details.

---

## 🎯 Production Deployment

1. **Environment Variables:**
   ```bash
   DATABASE_URL=postgresql://...
   OPENAI_API_KEY=sk-...
   ```

2. **Connection Pool:**
   ```python
   # Adjust in app/database.py
   await init_db_pool(min_size=10, max_size=50)
   ```

3. **Monitoring:**
   - Use Neon dashboard for query performance
   - Monitor connection pool usage
   - Set up alerts for errors

---

**You're ready to go!** 🚀
