"""Bring stored lifecycle_state up to date without waiting for an ingest.

The ingest sweep re-evaluates every behaviour a user has, so an active account
stays correct on its own. An account that has stopped sending events never gets
that sweep - and those are exactly the accounts whose behaviours have gone
dormant, so the stored label is most wrong precisely where it matters most.

Measured on the deployed instance before this existed: all 226 behaviour
objects disagreed with a fresh evaluation. The column said "growing" for 217 of
them; evaluating the same stored statistics gave 143 dormant, 48 archived, 31
stable and 4 emerging.

Reading is already safe. The Moved On page and goal scoring both evaluate the
state when asked rather than trusting the column, so nothing user-facing
depends on this script. It exists for everything that reads the column
directly, and so the stored value is not quietly wrong.

    python refresh_lifecycles.py           # report what would change
    python refresh_lifecycles.py --apply   # write it

Nothing is destroyed: lifecycle_state is derived, and this recomputes it from
statistics already stored. Running it twice changes nothing the second time.
"""
import asyncio
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.db.postgres import close_pool, execute, fetch, init_pool  # noqa: E402
from reasoning.lifecycle import evaluate_lifecycle  # noqa: E402


def _decode(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}
    return value or {}


async def main(apply: bool) -> int:
    await init_pool()
    try:
        rows = await fetch(
            "SELECT unique_id, user_id, topic, lifecycle_state, "
            "temporal_statistics, trend_information FROM behavior_objects"
        )

        changes = []
        moves = Counter()
        for row in rows:
            state, _reason = evaluate_lifecycle(
                _decode(row["temporal_statistics"]),
                _decode(row["trend_information"]),
            )
            if state != row["lifecycle_state"]:
                changes.append((row["unique_id"], row["lifecycle_state"], state))
                moves[(row["lifecycle_state"], state)] += 1

        print("behaviour objects: %d" % len(rows))
        print("out of date:       %d" % len(changes))
        if moves:
            print("\ntransitions:")
            for (was, now), n in moves.most_common():
                print("   %-10s -> %-10s %d" % (was, now, n))

        if not changes:
            print("\nNothing to do.")
            return 0

        if not apply:
            print("\nDry run. Pass --apply to write these.")
            return 0

        for unique_id, _was, now in changes:
            await execute(
                "UPDATE behavior_objects SET lifecycle_state = $1, updated_at = NOW() "
                "WHERE unique_id = $2",
                now, unique_id,
            )
        print("\nUpdated %d rows." % len(changes))
        return 0
    finally:
        await close_pool()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main("--apply" in sys.argv)))
