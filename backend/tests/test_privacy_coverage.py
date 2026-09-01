"""Right-to-erasure coverage.

USER_DATA_TABLES drives both export and deletion, so a table missing from it
is silently exempt from both: an erasure request reports success while the
rows stay in the database. That is the worst possible failure mode for this
particular feature — it fails quietly, and it fails a legal obligation.

platform_profile_claims was added late and did exactly that, which is why
these tests check the RULE rather than any one table.
"""
import pytest

from app.services.data_privacy import USER_DATA_TABLES

pytestmark = pytest.mark.db


@pytest.mark.asyncio
async def test_every_user_scoped_table_is_covered(db):
    """Discovers tables from the live schema instead of a hand-written list,
    so adding a user-keyed table without registering it fails here rather than
    in a user's erasure request."""
    from app.db.postgres import fetch

    rows = await fetch(
        """
        SELECT table_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND column_name = 'user_id'
        GROUP BY table_name
        """
    )
    discovered = {r["table_name"] for r in rows}

    # Tables deliberately out of scope: `users` is the account itself (deleting
    # data must not delete the login), and rl_policy is a shared, non-personal
    # model of action quality rather than a record about any one person.
    exempt = {"users", "rl_policy"}

    missing = discovered - set(USER_DATA_TABLES) - exempt
    assert not missing, (
        f"These user-keyed tables are exempt from export AND erasure: "
        f"{sorted(missing)}. Add them to USER_DATA_TABLES."
    )


@pytest.mark.asyncio
async def test_platform_claims_are_actually_deleted(db, disposable_user_id):
    """The specific regression: a platform's profile of someone is personal
    data about them, and has to be erasable."""
    from app.db.postgres import execute, fetchrow
    from app.services import data_privacy

    await execute(
        """
        INSERT INTO platform_profile_claims
            (user_id, platform, claim_type, label, raw_label)
        VALUES ($1, 'meta', 'ad_interest', 'robotics', 'Robotics')
        """,
        disposable_user_id,
    )

    before = await fetchrow(
        "SELECT COUNT(*) AS c FROM platform_profile_claims WHERE user_id = $1",
        disposable_user_id,
    )
    assert before["c"] == 1

    await data_privacy.delete_all_user_data(disposable_user_id)

    after = await fetchrow(
        "SELECT COUNT(*) AS c FROM platform_profile_claims WHERE user_id = $1",
        disposable_user_id,
    )
    assert after["c"] == 0
