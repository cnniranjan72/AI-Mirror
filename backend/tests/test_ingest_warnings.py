"""IngestRequest accepts extension extraction-failure warnings and records
them via error_tracking, instead of the extension's console.log being the
only record they ever existed (the same failure-visibility gap that let the
YouTube caption bug go unnoticed)."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.db


@pytest.mark.asyncio
async def test_ingest_accepts_warnings_only_batch(db):
    username = f"warntest_{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/auth/register", json={"username": username, "password": "test-password-123"})
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/ingest",
            json={
                "user_id": username,
                "events": [],
                "warnings": [{
                    "type": "extraction_failed", "platform": "youtube", "surface": "shorts",
                    "content_id": "abc123", "tier": 2, "timestamp": "2026-01-01T00:00:00Z",
                }],
            },
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

        errors = await client.get("/admin/errors", params={"error_type": "extension_extraction_failed", "limit": 5})
        assert errors.status_code == 200
        matches = [e for e in errors.json()["errors"] if e["user_id"] == username]
        assert len(matches) == 1
        assert "abc123" in matches[0]["message"]

    from app.services import data_privacy
    await data_privacy.delete_all_user_data(username)


@pytest.mark.asyncio
async def test_ingest_still_rejects_empty_events_with_no_warnings(db):
    username = f"warntest2_{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/auth/register", json={"username": username, "password": "test-password-123"})
        token = reg.json()["token"]
        resp = await client.post(
            "/ingest",
            json={"user_id": username, "events": [], "warnings": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    from app.services import data_privacy
    await data_privacy.delete_all_user_data(username)
