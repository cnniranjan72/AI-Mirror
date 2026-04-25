"""Drop old behavioral-engine tables to avoid conflicts with new backend schema"""
import asyncio
from app.db.postgres import init_pool, execute, fetch, close_pool

async def main():
    await init_pool()
    
    # Drop old behavioral-engine tables
    old_tables = [
        'chat_history',
        'sessions', 
        'behavioral_memory',
        'user_profiles',
        'recent_behavioral_data'
    ]
    
    for table in old_tables:
        try:
            await execute(f'DROP TABLE IF EXISTS {table} CASCADE')
            print(f"Dropped: {table}")
        except Exception as e:
            print(f"Error dropping {table}: {e}")
    
    # Verify new tables exist
    tables = await fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    print("\nRemaining tables:", [r['table_name'] for r in tables])
    
    await close_pool()
    print("\n✅ Old schema cleaned up")

if __name__ == "__main__":
    asyncio.run(main())
