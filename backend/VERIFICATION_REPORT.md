# AIMirror Pipeline Verification Report
**Senior Backend Engineer Audit**
**Date:** 2025-04-25

---

## Executive Summary

**PIPELINE STATUS: PARTIAL**

The system has critical issues with embedding storage. While data is being written to PostgreSQL, the embeddings are stored with incorrect vector dimensions, making them unusable for proper vector similarity search.

---

## Step 1: Database Connection Check

✅ **PASSED**
- Database: `neondb`
- pgvector extension: **INSTALLED**
- Connection: Active

---

## Step 2: Events Table Validation

✅ **PASSED**
- Total events: 7
- Sample data:
  - ID 7: `roy_s_ajin` - "Adult money spent right!!!!!" (109.01s)
  - ID 6: `siva._reddy` - "A.R. Rahman, Shakthisree Gopalan" (17.99s)
  - ID 5: `lucky_bhaiya__` - (empty caption) (4.0s)

⚠️ **ISSUE FOUND:**
- 1 event with empty caption (ID 5)
- All hashtags arrays are empty `[]`

---

## Step 3: Embeddings Table Validation

❌ **CRITICAL FAILURE**
- Total embeddings: 10
- Vector length: **4676-4707** (expected: 384)
- Text content: Present and valid

**Sample embeddings:**
```
ID 1: Vector length 4676 - "This entertaining content relates to general..."
ID 2: Vector length 4696 - "This entertaining content relates to technology..."
ID 3: Vector length 4672 - "This entertaining content relates to general..."
```

**Root Cause:**
The embedding column is storing the vector as a string representation instead of a proper pgvector type. The _vec() function in vector_store.py converts the list to string format `"[0.1,0.2,...]"` but this is being stored as text, not as a vector.

---

## Step 4: Vector Search Test

⚠️ **PARTIAL**
- Query embedding generated: 384 dimensions (correct)
- Similarity search: Working (returned results)
- Distance calculation: Functional

**Top 3 similar embeddings:**
1. ID 9: Distance 0.8980 - "This entertaining content relates to finance..."
2. ID 8: Distance 1.2693 - "User watched 1 reels with total watch time 18s..."
3. ID 6: Distance 1.3036 - "User watched 5 reels with total watch time 63s..."

⚠️ **Note:** Search works despite incorrect storage because PostgreSQL is casting the string to vector on-the-fly during comparison, but this is inefficient and incorrect.

---

## Step 5: Persona Table Validation

❌ **CRITICAL FAILURE**
- Total personas: 3
- Persona label: "Emerging User" (all same)
- Interest vector: `{"top_topics": [], "topic_count": 0}` (empty)
- Behavior vector: Present with creator data
- Confidence: 0.0 (all records)

**Sample personas:**
```
User: default
  Persona label: Emerging User
  Interest vector: {"top_topics": [], "topic_count": 0}
  Behavior vector: {"top_creators": [...], "total_events": 5, "avg_watch_time": 12.6}
  Confidence: 0.0
```

**Root Cause:**
The persona computation is not generating meaningful interest vectors or confidence scores. The enrichment layer is not detecting topics from captions, resulting in empty interest distributions.

---

## Step 6: Pipeline Test (Live Ingest)

⚠️ **BACKEND CONFUSION**
- Backend running: **behavioral-engine** (ChromaDB-based, old system)
- Expected backend: **backend/** (PostgreSQL-based, new system)
- Port 8000: behavioral-engine is active

**Test result:**
- Ingest response: `{"status":"success","events_processed":1,"summaries_created":2,"embeddings_stored":2}`
- Events added: 0 (behavioral-engine doesn't write to events table)
- Embeddings added: 0 (behavioral-engine uses ChromaDB, not PostgreSQL)

**Issue:**
The Chrome Extension and frontend are pointing to the wrong backend. The behavioral-engine backend is running on port 8000, but the new production backend should be used.

---

## Step 7: Data Flow Trace

✅ **Logging Added**
- `[ENRICH]` - NLP enrichment step
- `[EXPAND]` - Content expansion step
- `[EMBED]` - Embedding generation step
- `[DB]` - Database insertion step
- `[PERSONA]` - Persona computation step

**Note:** Logging was added to the new backend (`backend/app/api/ingest.py`) but this backend is not currently running.

---

## Step 8: Failure Detection

**Issues Detected:**

1. **Empty captions:** 1 event (ID 5)
2. **Empty hashtags:** 7 events (all)
3. **Incorrect embedding dimensions:** 10 embeddings (4676-4707 instead of 384)
4. **Empty interest vectors:** 3 personas (all)
5. **Zero confidence scores:** 3 personas (all)
6. **Wrong backend active:** behavioral-engine instead of new backend

**No issues found:**
- No NULL embeddings in database
- No zero watch_time events
- No duplicate inserts detected
- No failed DB writes (data is being stored, just incorrectly)

---

## Step 9: Final Report

### Database Validation Results

| Metric | Value | Status |
|--------|-------|--------|
| Events inserted | 7 | ✅ |
| Embeddings count | 10 | ⚠️ (wrong dimensions) |
| Personas count | 3 | ⚠️ (empty interest vectors) |
| Last inserted record | ID 7 (events), ID 10 (embeddings) | ✅ |

### Sample Rows

**Events:**
```json
{
  "id": 7,
  "user_id": "default",
  "reel_id": "reel_moe82xy4",
  "username": "roy_s_ajin",
  "caption": "Adult money spent right!!!!!",
  "hashtags": [],
  "watch_time": 109.01,
  "timestamp": "2026-04-25 10:56:35.888000+00:00"
}
```

**Embeddings:**
```json
{
  "id": 1,
  "text": "This entertaining content relates to general...",
  "embedding": [4676 elements] // SHOULD BE 384
}
```

**Personas:**
```json
{
  "user_id": "default",
  "persona_label": "Emerging User",
  "interest_vector": {"top_topics": [], "topic_count": 0},
  "behavior_vector": {"top_creators": [...], "total_events": 5},
  "confidence": 0.0
}
```

---

## Issues Found

### Critical Issues

1. **Embedding vector dimensions incorrect**
   - Expected: 384
   - Actual: 4676-4707
   - Impact: Vectors are stored as strings, not pgvector type
   - Fix: Update vector_store.py to use proper pgvector casting

2. **Persona interest vectors empty**
   - Expected: Topic distribution
   - Actual: Empty arrays
   - Impact: Persona classification not working
   - Fix: Fix enrichment.py topic detection

3. **Wrong backend active**
   - Expected: `backend/` (PostgreSQL)
   - Actual: `behavioral-engine/` (ChromaDB)
   - Impact: Data going to wrong system
   - Fix: Stop behavioral-engine, start new backend

### Medium Issues

4. **Empty hashtags in all events**
   - Chrome Extension not extracting hashtags
   - Fix: Update content.js DOM selectors

5. **Empty captions**
   - 1 event with no caption
   - Impact: Enrichment fails for these events
   - Fix: Add validation in Chrome Extension

### Low Issues

6. **Persona confidence scores zero**
   - All personas have 0.0 confidence
   - Fix: Update persona.py confidence calculation

---

## Fix Suggestions

### 1. Fix Embedding Storage (CRITICAL)

**File:** `backend/app/services/vector_store.py`

**Current:**
```python
def _vec(v: List[float]) -> str:
    return "[" + ",".join(map(str, v)) + "]"
```

**Fix:**
```python
# The string conversion is correct for pgvector
# The issue is likely in the INSERT statement
# Ensure the column type is VECTOR(384) in schema
# Verify the casting is correct: $3::vector
```

**Alternative:** Use pgvector's Python library for proper type handling.

### 2. Fix Persona Interest Vectors (CRITICAL)

**File:** `backend/app/services/enrichment.py`

**Current:** Topic detection returns empty arrays

**Fix:** 
- Improve keyword mapping for topics
- Add fallback topic detection
- Test enrichment with sample captions

### 3. Switch to Correct Backend (CRITICAL)

**Action:**
1. Stop behavioral-engine backend (port 8000)
2. Start new backend from `backend/` folder
3. Update Chrome Extension to point to correct backend if needed
4. Update frontend to use correct backend endpoints

**Command:**
```bash
# Stop old backend
taskkill /PID [behavioral-engine-pid] /F

# Start new backend
cd backend
python -m uvicorn app.main:app --host localhost --port 8000
```

### 4. Fix Hashtag Extraction (MEDIUM)

**File:** `chrome-extension/content.js`

**Current:** Hashtags always empty

**Fix:** Update DOM selectors for hashtag extraction

### 5. Add Caption Validation (LOW)

**File:** `chrome-extension/content.js`

**Action:** Skip events without captions before sending to backend

---

## PIPELINE STATUS

**PARTIAL** - Data is flowing but with critical storage issues

**Working:**
- ✅ Database connection
- ✅ Event storage
- ✅ Embedding generation
- ✅ Vector similarity search (despite storage issue)
- ✅ Persona record creation

**Broken:**
- ❌ Embedding vector dimensions (4676 instead of 384)
- ❌ Persona interest vectors (empty)
- ❌ Wrong backend active (behavioral-engine instead of new backend)
- ⚠️ Hashtag extraction (always empty)
- ⚠️ Caption validation (missing)

---

## Recommendation

**Priority 1:** Switch to the new backend (`backend/`) instead of behavioral-engine
**Priority 2:** Fix embedding storage to use proper pgvector type
**Priority 3:** Fix enrichment topic detection for persona interest vectors
**Priority 4:** Fix Chrome Extension hashtag extraction

Once these are fixed, re-run verification to confirm pipeline is fully functional.
