import os
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env if available
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key not in os.environ:
            os.environ[key] = value


@pytest_asyncio.fixture(scope="session")
async def db():
    """Live DB pool for tests marked `db`. Skips (not errors) if the
    configured DATABASE_URL is unreachable, so the suite stays runnable
    without a live Postgres available."""
    from app.db import postgres
    try:
        pool = await postgres.init_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        # Tests hit the ASGI app directly via ASGITransport, which does not
        # run FastAPI's lifespan (that's where the real app applies
        # migrations on startup) — apply them here so schema-dependent
        # tests see the same DB shape the real running app would.
        await postgres.run_schema()
    except Exception as e:
        pytest.skip(f"DATABASE_URL unreachable: {e}")
    yield postgres
    await postgres.close_pool()


@pytest_asyncio.fixture
async def disposable_user_id(db):
    """A throwaway user_id, deleted (all tables) after the test regardless
    of pass/fail — keeps pytest runs from leaving junk rows in the shared
    dev database."""
    user_id = f"pytest_{uuid.uuid4().hex[:8]}"
    yield user_id
    from app.services import data_privacy
    try:
        await data_privacy.delete_all_user_data(user_id)
    except Exception:
        pass
