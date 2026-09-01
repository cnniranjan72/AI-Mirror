"""Deleting "everything" must not quietly keep the account.

The Settings page offers "Delete all my data" and says it removes "every row
... across every table ... everything". delete_all_user_data deliberately does
not touch the `users` row, and that row is not just a login: it carries the
email, the display name, the pbkdf2 password hash and - via
services/user_llm_config.py, which stores them as columns on `users` - the
user's own encrypted LLM API key.

So the copy promised total erasure while the system kept a third-party
credential. In a product whose entire argument is that platforms should be
held to their stated claims, that gap is the product failing its own test.

Two things are pinned here. The account can now actually be deleted, opt-in
and separately. And every deletion reports what SURVIVED, so the promise and
the rows cannot drift apart again without a test failing.
"""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import data_privacy


# -- Contract (no database) --------------------------------------------------

def test_account_fields_include_the_credentials():
    """If a credential column is added to `users` and not listed here, the
    retention note stops mentioning it and the report goes quiet."""
    assert {"password_hash", "salt", "llm_api_key_encrypted"} <= set(
        data_privacy.ACCOUNT_FIELDS
    )


def test_the_users_table_is_still_out_of_the_behavioural_sweep():
    """delete_all_user_data must NOT silently start deleting accounts - the
    two operations answer different requests."""
    assert "users" not in data_privacy.USER_DATA_TABLES


def test_deleting_the_account_is_opt_in():
    from app.api.privacy import DeleteConfirmation

    body = DeleteConfirmation(user_id="u", confirm_user_id="u")
    assert body.delete_account is False, "account deletion must never be the default"


# -- Behaviour (live database) -----------------------------------------------

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


async def _account_exists(db, username):
    from app.db.postgres import fetchval
    return await fetchval("SELECT COUNT(*) FROM users WHERE username = $1", username) > 0


@pytest.mark.db
@pytest.mark.asyncio
async def test_data_deletion_alone_reports_what_it_kept(db, client):
    """The regression: a bare success message while the account survives."""
    username = f"erase_{uuid.uuid4().hex[:8]}"
    token = await _register(client, username)
    try:
        resp = await client.post(
            "/privacy/delete-all-data",
            json={"user_id": username, "confirm_user_id": username},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["retained"]["account_exists"] is True
        # The credentials that survive must be named, not glossed over.
        assert "password_hash" in body["retained"]["retained"]
        assert await _account_exists(db, username)
    finally:
        await data_privacy.delete_account(username)


@pytest.mark.db
@pytest.mark.asyncio
async def test_opting_in_actually_removes_the_account(db, client):
    username = f"erase_{uuid.uuid4().hex[:8]}"
    token = await _register(client, username)
    try:
        resp = await client.post(
            "/privacy/delete-all-data",
            json={"user_id": username, "confirm_user_id": username, "delete_account": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["account"]["deleted"] is True
        assert not await _account_exists(db, username)
    finally:
        await data_privacy.delete_account(username)


@pytest.mark.db
@pytest.mark.asyncio
async def test_the_stored_llm_key_goes_with_the_account(db, client):
    """The sharpest version of the gap: an encrypted third-party API key
    surviving a deletion the user was told removed everything."""
    from app.db.postgres import execute, fetchval

    username = f"erase_{uuid.uuid4().hex[:8]}"
    token = await _register(client, username)
    sentinel = "gAAAAAB_not_a_real_key"
    try:
        await execute(
            "UPDATE users SET llm_api_key_encrypted = $1 WHERE username = $2",
            sentinel, username,
        )

        # Behavioural deletion alone leaves it, and says so.
        resp = await client.post(
            "/privacy/delete-all-data",
            json={"user_id": username, "confirm_user_id": username},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert "llm_api_key_encrypted" in resp.json()["retained"]["retained"]

        # Opting in removes it with the row.
        resp = await client.post(
            "/privacy/delete-all-data",
            json={"user_id": username, "confirm_user_id": username, "delete_account": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.json()["account"]["deleted"] is True
        assert await fetchval(
            "SELECT COUNT(*) FROM users WHERE llm_api_key_encrypted = $1", sentinel
        ) == 0
    finally:
        await data_privacy.delete_account(username)


@pytest.mark.db
@pytest.mark.asyncio
async def test_the_retention_note_never_leaks_the_values(db, client):
    """It names which fields survive. It must not echo a password hash or an
    API key into a response body."""
    from app.db.postgres import execute, fetchval

    username = f"erase_{uuid.uuid4().hex[:8]}"
    await _register(client, username)
    sentinel = "gAAAAAB_not_a_real_key"
    try:
        await execute(
            "UPDATE users SET llm_api_key_encrypted = $1 WHERE username = $2",
            sentinel, username,
        )
        note = await data_privacy.account_retention_note(username)
        assert sentinel not in str(note)

        hash_value = await fetchval(
            "SELECT password_hash FROM users WHERE username = $1", username
        )
        assert hash_value and hash_value not in str(note)
    finally:
        await data_privacy.delete_account(username)


@pytest.mark.db
@pytest.mark.asyncio
async def test_an_org_owner_cannot_delete_themselves_out_from_under_the_org(db, client):
    """organizations.owner_username is a foreign key into users, so this would
    fail anyway - but the real reason is that removing the owner silently
    would take the other members' workspace with it."""
    from app.db.postgres import execute

    username = f"erase_{uuid.uuid4().hex[:8]}"
    token = await _register(client, username)
    org_created = False
    try:
        resp = await client.post(
            "/orgs", params={"username": username}, json={"name": f"Org {username}"},
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            pytest.skip(f"org creation unavailable: {resp.status_code} {resp.text[:120]}")
        org_created = True

        result = await data_privacy.delete_account(username)
        assert result["deleted"] is False
        assert result["reason"] == "owns_organization"
        assert await _account_exists(db, username)
    finally:
        if org_created:
            await execute("DELETE FROM org_invites WHERE created_by = $1", username)
            await execute("UPDATE users SET org_id = NULL WHERE username = $1", username)
            await execute("DELETE FROM organizations WHERE owner_username = $1", username)
        await data_privacy.delete_account(username)
