"""Global exception handler + error_events recording."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.db


@pytest.mark.asyncio
async def test_unhandled_exception_returns_structured_500(db, monkeypatch):
    from app.api import timeline as timeline_module

    async def _boom(*args, **kwargs):
        raise RuntimeError("synthetic failure for test_error_handling")

    monkeypatch.setattr(timeline_module, "fetch", _boom)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/timeline", params={"user_id": "test_user_001"})

    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "internal_error"
    assert body["trace_id"]
    assert resp.headers.get("x-trace-id") == body["trace_id"]

    from app.db.postgres import fetch
    rows = await fetch(
        "SELECT trace_id, error_type, message FROM error_events WHERE trace_id = $1",
        body["trace_id"],
    )
    assert len(rows) == 1
    assert "synthetic failure for test_error_handling" in rows[0]["message"]


@pytest.mark.asyncio
async def test_admin_errors_endpoint_lists_recent(db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/admin/errors", params={"limit": 5})
    assert resp.status_code == 200
    assert "errors" in resp.json()
