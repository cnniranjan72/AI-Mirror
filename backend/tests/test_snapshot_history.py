"""Identity snapshot history actually accumulates across ingests.

The unit-level gate is covered in test_snapshot_gate.py. This is the
end-to-end half: drive real events through /ingest more than once and assert
that `identity_snapshots` grows, because the bug being guarded against was
invisible at every level except this one — each individual ingest looked
completely healthy while the stored history quietly stopped at the first row.
"""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.postgres import fetchrow

pytestmark = pytest.mark.db


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _register(client):
    username = f"snaphist_{uuid.uuid4().hex[:8]}"
    resp = await client.post("/auth/register", json={"username": username, "password": "test-password-123"})
    assert resp.status_code == 200, resp.text
    return username, {"Authorization": f"Bearer {resp.json()['token']}"}


def _events(topic, n, offset=0):
    return [{
        "reel_id": f"snaphist_{topic}_{offset + i}",
        "username": f"creator_{topic}",
        "caption": f"{topic} deep dive part {offset + i}",
        "hashtags": [f"#{topic}"],
        "watch_time": 40.0 + i,
        "liked": True,
        "session_id": f"snaphist_session_{offset}",
        "platform": "instagram",
    } for i in range(n)]


async def _snapshot_count(user_id):
    row = await fetchrow(
        "SELECT COUNT(*) AS c FROM identity_snapshots WHERE user_id = $1", user_id
    )
    return row["c"] if row else 0


@pytest.mark.asyncio
async def test_history_grows_across_ingests(db, client):
    """Two ingests of clearly different content must leave more than the one
    snapshot the first ingest creates."""
    username, headers = await _register(client)
    try:
        first = await client.post(
            "/ingest", json={"user_id": username, "events": _events("ai", 6)}, headers=headers
        )
        assert first.status_code == 200, first.text
        after_first = await _snapshot_count(username)
        assert after_first >= 1, "the initial construct must always store a snapshot"

        # Different topic and creator, so the identity genuinely moves rather
        # than the test passing on the time-based floor alone.
        second = await client.post(
            "/ingest",
            json={"user_id": username, "events": _events("cooking", 6, offset=100)},
            headers=headers,
        )
        assert second.status_code == 200, second.text

        assert await _snapshot_count(username) > after_first, (
            "identity history stopped growing — the snapshot gate is measuring "
            "drift against the wrong baseline again"
        )
    finally:
        from app.services import data_privacy
        try:
            await data_privacy.delete_all_user_data(username)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_shift_diagnostics_are_persisted(db, client):
    """identity_shift / snapshot_threshold_exceeded must reach the database.

    They were computed and used at runtime but never written, which is exactly
    why the gate's behaviour was undiagnosable from the data.
    """
    username, headers = await _register(client)
    try:
        resp = await client.post(
            "/ingest", json={"user_id": username, "events": _events("ai", 5)}, headers=headers
        )
        assert resp.status_code == 200, resp.text

        # A second pass is what produces a shift measurement at all — the first
        # goes through construct, not evolve.
        resp = await client.post(
            "/ingest", json={"user_id": username, "events": _events("travel", 5, offset=50)}, headers=headers
        )
        assert resp.status_code == 200, resp.text

        row = await fetchrow(
            "SELECT metadata FROM identities WHERE user_id = $1", username
        )
        assert row is not None, "identity row missing"

        import json
        metadata = row["metadata"]
        metadata = json.loads(metadata) if isinstance(metadata, str) else (metadata or {})

        assert "identity_shift" in metadata, f"shift not persisted; got keys {sorted(metadata)}"
        assert isinstance(metadata["identity_shift"], (int, float))
        assert metadata["shift_baseline"] in ("last_snapshot", "previous_identity")
    finally:
        from app.services import data_privacy
        try:
            await data_privacy.delete_all_user_data(username)
        except Exception:
            pass
