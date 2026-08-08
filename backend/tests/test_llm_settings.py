"""Per-user LLM provider settings: storage, masking, and auth enforcement.
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


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_defaults_to_no_key(client, db):
    user = f"llmuser_{uuid.uuid4().hex[:8]}"
    token = await _register(client, user)
    resp = await client.get("/settings/llm", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_key"] is False
    assert body["provider"] is None


@pytest.mark.asyncio
async def test_set_and_get_masks_the_key(client, db):
    user = f"llmuser_{uuid.uuid4().hex[:8]}"
    token = await _register(client, user)

    resp = await client.post("/settings/llm", json={
        "provider": "openai", "api_key": "sk-abcdefghijklmnop1234",
    }, headers=_auth(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_key"] is True
    assert body["provider"] == "openai"
    assert "abcdefghijklmnop" not in body["key_preview"]
    assert body["key_preview"].endswith("1234")

    resp2 = await client.get("/settings/llm", headers=_auth(token))
    assert resp2.json()["has_key"] is True


@pytest.mark.asyncio
async def test_invalid_provider_rejected(client, db):
    user = f"llmuser_{uuid.uuid4().hex[:8]}"
    token = await _register(client, user)
    resp = await client.post("/settings/llm", json={
        "provider": "not-a-real-provider", "api_key": "x",
    }, headers=_auth(token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_non_ollama_provider_requires_key(client, db):
    user = f"llmuser_{uuid.uuid4().hex[:8]}"
    token = await _register(client, user)
    resp = await client.post("/settings/llm", json={"provider": "anthropic"}, headers=_auth(token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_ollama_does_not_require_key(client, db):
    user = f"llmuser_{uuid.uuid4().hex[:8]}"
    token = await _register(client, user)
    resp = await client.post("/settings/llm", json={
        "provider": "ollama", "base_url": "https://my-ollama.example.com/v1",
    }, headers=_auth(token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["has_key"] is False
    assert resp.json()["base_url"] == "https://my-ollama.example.com/v1"


@pytest.mark.asyncio
async def test_clear_reverts_to_server_default(client, db):
    user = f"llmuser_{uuid.uuid4().hex[:8]}"
    token = await _register(client, user)
    await client.post("/settings/llm", json={"provider": "openai", "api_key": "sk-test"}, headers=_auth(token))

    resp = await client.delete("/settings/llm", headers=_auth(token))
    assert resp.status_code == 200

    check = await client.get("/settings/llm", headers=_auth(token))
    assert check.json()["has_key"] is False
    assert check.json()["provider"] is None


@pytest.mark.asyncio
async def test_requires_auth(client, db):
    resp = await client.get("/settings/llm")
    assert resp.status_code == 401
    resp2 = await client.post("/settings/llm", json={"provider": "openai", "api_key": "x"})
    assert resp2.status_code == 401
    resp3 = await client.delete("/settings/llm")
    assert resp3.status_code == 401
