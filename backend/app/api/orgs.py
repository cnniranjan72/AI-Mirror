"""
Organizations — a seat/roster grouping layer above individual user accounts,
modeled on how Slack/Notion workspaces work: an owner manages membership and
billing, but never gets a window into what a member actually does inside
their own account.

Deliberate privacy boundary, worth restating here since it's easy to erode
by accident later: every query in this file touches users/organizations/
org_invites only. None of it ever joins against behavior_objects, evidence,
inferences, reflections, self_models, or identity_snapshots. Those stay
scoped to user_id and enforced by enforce_user_match/enforce_write_match
exactly as before — an org membership grants zero additional data access.

  POST   /orgs                  {name}              -> create (caller becomes owner)
  POST   /orgs/invites           {max_uses?, expires_hours?} -> {code, expires_at, max_uses}
  GET    /orgs/invites                               -> list this org's active invites (owner only)
  POST   /orgs/join              {code}              -> join via invite code
  GET    /orgs/me                                    -> {org} or {org: null}
  GET    /orgs/members                                -> roster (no cognitive data)
  DELETE /orgs/members/{username}                     -> remove a member (owner only)
  POST   /orgs/leave                                  -> leave (owners blocked unless sole member)
"""
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import require_auth
from app.db.postgres import execute, fetch, fetchrow

logger = logging.getLogger(__name__)
router = APIRouter()


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "org"
    return base[:40]


async def _unique_slug(name: str) -> str:
    base = _slugify(name)
    slug = base
    n = 1
    while await fetchrow("SELECT id FROM organizations WHERE slug = $1", slug):
        n += 1
        slug = f"{base}-{n}"
    return slug


async def _my_org_row(username: str):
    return await fetchrow(
        "SELECT org_id, org_role FROM users WHERE username = $1", username,
    )


class CreateOrgRequest(BaseModel):
    name: str


class CreateInviteRequest(BaseModel):
    max_uses: Optional[int] = 1
    expires_hours: int = 168  # 7 days


class JoinOrgRequest(BaseModel):
    code: str


@router.post("/orgs")
async def create_org(body: CreateOrgRequest, username: str = Depends(require_auth)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    me = await _my_org_row(username)
    if me and me["org_id"]:
        raise HTTPException(status_code=400, detail="You already belong to an organization")

    slug = await _unique_slug(name)
    row = await fetchrow(
        "INSERT INTO organizations (name, slug, owner_username) VALUES ($1, $2, $3) "
        "RETURNING id, name, slug, owner_username, created_at",
        name, slug, username,
    )
    await execute(
        "UPDATE users SET org_id = $1, org_role = 'owner' WHERE username = $2",
        row["id"], username,
    )
    return {"org": {
        "id": row["id"], "name": row["name"], "slug": row["slug"],
        "owner_username": row["owner_username"], "role": "owner", "member_count": 1,
    }}


@router.post("/orgs/invites")
async def create_invite(body: CreateInviteRequest, username: str = Depends(require_auth)):
    me = await _my_org_row(username)
    if not me or not me["org_id"]:
        raise HTTPException(status_code=400, detail="You don't belong to an organization")
    if me["org_role"] != "owner":
        raise HTTPException(status_code=403, detail="Only the org owner can create invites")

    code = secrets.token_urlsafe(9)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=body.expires_hours) if body.expires_hours else None
    await execute(
        "INSERT INTO org_invites (code, org_id, created_by, expires_at, max_uses) "
        "VALUES ($1, $2, $3, $4, $5)",
        code, me["org_id"], username, expires_at, body.max_uses,
    )
    return {"code": code, "expires_at": expires_at.isoformat() if expires_at else None, "max_uses": body.max_uses}


@router.get("/orgs/invites")
async def list_invites(username: str = Depends(require_auth)):
    me = await _my_org_row(username)
    if not me or not me["org_id"]:
        raise HTTPException(status_code=400, detail="You don't belong to an organization")
    if me["org_role"] != "owner":
        raise HTTPException(status_code=403, detail="Only the org owner can view invites")

    rows = await fetch(
        "SELECT code, created_by, created_at, expires_at, max_uses, use_count "
        "FROM org_invites WHERE org_id = $1 ORDER BY created_at DESC",
        me["org_id"],
    )
    return {"invites": [dict(r) for r in rows]}


@router.post("/orgs/join")
async def join_org(body: JoinOrgRequest, username: str = Depends(require_auth)):
    me = await _my_org_row(username)
    if me and me["org_id"]:
        raise HTTPException(status_code=400, detail="You already belong to an organization — leave it first")

    invite = await fetchrow(
        "SELECT code, org_id, expires_at, max_uses, use_count FROM org_invites WHERE code = $1",
        body.code,
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    if invite["expires_at"] and invite["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This invite has expired")
    if invite["max_uses"] is not None and invite["use_count"] >= invite["max_uses"]:
        raise HTTPException(status_code=400, detail="This invite has already been used")

    await execute(
        "UPDATE users SET org_id = $1, org_role = 'member' WHERE username = $2",
        invite["org_id"], username,
    )
    await execute("UPDATE org_invites SET use_count = use_count + 1 WHERE code = $1", body.code)

    org = await fetchrow("SELECT id, name, slug, owner_username FROM organizations WHERE id = $1", invite["org_id"])
    return {"org": {**dict(org), "role": "member"}}


@router.get("/orgs/me")
async def get_my_org(username: str = Depends(require_auth)):
    me = await _my_org_row(username)
    if not me or not me["org_id"]:
        return {"org": None}

    org = await fetchrow(
        "SELECT id, name, slug, owner_username, created_at FROM organizations WHERE id = $1",
        me["org_id"],
    )
    if not org:
        return {"org": None}
    count_row = await fetchrow("SELECT COUNT(*) AS c FROM users WHERE org_id = $1", me["org_id"])
    return {"org": {
        "id": org["id"], "name": org["name"], "slug": org["slug"],
        "owner_username": org["owner_username"], "role": me["org_role"],
        "member_count": count_row["c"],
    }}


@router.get("/orgs/members")
async def list_members(username: str = Depends(require_auth)):
    me = await _my_org_row(username)
    if not me or not me["org_id"]:
        raise HTTPException(status_code=400, detail="You don't belong to an organization")

    rows = await fetch(
        "SELECT username, display_name, org_role, created_at FROM users "
        "WHERE org_id = $1 ORDER BY org_role, created_at",
        me["org_id"],
    )
    return {"members": [dict(r) for r in rows]}


@router.delete("/orgs/members/{target_username}")
async def remove_member(target_username: str, username: str = Depends(require_auth)):
    me = await _my_org_row(username)
    if not me or not me["org_id"]:
        raise HTTPException(status_code=400, detail="You don't belong to an organization")
    if me["org_role"] != "owner":
        raise HTTPException(status_code=403, detail="Only the org owner can remove members")
    if target_username == username:
        raise HTTPException(status_code=400, detail="Use POST /orgs/leave to remove yourself")

    target = await fetchrow("SELECT org_id FROM users WHERE username = $1", target_username)
    if not target or target["org_id"] != me["org_id"]:
        raise HTTPException(status_code=404, detail="That user is not a member of your organization")

    await execute(
        "UPDATE users SET org_id = NULL, org_role = NULL WHERE username = $1",
        target_username,
    )
    return {"removed": target_username}


@router.post("/orgs/leave")
async def leave_org(username: str = Depends(require_auth)):
    me = await _my_org_row(username)
    if not me or not me["org_id"]:
        raise HTTPException(status_code=400, detail="You don't belong to an organization")

    count_row = await fetchrow("SELECT COUNT(*) AS c FROM users WHERE org_id = $1", me["org_id"])
    if me["org_role"] == "owner" and count_row["c"] > 1:
        raise HTTPException(
            status_code=400,
            detail="Remove all other members before leaving as owner (ownership transfer isn't supported yet)",
        )

    org_id = me["org_id"]
    await execute("UPDATE users SET org_id = NULL, org_role = NULL WHERE username = $1", username)
    if me["org_role"] == "owner":
        # sole member was the owner leaving — the org has no one left in it
        await execute("DELETE FROM organizations WHERE id = $1", org_id)
    return {"left": True}
