"""Check latest embedding dimensions"""
import asyncio
import json
from app.db.postgres import init_pool, fetch, close_pool

async def main():
    await init_pool()
    
    # Get latest embeddings - fetch the raw embedding data
    rows = await fetch("""
        SELECT id, text, embedding
        FROM embeddings
        ORDER BY id DESC
        LIMIT 5;
    """)
    
    print("Latest embeddings:")
    for r in rows:
        vec = r['embedding']
        # Parse the string representation back to a list
        if isinstance(vec, str):
            try:
                vec = json.loads(vec.replace("'", '"'))
            except:
                vec = []
        vec_len = len(vec) if vec else 0
        print(f"  ID: {r['id']}, Vector length: {vec_len}")
        print(f"    Text: {r['text'][:50] if r['text'] else '(empty)'}...")
        if vec_len > 0:
            print(f"    First 5 values: {vec[:5]}")
            print(f"    Type: {type(vec)}")
    
    # Get latest persona
    personas = await fetch("""
        SELECT user_id, persona_label, interest_vector, confidence
        FROM personas
        ORDER BY created_at DESC
        LIMIT 3;
    """)
    
    print("\nLatest personas:")
    for p in personas:
        print(f"  User: {p['user_id']}, Label: {p['persona_label']}")
        print(f"    Interest vector: {p['interest_vector']}")
        print(f"    Confidence: {p['confidence']}")
    
    await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
