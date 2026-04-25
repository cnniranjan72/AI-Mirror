"""Test live ingest to verify pipeline"""
import asyncio
import json
from app.db.postgres import init_pool, fetch, fetchrow, close_pool

async def main():
    await init_pool()
    
    # Check current state before test
    events_before = await fetchrow("SELECT COUNT(*) AS c FROM events;")
    embeds_before = await fetchrow("SELECT COUNT(*) AS c FROM embeddings;")
    
    print(f"BEFORE TEST:")
    print(f"  Events: {events_before['c']}")
    print(f"  Embeddings: {embeds_before['c']}")
    
    # Test data
    test_event = {
        "user_id": "test_verification",
        "events": [{
            "reel_id": "test_reel_001",
            "username": "test_user",
            "caption": "This is a test caption about technology and coding #tech #code",
            "hashtags": ["#tech", "#code"],
            "audio": "Test Audio",
            "watch_time": 15.5,
            "timestamp": "2024-01-15T10:30:00Z",
            "session_id": "test_session_001"
        }]
    }
    
    # Send to backend
    import requests
    response = requests.post(
        "http://localhost:8000/ingest",
        json=test_event,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nINGEST RESPONSE:")
    print(f"  Status: {response.status_code}")
    print(f"  Body: {response.text[:500]}")
    
    # Check state after test
    await asyncio.sleep(1)  # Wait for processing
    
    events_after = await fetchrow("SELECT COUNT(*) AS c FROM events;")
    embeds_after = await fetchrow("SELECT COUNT(*) AS c FROM embeddings;")
    
    print(f"\nAFTER TEST:")
    print(f"  Events: {events_after['c']} (+{events_after['c'] - events_before['c']})")
    print(f"  Embeddings: {embeds_after['c']} (+{embeds_after['c'] - embeds_before['c']})")
    
    # Check the new embedding vector length
    new_embed = await fetch("""
        SELECT id, text, embedding
        FROM embeddings
        ORDER BY id DESC
        LIMIT 1;
    """)
    
    if new_embed:
        vec_len = len(new_embed[0]['embedding']) if new_embed[0]['embedding'] else 0
        print(f"\nNEW EMBEDDING:")
        print(f"  ID: {new_embed[0]['id']}")
        print(f"  Vector length: {vec_len}")
        print(f"  Expected: 384")
        print(f"  Status: {'✓ OK' if vec_len == 384 else '✗ WRONG'}")
    
    await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
