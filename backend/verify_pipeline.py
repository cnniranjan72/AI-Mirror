"""
AIMirror Pipeline Verification
Senior Backend Engineer Audit
"""

import asyncio
import json
from app.db.postgres import init_pool, fetch, fetchrow, execute, close_pool
from app.services.embedding import encode

print("=" * 80)
print("🔍 AIMIRROR PIPELINE VERIFICATION")
print("=" * 80)

async def main():
    await init_pool()
    
    # STEP 1: Database Connection Check
    print("\n[STEP 1] DATABASE CONNECTION CHECK")
    print("-" * 80)
    
    db_name = await fetchrow("SELECT current_database();")
    print(f"✓ Database: {db_name['current_database']}")
    
    extensions = await fetch("SELECT extname FROM pg_extension WHERE extname = 'vector';")
    print(f"✓ pgvector extension: {'INSTALLED' if extensions else 'NOT FOUND'}")
    
    # STEP 2: Events Table Validation
    print("\n[STEP 2] EVENTS TABLE VALIDATION")
    print("-" * 80)
    
    events = await fetch("SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;")
    print(f"✓ Total events in DB: {len(events)}")
    
    if events:
        print("\nSample events:")
        for e in events[:3]:
            print(f"  - ID: {e['id']}, User: {e['user_id']}, Reel: {e['reel_id']}")
            print(f"    Username: {e['username']}")
            print(f"    Caption: {e['caption'][:50] if e['caption'] else '(empty)'}...")
            print(f"    Hashtags: {e['hashtags']}")
            print(f"    Watch time: {e['watch_time']}s")
            print(f"    Timestamp: {e['timestamp']}")
            print()
    else:
        print("⚠ No events found in database")
    
    # STEP 3: Embeddings Table Validation
    print("\n[STEP 3] EMBEDDINGS TABLE VALIDATION")
    print("-" * 80)
    
    embed_count = await fetchrow("SELECT COUNT(*) AS c FROM embeddings;")
    print(f"✓ Total embeddings: {embed_count['c']}")
    
    embeddings = await fetch("SELECT id, text, embedding FROM embeddings LIMIT 5;")
    print(f"\nSample embeddings:")
    for emb in embeddings:
        vec_len = len(emb['embedding']) if emb['embedding'] else 0
        print(f"  - ID: {emb['id']}, Vector length: {vec_len}")
        print(f"    Text: {emb['text'][:50] if emb['text'] else '(empty)'}...")
        print()
    
    # STEP 4: Vector Search Test
    print("\n[STEP 4] VECTOR SEARCH TEST")
    print("-" * 80)
    
    if events and events[0]['caption']:
        test_caption = events[0]['caption']
        print(f"Test caption: {test_caption[:50]}...")
        
        query_emb = encode(test_caption)
        print(f"✓ Query embedding generated (length: {len(query_emb)})")
        
        # Simple vector similarity test
        vec_str = "[" + ",".join(map(str, query_emb)) + "]"
        results = await fetch(f"""
            SELECT id, text, embedding <-> '{vec_str}'::vector AS distance
            FROM embeddings
            ORDER BY distance
            LIMIT 3;
        """)
        
        print(f"\nTop 3 similar embeddings:")
        for r in results:
            print(f"  - ID: {r['id']}, Distance: {float(r['distance']):.4f}")
            print(f"    Text: {r['text'][:50] if r['text'] else '(empty)'}...")
            print()
    else:
        print("⚠ No captions available for vector search test")
    
    # STEP 5: Persona Table Validation
    print("\n[STEP 5] PERSONA TABLE VALIDATION")
    print("-" * 80)
    
    persona_count = await fetchrow("SELECT COUNT(*) AS c FROM personas;")
    print(f"✓ Total personas: {persona_count['c']}")
    
    personas = await fetch("SELECT * FROM personas LIMIT 5;")
    print(f"\nSample personas:")
    for p in personas:
        print(f"  - User: {p['user_id']}")
        print(f"    Persona label: {p['persona_label']}")
        print(f"    Interest vector: {p['interest_vector']}")
        print(f"    Behavior vector: {p['behavior_vector']}")
        print(f"    Confidence: {p['confidence']}")
        print()
    
    # STEP 6: Data Integrity Checks
    print("\n[STEP 6] DATA INTEGRITY CHECKS")
    print("-" * 80)
    
    # Check for empty captions
    empty_captions = await fetchrow("SELECT COUNT(*) AS c FROM events WHERE caption IS NULL OR caption = '';")
    print(f"✓ Events with empty captions: {empty_captions['c']}")
    
    # Check for zero watch time
    zero_watch = await fetchrow("SELECT COUNT(*) AS c FROM events WHERE watch_time = 0;")
    print(f"✓ Events with zero watch time: {zero_watch['c']}")
    
    # Check for empty embeddings
    empty_embeds = await fetchrow("SELECT COUNT(*) AS c FROM embeddings WHERE embedding IS NULL;")
    print(f"✓ Embeddings with NULL vector: {empty_embeds['c']}")
    
    # Check for users without personas
    users_without_persona = await fetchrow("""
        SELECT COUNT(DISTINCT user_id) AS c
        FROM events
        WHERE user_id NOT IN (SELECT user_id FROM personas);
    """)
    print(f"✓ Users without persona: {users_without_persona['c']}")
    
    await close_pool()
    
    print("\n" + "=" * 80)
    print("📊 VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
