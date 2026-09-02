"""Pausing collection has to actually stop collection.

The product could already export everything it held and delete it, and could
opt out of research sharing. It could not be told to stop watching - the one
control a behavioural tracker most needs, and the thing this product criticises
platforms for lacking.

What is pinned here is that the switch is real rather than cosmetic. A pause
honoured only by the dashboard or the extension would be a request: anything
holding the user_id could keep posting. So the test that matters is the one
that counts rows in the database after a paused ingest.

Also pinned: pausing does not delete. A switch that quietly destroyed history
would be a far worse surprise than one that only stops the flow, and the copy
promises it does not.
"""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import collection_control


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def demo_user_id(db):
    user_id = f"demo_pause_{uuid.uuid4().hex[:8]}"
    yield user_id
    from app.services import data_privacy
    try:
        await data_privacy.delete_all_user_data(user_id)
    except Exception:
        pass


def _event(reel_id):
    """EventItem requires reel_id; the rest carry defaults."""
    return {
        "platform": "instagram",
        "reel_id": reel_id,
        "username": "natgeo",
        "caption": "wildlife photography",
        "hashtags": ["#nature"],
        "watch_time": 30,
        "liked": False,
    }


async def _event_count(user_id):
    from app.db.postgres import fetchval
    return await fetchval("SELECT COUNT(*) FROM events WHERE user_id = $1", user_id)


class TestTheContract:
    def test_erasure_takes_the_setting_with_it(self):
        """Erasing everything while leaving a row keyed to their user_id is its
        own small dishonesty."""
        from app.services.data_privacy import USER_DATA_TABLES
        assert "collection_settings" in USER_DATA_TABLES

    def test_the_check_sits_in_ingest_not_the_client(self):
        """A pause enforced anywhere but the server is a request, not a
        guarantee."""
        import inspect
        from app.api import ingest

        source = inspect.getsource(ingest.ingest_events)
        assert "collection_control.is_paused" in source
        # Before anything is written.
        assert source.index("is_paused") < source.index("req.warnings")

    @pytest.mark.asyncio
    async def test_an_unreadable_table_fails_open(self, monkeypatch):
        """Deliberately the uncomfortable direction. Failing closed would stop
        collection for everyone the moment this table became unreadable, and a
        tracker that quietly stops is harder to notice than one that keeps
        going."""
        async def boom(*_a, **_k):
            raise RuntimeError("table gone")
        monkeypatch.setattr(collection_control, "fetchrow", boom)
        assert await collection_control.is_paused("u") is False


@pytest.mark.db
@pytest.mark.asyncio
async def test_pausing_stops_events_reaching_the_database(db, demo_user_id, client):
    """The test this file exists for."""
    first = await client.post("/ingest", json={
        "user_id": demo_user_id, "events": [_event("evt_before")]})
    assert first.status_code == 200, first.text
    assert await _event_count(demo_user_id) == 1

    await client.post("/collection/pause", json={"user_id": demo_user_id, "paused": True})

    second = await client.post("/ingest", json={
        "user_id": demo_user_id, "events": [_event("evt_during")]})
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["events_stored"] == 0
    assert "paused" in body["message"].lower()

    assert await _event_count(demo_user_id) == 1, "an event was stored while paused"


@pytest.mark.db
@pytest.mark.asyncio
async def test_resuming_starts_collecting_again(db, demo_user_id, client):
    await client.post("/collection/pause", json={"user_id": demo_user_id, "paused": True})
    await client.post("/ingest", json={"user_id": demo_user_id, "events": [_event("evt_a")]})
    assert await _event_count(demo_user_id) == 0

    await client.post("/collection/pause", json={"user_id": demo_user_id, "paused": False})
    await client.post("/ingest", json={"user_id": demo_user_id, "events": [_event("evt_b")]})
    assert await _event_count(demo_user_id) == 1


@pytest.mark.db
@pytest.mark.asyncio
async def test_pausing_does_not_delete_what_was_already_collected(db, demo_user_id, client):
    """The interface promises this explicitly."""
    await client.post("/ingest", json={"user_id": demo_user_id, "events": [_event("evt_keep")]})
    before = await _event_count(demo_user_id)
    assert before == 1

    await client.post("/collection/pause", json={"user_id": demo_user_id, "paused": True})
    assert await _event_count(demo_user_id) == before


@pytest.mark.db
@pytest.mark.asyncio
async def test_status_reports_the_state_and_its_scope(db, demo_user_id, client):
    running = (await client.get(f"/collection/status?user_id={demo_user_id}")).json()
    assert running["paused"] is False
    assert running["paused_at"] is None
    assert "does not delete" in running["note"]

    await client.post("/collection/pause", json={"user_id": demo_user_id, "paused": True})
    paused = (await client.get(f"/collection/status?user_id={demo_user_id}")).json()
    assert paused["paused"] is True
    assert paused["paused_at"] is not None
    assert "still stored" in paused["note"]


@pytest.mark.db
@pytest.mark.asyncio
async def test_pausing_twice_does_not_reset_the_clock(db, demo_user_id, client):
    """Otherwise a long pause reads as though it began just now."""
    first = (await client.post("/collection/pause",
                               json={"user_id": demo_user_id, "paused": True})).json()
    again = (await client.post("/collection/pause",
                               json={"user_id": demo_user_id, "paused": True})).json()
    assert first["paused_at"] == again["paused_at"]


@pytest.mark.db
@pytest.mark.asyncio
async def test_a_stranger_cannot_change_someone_elses_collection(db, client):
    """Resuming someone's collection without their knowledge is the worst
    version of this bug, so the write takes the same authority as any other
    write to their account."""
    from app.services import data_privacy

    alice = f"alice_{uuid.uuid4().hex[:8]}"
    bob = f"bob_{uuid.uuid4().hex[:8]}"
    await client.post("/auth/register", json={"username": alice, "password": "test-password-123"})
    bob_token = (await client.post("/auth/register",
                                   json={"username": bob, "password": "test-password-123"})).json()["token"]
    try:
        resp = await client.post(
            "/collection/pause",
            json={"user_id": alice, "paused": False},
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert resp.status_code == 403

        anon = await client.post("/collection/pause", json={"user_id": alice, "paused": False})
        assert anon.status_code == 401
    finally:
        for name in (alice, bob):
            await data_privacy.delete_all_user_data(name)
            await data_privacy.delete_account(name)
