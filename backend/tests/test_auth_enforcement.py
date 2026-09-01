"""End-to-end auth enforcement tests against the real ASGI app.

Covers the demo-preserving contract in app/api/deps.py: public ids stay
unauthenticated, real ids require a matching bearer token, invalid/expired
tokens are always rejected, and goals ownership can't be bypassed.
"""
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


async def _register(client, username):
    resp = await client.post("/auth/register", json={
        "username": username, "password": "test-password-123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


async def _cleanup(*usernames):
    """Remove the throwaway accounts a test registered.

    delete_all_user_data deliberately does not touch the `users` row (see
    services/data_privacy.py), so tests that only called it were leaking an
    account per run into the shared database — 124 of them had accumulated
    since August before anyone looked.
    """
    from app.services import data_privacy

    for username in usernames:
        await data_privacy.delete_all_user_data(username)
        await data_privacy.delete_account(username)


@pytest.mark.asyncio
async def test_public_user_id_no_token_allowed(db, client):
    resp = await client.get("/timeline", params={"user_id": "test_user_001", "limit": 1})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_real_user_id_no_token_rejected(db, client):
    resp = await client.get("/timeline", params={"user_id": "some_real_person"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_own_token_allows_own_data(db, client):
    username = f"alice_{uuid.uuid4().hex[:8]}"
    token = await _register(client, username)
    resp = await client.get(
        "/timeline", params={"user_id": username},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    await _cleanup(username)


@pytest.mark.asyncio
async def test_token_cannot_access_other_users_data(db, client):
    alice = f"alice_{uuid.uuid4().hex[:8]}"
    bob = f"bob_{uuid.uuid4().hex[:8]}"
    token = await _register(client, alice)
    await _register(client, bob)
    resp = await client.get(
        "/timeline", params={"user_id": bob},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    await _cleanup(alice)
    await _cleanup(bob)


@pytest.mark.asyncio
async def test_tampered_token_rejected_even_for_public_id(db, client):
    resp = await client.get(
        "/timeline", params={"user_id": "test_user_001"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_signed_in_user_can_still_browse_demo_data(db, client):
    username = f"alice_{uuid.uuid4().hex[:8]}"
    token = await _register(client, username)
    resp = await client.get(
        "/timeline", params={"user_id": "test_user_001"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    await _cleanup(username)


@pytest.mark.asyncio
async def test_goal_update_requires_ownership(db, client):
    owner = f"owner_{uuid.uuid4().hex[:8]}"
    attacker = f"attacker_{uuid.uuid4().hex[:8]}"
    owner_token = await _register(client, owner)
    attacker_token = await _register(client, attacker)

    create_resp = await client.post(
        "/goals",
        json={
            "user_id": owner, "goal_description": "test goal",
            "goal_type": "increase", "target_keywords": ["testing"],
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert create_resp.status_code == 200, create_resp.text
    goal_id = create_resp.json()["goal_id"]

    # No token at all -> 401 (goal ids are never public).
    no_auth_resp = await client.patch(f"/goals/{goal_id}", json={"status": "paused"})
    assert no_auth_resp.status_code == 401

    # Someone else's valid token -> 403.
    attacker_resp = await client.patch(
        f"/goals/{goal_id}", json={"status": "paused"},
        headers={"Authorization": f"Bearer {attacker_token}"},
    )
    assert attacker_resp.status_code == 403

    # The owner's own token -> succeeds.
    owner_resp = await client.patch(
        f"/goals/{goal_id}", json={"status": "paused"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_resp.status_code == 200

    await _cleanup(owner)
    await _cleanup(attacker)


@pytest.mark.asyncio
async def test_delete_all_data_rejects_unrelated_token_against_public_id(db, client):
    """The most severe version of the write-vs-read bypass bug: this must
    never allow an unrelated signed-in user's token to wipe a public id's
    data (e.g. test_user_001) just because that id is public to read."""
    unrelated = f"unrelated_{uuid.uuid4().hex[:8]}"
    token = await _register(client, unrelated)
    try:
        resp = await client.post(
            "/privacy/delete-all-data",
            json={"user_id": "test_user_001", "confirm_user_id": "test_user_001"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
    finally:
        await _cleanup(unrelated)


@pytest.mark.asyncio
async def test_ingest_rejects_unrelated_token_against_public_id(db, client):
    unrelated = f"unrelated_{uuid.uuid4().hex[:8]}"
    token = await _register(client, unrelated)
    try:
        resp = await client.post(
            "/ingest",
            json={"user_id": "test_user_001", "events": [{
                "reel_id": "poison_attempt", "username": "attacker_creator",
                "caption": "should never be stored", "watch_time": 10.0,
                "session_id": "attack_session",
            }]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
    finally:
        await _cleanup(unrelated)
