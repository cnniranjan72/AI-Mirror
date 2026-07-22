"""Clean test data for pipeline validation."""
import asyncio
import sys
from app.db.postgres import init_pool, execute, close_pool

async def clean(user_id="test_user_001"):
    await init_pool()
    tables = [
        "behavior_objects", "evidence", "inferences", "identities",
        "identity_snapshots", "self_models", "memories", "goals",
        "reflections", "runtime_metrics",
    ]
    for t in tables:
        try:
            await execute(f"DELETE FROM {t} WHERE user_id = $1", user_id)
            print(f"Cleaned {t}")
        except Exception as e:
            print(f"{t}: {e}")
    try:
        await execute("DELETE FROM events WHERE user_id = $1", user_id)
        print("Cleaned events")
    except Exception as e:
        print(f"events: {e}")
    await close_pool()

asyncio.run(clean())
