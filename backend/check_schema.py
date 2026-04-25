"""Check database schema"""
import asyncio
from app.db.postgres import init_pool, fetch, close_pool

async def main():
    await init_pool()
    
    # Check tables
    tables = await fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    print("Tables:", [r['table_name'] for r in tables])
    
    # Check behavioral_memory columns (old schema)
    if any(t['table_name'] == 'behavioral_memory' for t in tables):
        cols = await fetch("SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_name='behavioral_memory'")
        print("\nbehavioral_memory columns:")
        for c in cols:
            print(f"  {c['column_name']}: {c['data_type']} (default: {c['column_default']})")
        
        # Check constraints
        cons = await fetch("SELECT conname, contype, pg_get_constraintdef(oid) as def FROM pg_constraint WHERE conrelid='behavioral_memory'::regclass")
        print("\nbehavioral_memory constraints:")
        for c in cons:
            print(f"  {c['conname']}: {c['contype']} - {c['def']}")
    
    # Check embeddings columns (new schema)
    if any(t['table_name'] == 'embeddings' for t in tables):
        cols = await fetch("SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_name='embeddings'")
        print("\nembeddings columns:")
        for c in cols:
            print(f"  {c['column_name']}: {c['data_type']} (default: {c['column_default']})")
    
    await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
