"""Explain endpoints must not hand another user's profile to whoever has an id.

Four endpoints are addressed by an opaque resource id instead of a user_id:

    GET /query/traces/{trace_id}
    GET /explain/{trace_id}
    GET /explain/evidence/{evidence_id}
    GET /explain/identity/{identity_id}

Each reads the owning user_id off the row it just fetched and then assembles
that user's identity snapshot, personality traits, interest graph, beliefs,
evidence, inferences and reflections. They shipped with no ownership check, so
holding an id was enough to read someone's entire cognitive profile — the most
sensitive data the product holds.

The ids are not a meaningful barrier either: evidence ids are built as
evidence_{type}_{topic}_{timestamp} and identity ids are
identity_{username}_{8 hex}. Neither is a secret, and one leaked trace exposes
the snapshot_id and self_model_id it links to.

tests/test_auth_coverage.py cannot catch this shape: it enumerates routes
taking a user_id, and these take none.
"""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# ── The structural guard (no database) ──────────────────────────────────────

OPAQUE_ID_ROUTES = [
    "/query/traces/{trace_id}",
    "/explain/{trace_id}",
    "/explain/evidence/{evidence_id}",
    "/explain/identity/{identity_id}",
]


def _endpoint(path):
    return next(r for r in app.routes if getattr(r, "path", None) == path).endpoint


@pytest.mark.parametrize("path", OPAQUE_ID_ROUTES)
def test_route_checks_ownership_of_the_row_it_loaded(path):
    """The check cannot be a dependency — the owner is only known after the
    lookup — so it has to be an explicit call inside the handler."""
    import inspect

    source = inspect.getsource(_endpoint(path))
    assert "enforce_user_match" in source, (
        f"{path} returns data belonging to the row's owner without checking "
        f"that the caller is that owner"
    )


@pytest.mark.parametrize("path", OPAQUE_ID_ROUTES)
def test_route_accepts_the_authorization_header(path):
    """Without the header in the signature the enforcement call would always
    see None and reject every signed-in user."""
    import inspect

    assert "authorization" in inspect.signature(_endpoint(path)).parameters, path


# ── The behaviour (live database) ───────────────────────────────────────────

pytest_db = pytest.mark.db


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


async def _insert_trace(db, user_id, trace_id):
    await db.execute(
        """
        INSERT INTO pipeline_traces (trace_id, user_id, query, intent_type)
        VALUES ($1, $2, $3, $4)
        """,
        trace_id, user_id, "what am I into?", "self_query",
    )


@pytest.mark.db
@pytest.mark.asyncio
async def test_a_stranger_cannot_read_someone_elses_trace(db, client):
    """The core regression. Bob holds Alice's trace_id and nothing else."""
    from app.services import data_privacy

    alice = f"alice_{uuid.uuid4().hex[:8]}"
    bob = f"bob_{uuid.uuid4().hex[:8]}"
    trace_id = f"trace_{uuid.uuid4().hex}"

    await _register(client, alice)
    bob_token = await _register(client, bob)
    try:
        await _insert_trace(db, alice, trace_id)

        for path in (f"/query/traces/{trace_id}", f"/explain/{trace_id}"):
            resp = await client.get(path, headers={"Authorization": f"Bearer {bob_token}"})
            assert resp.status_code == 403, f"{path} leaked to another user: {resp.text[:200]}"
    finally:
        await data_privacy.delete_all_user_data(alice)
        await data_privacy.delete_all_user_data(bob)


@pytest.mark.db
@pytest.mark.asyncio
async def test_an_anonymous_caller_cannot_read_a_real_users_trace(db, client):
    """No token at all — how the endpoint was reachable before the fix."""
    from app.services import data_privacy

    alice = f"alice_{uuid.uuid4().hex[:8]}"
    trace_id = f"trace_{uuid.uuid4().hex}"

    await _register(client, alice)
    try:
        await _insert_trace(db, alice, trace_id)

        for path in (f"/query/traces/{trace_id}", f"/explain/{trace_id}"):
            resp = await client.get(path)
            assert resp.status_code == 401, f"{path} readable with no token: {resp.text[:200]}"
    finally:
        await data_privacy.delete_all_user_data(alice)


@pytest.mark.db
@pytest.mark.asyncio
async def test_the_owner_can_still_read_their_own_trace(db, client):
    """The fix must not lock users out of their own explainability data —
    which is the feature the whole product is arguing for."""
    from app.services import data_privacy

    alice = f"alice_{uuid.uuid4().hex[:8]}"
    trace_id = f"trace_{uuid.uuid4().hex}"

    token = await _register(client, alice)
    try:
        await _insert_trace(db, alice, trace_id)

        resp = await client.get(
            f"/query/traces/{trace_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["trace_id"] == trace_id
    finally:
        await data_privacy.delete_all_user_data(alice)


@pytest.mark.db
@pytest.mark.asyncio
async def test_demo_traces_stay_browsable_signed_out(db, client):
    """Public ids are meant to be readable by anyone — that is the signed-out
    demo, and the fix must not break it."""
    from app.services import data_privacy

    demo_user = f"demo_idor_{uuid.uuid4().hex[:8]}"
    trace_id = f"trace_{uuid.uuid4().hex}"
    try:
        await _insert_trace(db, demo_user, trace_id)

        resp = await client.get(f"/query/traces/{trace_id}")
        assert resp.status_code == 200, resp.text
    finally:
        await data_privacy.delete_all_user_data(demo_user)


@pytest.mark.db
@pytest.mark.asyncio
async def test_a_missing_id_does_not_require_auth(db, client):
    """A nonexistent id has no owner to check against; it must not turn into
    a confusing 401."""
    resp = await client.get(f"/query/traces/does_not_exist_{uuid.uuid4().hex}")
    assert resp.status_code == 200
    assert resp.json() is None
