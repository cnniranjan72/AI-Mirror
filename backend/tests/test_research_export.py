"""Research export: opt-in gating, de-identification, and that opting out
removes a user from future exports.
"""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import research_export

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


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_opt_in_defaults_to_false(client, db):
    user = f"researchuser_{uuid.uuid4().hex[:8]}"
    token = await _register(client, user)
    resp = await client.get("/research/status", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["opted_in"] is False


@pytest.mark.asyncio
async def test_opted_in_user_appears_in_export_with_anonymized_id(client, db):
    user = f"researchuser_{uuid.uuid4().hex[:8]}"
    token = await _register(client, user)

    opt = await client.post("/research/opt-in", json={"opt_in": True}, headers=_auth(token))
    assert opt.status_code == 200
    assert opt.json()["opted_in"] is True

    export = await client.get("/research/export", headers=_auth(token))
    assert export.status_code == 200
    body = export.json()

    expected_pid = research_export.participant_id(user)
    pids = [p["participant_id"] for p in body["participants"]]
    assert expected_pid in pids
    # The raw username must never appear anywhere in the export.
    assert user not in export.text


@pytest.mark.asyncio
async def test_opted_out_user_excluded_from_export(client, db):
    user = f"researchuser_{uuid.uuid4().hex[:8]}"
    token = await _register(client, user)
    await client.post("/research/opt-in", json={"opt_in": True}, headers=_auth(token))
    await client.post("/research/opt-in", json={"opt_in": False}, headers=_auth(token))

    export = await client.get("/research/export", headers=_auth(token))
    pids = [p["participant_id"] for p in export.json()["participants"]]
    assert research_export.participant_id(user) not in pids


@pytest.mark.asyncio
async def test_participant_id_is_stable_and_non_reversible(db):
    a = research_export.participant_id("alice")
    b = research_export.participant_id("alice")
    c = research_export.participant_id("bob")
    assert a == b
    assert a != c
    assert "alice" not in a


@pytest.mark.asyncio
async def test_export_requires_auth(client, db):
    resp = await client.get("/research/export")
    assert resp.status_code == 401
