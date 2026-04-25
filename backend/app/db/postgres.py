"""
PostgreSQL connection module for Neon + pgvector
Async connection pool with health checks
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, List, Any

import asyncpg
from asyncpg.pool import Pool
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

_pool: Optional[Pool] = None


async def init_pool(min_size: int = 2, max_size: int = 10) -> Pool:
    global _pool
    if _pool is None:
        # asyncpg needs sslmode via ssl param, strip channel_binding for compat
        dsn = DATABASE_URL
        _pool = await asyncpg.create_pool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            command_timeout=30,
            server_settings={"jit": "off"},
        )
        logger.info("Database pool created (min=%d, max=%d)", min_size, max_size)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


async def get_pool() -> Pool:
    global _pool
    if _pool is None:
        await init_pool()
    return _pool


@asynccontextmanager
async def get_conn():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def fetch(query: str, *args) -> List[asyncpg.Record]:
    async with get_conn() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args) -> Optional[asyncpg.Record]:
    async with get_conn() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args) -> Any:
    async with get_conn() as conn:
        return await conn.fetchval(query, *args)


async def execute(query: str, *args) -> str:
    async with get_conn() as conn:
        return await conn.execute(query, *args)


async def executemany(query: str, args_list: list):
    async with get_conn() as conn:
        await conn.executemany(query, args_list)


async def run_schema():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    async with get_conn() as conn:
        with open(schema_path, "r") as f:
            await conn.execute(f.read())
    logger.info("Schema applied successfully")


async def health() -> dict:
    try:
        async with get_conn() as conn:
            ok = await conn.fetchval("SELECT 1")
            vec = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')"
            )
            tables = await conn.fetch(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name IN "
                "('events','embeddings','personas','actions_log')"
            )
        return {
            "status": "healthy",
            "connected": ok == 1,
            "pgvector": vec,
            "tables": [r["table_name"] for r in tables],
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
