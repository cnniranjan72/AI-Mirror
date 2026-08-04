"""POST /admin/reprocess — the reusable replacement for the one-off script
hand-rolled earlier this session to fix stale/orphaned behavior_objects."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.db


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seeded_user(client):
    """Register a real user and give them a few real events via /ingest,
    so reprocess has real, auth-checkable data to work with."""
    username = f"reproc_{uuid.uuid4().hex[:8]}"
    reg = await client.post("/auth/register", json={"username": username, "password": "test-password-123"})
    assert reg.status_code == 200, reg.text
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    events = [{
        "reel_id": f"reproc_reel_{i}",
        "username": "some_creator",
        "caption": f"AI research deep dive part {i}",
        "hashtags": ["#ai", "#research"],
        "watch_time": 45.0,
        "liked": True,
        "session_id": "reproc_session",
        "platform": "instagram",
    } for i in range(5)]

    ingest_resp = await client.post("/ingest", json={"user_id": username, "events": events}, headers=headers)
    assert ingest_resp.status_code == 200, ingest_resp.text
    return username, token, headers


@pytest.mark.asyncio
async def test_dry_run_does_not_mutate(db, client):
    username, _, headers = await _seeded_user(client)
    try:
        before = await client.post(
            "/admin/reprocess",
            json={"user_id": username, "confirm_user_id": username, "dry_run": True},
            headers=headers,
        )
        assert before.status_code == 200, before.text
        body = before.json()
        assert body["dry_run"] is True
        assert body["events_loaded"] == 5

        # A second dry run sees identical counts — proves nothing was written.
        again = await client.post(
            "/admin/reprocess",
            json={"user_id": username, "confirm_user_id": username, "dry_run": True},
            headers=headers,
        )
        assert again.json()["current_counts"] == body["current_counts"]
    finally:
        from app.services import data_privacy
        await data_privacy.delete_all_user_data(username)


@pytest.mark.asyncio
async def test_reprocess_rebuilds_and_is_idempotent(db, client):
    username, _, headers = await _seeded_user(client)
    try:
        first = await client.post(
            "/admin/reprocess",
            json={"user_id": username, "confirm_user_id": username},
            headers=headers,
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["pipeline_result"]["behavior_object_count"] > 0
        assert first_body["pipeline_result"]["evidence_count"] > 0

        second = await client.post(
            "/admin/reprocess",
            json={"user_id": username, "confirm_user_id": username},
            headers=headers,
        )
        assert second.status_code == 200, second.text
        second_body = second.json()
        # Idempotent: reprocessing the same events twice shouldn't accumulate
        # duplicate behavior objects.
        assert second_body["pipeline_result"]["behavior_object_count"] == first_body["pipeline_result"]["behavior_object_count"]
    finally:
        from app.services import data_privacy
        await data_privacy.delete_all_user_data(username)


@pytest.mark.asyncio
async def test_confirm_mismatch_rejected(db, client):
    username, _, headers = await _seeded_user(client)
    try:
        resp = await client.post(
            "/admin/reprocess",
            json={"user_id": username, "confirm_user_id": "not-the-same"},
            headers=headers,
        )
        assert resp.status_code == 400
    finally:
        from app.services import data_privacy
        await data_privacy.delete_all_user_data(username)


@pytest.mark.asyncio
async def test_reprocess_requires_auth_even_for_public_ids(db, client):
    resp = await client.post(
        "/admin/reprocess",
        json={"user_id": "test_user_001", "confirm_user_id": "test_user_001"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_reprocess_rejects_unrelated_token_against_public_id(db, client):
    """Regression test for a real bug caught live during development: an
    earlier version of this endpoint used enforce_user_match (the read-path
    check, which allows any valid token to access public ids) instead of
    enforce_write_match, so an unrelated signed-in user's token was able to
    reprocess test_user_001 and wipe its accumulated identity/reflection
    history. Reprocess must require the token to belong to user_id exactly,
    even when user_id is public."""
    unrelated = f"unrelated_{uuid.uuid4().hex[:8]}"
    reg = await client.post("/auth/register", json={"username": unrelated, "password": "test-password-123"})
    token = reg.json()["token"]
    try:
        resp = await client.post(
            "/admin/reprocess",
            json={"user_id": "test_user_001", "confirm_user_id": "test_user_001"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
    finally:
        from app.services import data_privacy
        await data_privacy.delete_all_user_data(unrelated)


@pytest.mark.asyncio
async def test_reprocess_rejects_wrong_users_token(db, client):
    username, _, _ = await _seeded_user(client)
    attacker = f"attacker_{uuid.uuid4().hex[:8]}"
    reg = await client.post("/auth/register", json={"username": attacker, "password": "test-password-123"})
    attacker_token = reg.json()["token"]
    try:
        resp = await client.post(
            "/admin/reprocess",
            json={"user_id": username, "confirm_user_id": username},
            headers={"Authorization": f"Bearer {attacker_token}"},
        )
        assert resp.status_code == 403
    finally:
        from app.services import data_privacy
        await data_privacy.delete_all_user_data(username)
        await data_privacy.delete_all_user_data(attacker)
