"""Run database schema setup"""
import asyncio
from app.db.postgres import init_pool, run_schema, close_pool

async def main():
    await init_pool()
    await run_schema()
    await close_pool()
    print("✅ Schema applied successfully")

if __name__ == "__main__":
    asyncio.run(main())
