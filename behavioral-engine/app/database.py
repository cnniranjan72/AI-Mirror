"""
Database connection module for Neon PostgreSQL with pgvector
Replaces ChromaDB with PostgreSQL vector storage
"""

import os
from typing import Optional
from contextlib import asynccontextmanager
import asyncpg
from asyncpg.pool import Pool
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Connection pool
_pool: Optional[Pool] = None


async def init_db_pool(min_size: int = 5, max_size: int = 20) -> Pool:
    """
    Initialize database connection pool
    
    Args:
        min_size: Minimum number of connections in pool
        max_size: Maximum number of connections in pool
        
    Returns:
        Connection pool instance
    """
    global _pool
    
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60,
            server_settings={
                'jit': 'off'  # Disable JIT for better performance with small queries
            }
        )
    
    return _pool


async def close_db_pool():
    """Close database connection pool"""
    global _pool
    
    if _pool is not None:
        await _pool.close()
        _pool = None


async def get_db_pool() -> Pool:
    """
    Get database connection pool
    
    Returns:
        Connection pool instance
    """
    global _pool
    
    if _pool is None:
        _pool = await init_db_pool()
    
    return _pool


@asynccontextmanager
async def get_db_connection():
    """
    Context manager for database connections
    
    Usage:
        async with get_db_connection() as conn:
            result = await conn.fetch("SELECT * FROM table")
    """
    pool = await get_db_pool()
    async with pool.acquire() as connection:
        yield connection


async def execute_query(query: str, *args):
    """
    Execute a query and return results
    
    Args:
        query: SQL query string
        *args: Query parameters
        
    Returns:
        Query results
    """
    async with get_db_connection() as conn:
        return await conn.fetch(query, *args)


async def execute_one(query: str, *args):
    """
    Execute a query and return single result
    
    Args:
        query: SQL query string
        *args: Query parameters
        
    Returns:
        Single query result or None
    """
    async with get_db_connection() as conn:
        return await conn.fetchrow(query, *args)


async def execute_insert(query: str, *args):
    """
    Execute an insert query and return inserted row
    
    Args:
        query: SQL query string
        *args: Query parameters
        
    Returns:
        Inserted row
    """
    async with get_db_connection() as conn:
        return await conn.fetchrow(query, *args)


async def execute_many(query: str, args_list: list):
    """
    Execute batch insert/update
    
    Args:
        query: SQL query string
        args_list: List of parameter tuples
        
    Returns:
        Number of affected rows
    """
    async with get_db_connection() as conn:
        await conn.executemany(query, args_list)
        return len(args_list)


async def check_db_health() -> dict:
    """
    Check database health and connectivity
    
    Returns:
        Health status dictionary
    """
    try:
        async with get_db_connection() as conn:
            # Check basic connectivity
            result = await conn.fetchval("SELECT 1")
            
            # Check pgvector extension
            vector_check = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            
            # Check table existence
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name IN ('behavioral_memory', 'chat_history', 'user_profiles', 'sessions')
            """)
            
            table_names = [row['table_name'] for row in tables]
            
            # Get connection pool stats
            pool = await get_db_pool()
            
            return {
                "status": "healthy",
                "connected": result == 1,
                "pgvector_enabled": vector_check,
                "tables_exist": table_names,
                "pool_size": pool.get_size(),
                "pool_free": pool.get_size() - pool.get_idle_size()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def initialize_database():
    """
    Initialize database schema
    Run migrations if needed
    """
    async with get_db_connection() as conn:
        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # Check if tables exist
        tables_exist = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'behavioral_memory'
            )
        """)
        
        if not tables_exist:
            # Read and execute migration file
            migration_path = os.path.join(
                os.path.dirname(__file__), 
                "..", 
                "migrations", 
                "001_initial_schema.sql"
            )
            
            if os.path.exists(migration_path):
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                    await conn.execute(migration_sql)
            else:
                raise FileNotFoundError(f"Migration file not found: {migration_path}")


# Utility functions for vector operations
def vector_to_list(vector_str: str) -> list:
    """Convert PostgreSQL vector string to Python list"""
    if vector_str.startswith('[') and vector_str.endswith(']'):
        return [float(x) for x in vector_str[1:-1].split(',')]
    return []


def list_to_vector(vector_list: list) -> str:
    """Convert Python list to PostgreSQL vector string"""
    return '[' + ','.join(map(str, vector_list)) + ']'
