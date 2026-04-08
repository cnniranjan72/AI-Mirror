# ChromaDB Inspection Guide

## Quick Overview

Your ChromaDB contains **2 items** in the `behavioral_memory` collection:
- 1 session_summary
- 1 behavioral_traits

---

## Methods to Inspect ChromaDB

### Method 1: Use the Provided Script (Recommended)

```bash
python inspect_chroma.py
```

This shows:
- All collections
- Item counts
- Sample data
- Query examples
- Metadata details

---

### Method 2: Python Interactive

```python
import chromadb

# Connect to your database
client = chromadb.PersistentClient(path='./chroma_db')

# List collections
collections = client.list_collections()
print(collections)

# Get specific collection
collection = client.get_collection('behavioral_memory')

# Count items
count = collection.count()
print(f"Total items: {count}")

# Get all data
results = collection.get(include=['metadatas', 'documents'])
```

---

### Method 3: Command Line Quick Check

```bash
# Check if database exists
ls -la chroma_db/

# Check collection files
ls -la chroma_db/*/chroma.sqlite3
```

---

## Your Current Data

Based on the inspection:

### Collection: behavioral_memory
- **Total Items:** 2
- **Embedding Dimensions:** 384
- **Model:** all-MiniLM-L6-v2

### Item 1: Session Summary
```json
{
  "type": "session_summary",
  "session_id": "session_1",
  "timestamp": "2026-04-08T17:43:23.150562",
  "total_watch_time": 5.2,
  "reels_count": 1,
  "text": "User watched 1 reels with average watch time 5.2 seconds..."
}
```

### Item 2: Behavioral Traits
```json
{
  "type": "behavioral_traits",
  "session_id": "session_1", 
  "timestamp": "2026-04-08T17:43:23.150687",
  "attention_score": 0.087,
  "engagement_score": 1.0,
  "activity_level": 1.0,
  "text": "User behavioral traits: attention score 0.087..."
}
```

---

## Query Examples

### Query for Behavioral Traits
```python
results = collection.query(
    query_texts=["behavioral traits attention"],
    n_results=2
)
# Returns: behavioral_traits (distance: 0.741), session_summary (distance: 1.686)
```

### Query for Session Data
```python
results = collection.query(
    query_texts=["session summary watch time"],
    n_results=2
)
# Returns: session_summary (distance: 0.811), behavioral_traits (distance: 1.380)
```

---

## Database Structure

```
chroma_db/
  b46f82ab-4d7f-4fea-9ff5-def9b50dc154/  # Collection UUID
    chroma.sqlite3                      # Main database file
    link_lists.bin                      # Vector index
    onnx_models/                        # ML model cache
      all-MiniLM-L6-v2/                # Sentence transformer model
```

---

## Common Operations

### View All Items
```python
results = collection.get(include=['metadatas', 'documents', 'embeddings'])
for doc, meta in zip(results['documents'], results['metadatas']):
    print(f"Type: {meta['type']}")
    print(f"Text: {doc[:100]}...")
    print()
```

### Filter by Type
```python
# Get only behavioral traits
results = collection.get(
    where={"type": "behavioral_traits"},
    include=['metadatas', 'documents']
)
```

### Get Recent Items
```python
# Get items from specific session
results = collection.get(
    where={"session_id": "session_1"},
    include=['metadatas', 'documents']
)
```

---

## Reset Database

If you want to start fresh:

```bash
# Stop the server first, then:
rm -rf chroma_db/
rm -rf alignment_data/
rm -rf rl_data/
rm -rf chat_data/

# Restart server - fresh database
uvicorn app.main:app --reload
```

---

## Monitoring Growth

Track your database growth over time:

```python
collection = client.get_collection('behavioral_memory')
count = collection.count()
print(f"Database size: {count} items")

# Group by type
results = collection.get(include=['metadatas'])
types = {}
for meta in results['metadatas']:
    doc_type = meta['type']
    types[doc_type] = types.get(doc_type, 0) + 1

print("Items by type:", types)
```

---

## Performance Tips

1. **Batch Queries:** Query multiple texts at once
2. **Limit Results:** Use `n_results` to limit returned items
3. **Filtering:** Use `where` clauses to reduce search space
4. **Include Only Needed:** Specify only needed fields in `include`

---

## Troubleshooting

### Database Locked
```bash
# Stop server, check for processes
lsof chroma_db/*/chroma.sqlite3
```

### Model Download Issues
```python
# Clear model cache
import chromadb
chromadb.utils.clear_cache()
```

### Empty Results
```python
# Check collection exists
try:
    collection = client.get_collection('behavioral_memory')
    print(f"Items: {collection.count()}")
except:
    print("Collection not found")
```

---

## Integration with Backend

The backend automatically:
- Creates embeddings on ingest
- Stores with metadata
- Queries for chat responses
- Retrieves for persona generation

Your database will grow as you:
1. Use Instagram with extension
2. Ingest more events
3. Generate more sessions
4. Chat with AI Mirror

---

**Current Status:** Database is healthy with 2 items from testing
**Next:** Add more data through Instagram usage for richer insights
