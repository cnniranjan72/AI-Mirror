"""
Quick verification script for PostgreSQL setup
"""

import asyncio
import sys
from app.database import check_db_health, get_db_pool

async def verify_setup():
    """Verify database setup"""
    print("=" * 60)
    print("PostgreSQL Setup Verification")
    print("=" * 60)
    
    try:
        # Check database health
        print("\n1. Checking database connection...")
        health = await check_db_health()
        
        if health['status'] == 'healthy':
            print("✅ Database connection: HEALTHY")
            print(f"   - Connected: {health['connected']}")
            print(f"   - pgvector enabled: {health['pgvector_enabled']}")
            print(f"   - Tables: {', '.join(health['tables_exist'])}")
            print(f"   - Pool size: {health['pool_size']}")
        else:
            print(f"❌ Database connection: UNHEALTHY")
            print(f"   - Error: {health.get('error', 'Unknown error')}")
            return False
        
        # Check tables
        print("\n2. Verifying tables...")
        expected_tables = ['behavioral_memory', 'chat_history', 'user_profiles', 'sessions']
        missing_tables = [t for t in expected_tables if t not in health['tables_exist']]
        
        if not missing_tables:
            print("✅ All required tables exist")
        else:
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False
        
        # Check indexes
        print("\n3. Checking indexes...")
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            indexes = await conn.fetch("""
                SELECT indexname, tablename 
                FROM pg_indexes 
                WHERE schemaname = 'public'
                AND indexname LIKE '%embedding%'
            """)
            
            if indexes:
                print("✅ Vector indexes created:")
                for idx in indexes:
                    print(f"   - {idx['indexname']} on {idx['tablename']}")
            else:
                print("⚠️  No vector indexes found")
        
        print("\n" + "=" * 60)
        print("✅ Setup verification PASSED")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Run: python test_migration.py")
        print("2. Start server: uvicorn app.main:app --reload")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_setup())
    sys.exit(0 if success else 1)
