"""Clear old embeddings and personas from behavioral-engine"""
import asyncio
from app.db.postgres import init_pool, execute, close_pool

async def main():
    await init_pool()
    
    # Clear old embeddings and personas
    await execute("DELETE FROM embeddings;")
    await execute("DELETE FROM personas;")
    await execute("DELETE FROM events WHERE user_id = 'test_verification';")
    
    print("✅ Cleared old embeddings, personas, and test events")
    
    await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
