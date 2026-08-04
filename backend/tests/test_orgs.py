"""Organizations: create/invite/join/roster/remove/leave, and the privacy
boundary that no org endpoint ever returns another member's cognitive data —
only the users/organizations tables are touched.
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
async def test_create_org_makes_creator_owner(client, db):
    owner = f"orgowner_{uuid.uuid4().hex[:8]}"
    token = await _register(client, owner)

    resp = await client.post("/orgs", json={"name": "Acme Research"}, headers=_auth(token))
    assert resp.status_code == 200, resp.text
    org = resp.json()["org"]
    assert org["role"] == "owner"
    assert org["member_count"] == 1
    assert org["owner_username"] == owner

    me = await client.get("/orgs/me", headers=_auth(token))
    assert me.json()["org"]["id"] == org["id"]


@pytest.mark.asyncio
async def test_cannot_create_second_org_while_in_one(client, db):
    owner = f"orgowner_{uuid.uuid4().hex[:8]}"
    token = await _register(client, owner)
    await client.post("/orgs", json={"name": "First Org"}, headers=_auth(token))

    resp = await client.post("/orgs", json={"name": "Second Org"}, headers=_auth(token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invite_and_join_flow(client, db):
    owner = f"orgowner_{uuid.uuid4().hex[:8]}"
    member = f"orgmember_{uuid.uuid4().hex[:8]}"
    owner_token = await _register(client, owner)
    member_token = await _register(client, member)

    await client.post("/orgs", json={"name": "Joinable Org"}, headers=_auth(owner_token))
    invite = await client.post("/orgs/invites", json={"max_uses": 1}, headers=_auth(owner_token))
    assert invite.status_code == 200
    code = invite.json()["code"]

    join = await client.post("/orgs/join", json={"code": code}, headers=_auth(member_token))
    assert join.status_code == 200, join.text
    assert join.json()["org"]["role"] == "member"

    # Invite is single-use — a second join attempt with the same code fails.
    other = f"orgmember2_{uuid.uuid4().hex[:8]}"
    other_token = await _register(client, other)
    join2 = await client.post("/orgs/join", json={"code": code}, headers=_auth(other_token))
    assert join2.status_code == 400


@pytest.mark.asyncio
async def test_join_with_invalid_code_rejected(client, db):
    user = f"orguser_{uuid.uuid4().hex[:8]}"
    token = await _register(client, user)
    resp = await client.post("/orgs/join", json={"code": "not-a-real-code"}, headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_members_roster_has_no_cognitive_data_fields(client, db):
    owner = f"orgowner_{uuid.uuid4().hex[:8]}"
    owner_token = await _register(client, owner)
    await client.post("/orgs", json={"name": "Roster Org"}, headers=_auth(owner_token))

    resp = await client.get("/orgs/members", headers=_auth(owner_token))
    assert resp.status_code == 200
    members = resp.json()["members"]
    assert len(members) == 1
    allowed_keys = {"username", "display_name", "org_role", "created_at"}
    for m in members:
        assert set(m.keys()) <= allowed_keys


@pytest.mark.asyncio
async def test_only_owner_can_remove_members(client, db):
    owner = f"orgowner_{uuid.uuid4().hex[:8]}"
    member = f"orgmember_{uuid.uuid4().hex[:8]}"
    owner_token = await _register(client, owner)
    member_token = await _register(client, member)

    await client.post("/orgs", json={"name": "Remove Test Org"}, headers=_auth(owner_token))
    invite = await client.post("/orgs/invites", json={}, headers=_auth(owner_token))
    code = invite.json()["code"]
    await client.post("/orgs/join", json={"code": code}, headers=_auth(member_token))

    # Member cannot remove the owner.
    forbidden = await client.request(
        "DELETE", f"/orgs/members/{owner}", headers=_auth(member_token),
    )
    assert forbidden.status_code == 403

    # Owner can remove the member.
    removed = await client.request(
        "DELETE", f"/orgs/members/{member}", headers=_auth(owner_token),
    )
    assert removed.status_code == 200

    roster = await client.get("/orgs/members", headers=_auth(owner_token))
    assert len(roster.json()["members"]) == 1


@pytest.mark.asyncio
async def test_owner_cannot_leave_while_other_members_present(client, db):
    owner = f"orgowner_{uuid.uuid4().hex[:8]}"
    member = f"orgmember_{uuid.uuid4().hex[:8]}"
    owner_token = await _register(client, owner)
    member_token = await _register(client, member)

    await client.post("/orgs", json={"name": "Leave Test Org"}, headers=_auth(owner_token))
    invite = await client.post("/orgs/invites", json={}, headers=_auth(owner_token))
    code = invite.json()["code"]
    await client.post("/orgs/join", json={"code": code}, headers=_auth(member_token))

    blocked = await client.post("/orgs/leave", headers=_auth(owner_token))
    assert blocked.status_code == 400

    # Member can leave freely.
    left = await client.post("/orgs/leave", headers=_auth(member_token))
    assert left.status_code == 200

    # Now the owner (sole member) can leave, which also deletes the org.
    solo_leave = await client.post("/orgs/leave", headers=_auth(owner_token))
    assert solo_leave.status_code == 200
    me = await client.get("/orgs/me", headers=_auth(owner_token))
    assert me.json()["org"] is None


@pytest.mark.asyncio
async def test_orgs_endpoints_require_auth(client, db):
    resp = await client.post("/orgs", json={"name": "No Auth Org"})
    assert resp.status_code == 401
    resp2 = await client.get("/orgs/members")
    assert resp2.status_code == 401
