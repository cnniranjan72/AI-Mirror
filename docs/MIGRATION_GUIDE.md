# AIMirror Architecture Migration Guide

## Overview

This guide explains how to migrate from the prototype architecture to the production-grade modular architecture while preserving all existing functionality.

## Migration Strategy

### Phase 1: Coexistence (Current)
- New modules coexist with old code
- No breaking changes
- Existing APIs continue to work
- Extension remains compatible

### Phase 2: Gradual Adoption (Next)
- Route new requests through new modules
- Old code remains as fallback
- Monitor performance and correctness
- Fix any issues

### Phase 3: Deprecation (Future)
- Mark old code as deprecated
- Add deprecation warnings
- Update documentation
- Provide migration examples

### Phase 4: Removal (Final)
- Remove deprecated code
- Clean up dependencies
- Update tests
- Final documentation update

## Current Status

**Phase 1 Complete**: New architecture implemented, existing code preserved

## Key Changes

### 1. Event Ingestion

#### Old Flow
```python
# behavioral-engine/app/api/ingest.py
@router.post("/ingest")
async def ingest_events(batch: EventBatch):
    # Direct processing
    sessions = group_events_by_session(batch.events)
    # ...
```

#### New Flow
```python
# backend/api/ingest.py
@router.post("/ingest")
async def ingest_events(batch: EventBatch):
    # Route through Behavior Gateway
    gateway = get_behavior_gateway()
    normalized_events = gateway.process_batch(
        payload={"events": batch.events},
        source=EventSource.CHROME_EXTENSION
    )
    # Continue processing with normalized events
```

#### Migration Steps
1. Keep old endpoint working
2. Add new gateway processing
3. Compare outputs
4. Switch to new flow when validated

### 2. Memory Storage

#### Old Approach
```python
# Single vector store for everything
vector_store.add_embedding(
    embedding=embedding,
    text=text,
    metadata={"type": "session_summary", ...}
)
```

#### New Approach
```python
# Separate memory modules
episodic_memory = get_episodic_memory()
await episodic_memory.store(memory_record)

semantic_memory = get_semantic_memory()
await semantic_memory.store(memory_record)

behavioral_memory = get_behavioral_memory()
await behavioral_memory.store_cluster(cluster)
```

#### Migration Steps
1. Create memory records from existing data
2. Store in appropriate memory modules
3. Update retrieval logic
4. Validate correctness

### 3. Persona Generation

#### Old Approach
```python
# app/services/persona.py
persona_generator = PersonaGenerator()
persona = persona_generator.generate_persona(summaries, traits_list)
```

#### New Approach
```python
# backend/engines/persona_engine.py
persona_engine = PersonaEngineV2()
persona = await persona_engine.generate_persona_v2(
    events=events,
    clusters=clusters,
    memories=memories
)
```

#### Migration Steps
1. Map old persona fields to new Persona contract
2. Add new fields with default values
3. Update API responses
4. Update dashboard to use new fields

### 4. Content Extraction

#### Old Approach
```python
# Direct Playwright usage
from playwright.async_api import async_playwright
async with async_playwright() as p:
    browser = await p.chromium.launch()
    # ...
```

#### New Approach
```python
# Provider pattern
from backend.providers import PlaywrightProvider

provider = PlaywrightProvider(config)
content = await provider.extract_content(url)
# Returns NormalizedContent
```

#### Migration Steps
1. Wrap existing extraction in provider
2. Return NormalizedContent
3. Update consumers
4. Add other providers as needed

## Data Migration

### Existing Data Compatibility

**Good News**: Existing data remains compatible

#### Vector Store Data
- Existing embeddings remain in ChromaDB
- Metadata preserved
- Can be gradually migrated to new memory modules

#### Database Data
- Existing PostgreSQL tables unchanged
- New tables added for new features
- No data loss

### Migration Script

```python
# scripts/migrate_to_new_architecture.py

async def migrate_vector_store():
    """Migrate existing vector store data to memory modules"""
    
    # Get existing data
    vector_store = get_vector_store()
    all_docs = vector_store.get_all()
    
    # Initialize memory modules
    episodic = get_episodic_memory()
    semantic = get_semantic_memory()
    behavioral = get_behavioral_memory()
    
    for doc in all_docs:
        metadata = doc["metadata"]
        doc_type = metadata.get("type")
        
        if doc_type == "session_summary":
            # Create episodic memory
            memory = MemoryRecord(
                memory_id=doc["id"],
                memory_type=MemoryType.EPISODIC,
                user_id="default",  # Update with actual user_id
                content=doc["text"],
                embedding=doc["embedding"],
                context=metadata,
                tags=[doc_type],
                timestamp=datetime.fromisoformat(metadata["timestamp"]),
                importance_score=0.5,
                metadata=metadata
            )
            await episodic.store(memory)
            
        elif doc_type == "behavioral_traits":
            # Create behavioral memory
            memory = MemoryRecord(
                memory_id=doc["id"],
                memory_type=MemoryType.BEHAVIORAL,
                user_id="default",
                content=doc["text"],
                embedding=doc["embedding"],
                context=metadata,
                tags=[doc_type],
                timestamp=datetime.fromisoformat(metadata["timestamp"]),
                importance_score=0.7,
                metadata=metadata
            )
            await behavioral.store(memory)
        
        # Store in semantic memory for search
        semantic_memory = MemoryRecord(
            memory_id=f"semantic_{doc['id']}",
            memory_type=MemoryType.SEMANTIC,
            user_id="default",
            content=doc["text"],
            embedding=doc["embedding"],
            context=metadata,
            tags=[doc_type],
            timestamp=datetime.fromisoformat(metadata["timestamp"]),
            importance_score=0.6,
            metadata=metadata
        )
        await semantic.store(semantic_memory)
    
    print(f"Migrated {len(all_docs)} documents to new memory modules")

# Run migration
if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate_vector_store())
```

## API Compatibility

### Existing Endpoints

All existing endpoints preserved:

#### POST /ingest
```python
# Old format still works
{
    "events": [
        {
            "reel_id": "123",
            "username": "creator",
            "caption": "...",
            "hashtags": ["ai", "tech"],
            "audio_info": "...",
            "watch_time": 15.5,
            "liked": true,
            "timestamp": "2026-06-11T17:43:00Z",
            "session_id": "sess_456"
        }
    ]
}
```

**Internally**: Converted to `BehaviorEvent` by gateway

#### POST /query
```python
# Old format still works
{
    "query": "What are my interests?",
    "top_k": 5
}
```

**Internally**: Routes through new memory modules

#### GET /profile
```python
# Old format still works
# Returns persona in old format for compatibility
```

**Internally**: Generated by PersonaEngineV2, converted to old format

### New Endpoints (Optional)

New endpoints for advanced features:

#### POST /api/v2/ingest
```python
# New format with source specification
{
    "source": "chrome_extension",
    "events": [...]
}
```

#### POST /api/v2/query
```python
# New format with memory type specification
{
    "query": "...",
    "memory_types": ["episodic", "semantic"],
    "filters": {...}
}
```

#### GET /api/v2/persona
```python
# Returns full Persona V2 object
{
    "persona_id": "...",
    "archetype": "...",
    "interest_graph": {...},
    "behavior_graph": {...},
    ...
}
```

## Extension Compatibility

### No Changes Required

Chrome extension continues to work without any changes:

1. **Same endpoint**: POST /ingest
2. **Same format**: EventBatch with BehavioralEvent array
3. **Same response**: IngestResponse

### Behind the Scenes

1. Extension sends events to POST /ingest
2. Behavior Gateway normalizes to BehaviorEvent
3. Knowledge Consolidation Engine processes
4. Memory modules store appropriately
5. Response sent back to extension

## Testing Strategy

### 1. Unit Tests

Test each new module in isolation:

```python
# tests/test_behavior_gateway.py
def test_normalize_extension_event():
    gateway = BehaviorGateway()
    raw_event = {
        "reel_id": "123",
        "username": "creator",
        # ...
    }
    normalized = gateway.ingest_from_extension({"events": [raw_event]})
    assert len(normalized) == 1
    assert isinstance(normalized[0], BehaviorEvent)
```

### 2. Integration Tests

Test module interactions:

```python
# tests/test_integration.py
async def test_end_to_end_ingestion():
    # Send event through gateway
    gateway = get_behavior_gateway()
    events = gateway.process_batch(payload, EventSource.CHROME_EXTENSION)
    
    # Verify storage in memory modules
    episodic = get_episodic_memory()
    count = await episodic.count()
    assert count > 0
```

### 3. Regression Tests

Ensure old functionality still works:

```python
# tests/test_regression.py
async def test_old_ingest_endpoint():
    # Test old endpoint format
    response = await client.post("/ingest", json=old_format_batch)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

### 4. Performance Tests

Ensure no performance degradation:

```python
# tests/test_performance.py
async def test_ingestion_latency():
    start = time.time()
    await ingest_events(batch)
    latency = time.time() - start
    assert latency < 1.0  # Should complete in < 1 second
```

## Rollback Plan

If issues arise, rollback is straightforward:

### Step 1: Disable New Modules
```python
# config.py
USE_NEW_ARCHITECTURE = False
```

### Step 2: Route to Old Code
```python
# api/ingest.py
if USE_NEW_ARCHITECTURE:
    # Use new flow
    gateway = get_behavior_gateway()
    # ...
else:
    # Use old flow
    sessions = group_events_by_session(batch.events)
    # ...
```

### Step 3: Monitor
- Check error rates
- Check response times
- Check data integrity

### Step 4: Investigate
- Review logs
- Identify root cause
- Fix issues

### Step 5: Re-enable
- Deploy fix
- Enable new architecture
- Monitor again

## Common Issues

### Issue 1: Import Errors

**Problem**: `ModuleNotFoundError: No module named 'backend.shared'`

**Solution**: Update Python path
```python
import sys
sys.path.insert(0, '/path/to/AI-Mirror')
```

### Issue 2: Type Errors

**Problem**: Pydantic validation errors

**Solution**: Ensure all fields match contract definitions
```python
# Check contract in backend/shared/contracts.py
# Ensure data matches expected types
```

### Issue 3: Memory Module Not Found

**Problem**: Singleton not initialized

**Solution**: Call getter function
```python
# Wrong
memory = EpisodicMemory()

# Correct
memory = get_episodic_memory()
```

## Next Steps

1. **Review Architecture**: Read `Architecture.md`
2. **Run Tests**: Verify existing pipeline works
3. **Gradual Adoption**: Start using new modules
4. **Monitor**: Watch for issues
5. **Iterate**: Fix problems, improve design

## Support

For questions or issues:
1. Check documentation in `docs/`
2. Review code comments
3. Run tests to verify behavior
4. Create issue if problem persists

## Conclusion

This migration preserves all existing functionality while providing a solid foundation for future development. The modular architecture enables:

- Easy addition of new features
- Better testing and maintenance
- Clear separation of concerns
- Scalability and extensibility

Take your time with the migration. The architecture supports gradual adoption, so you can migrate piece by piece while keeping the system running.
