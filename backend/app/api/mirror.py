"""GET /mirror/report — the Algorithmic Mirror.

Compares what a platform claims about the user against what the user's own
behaviour actually evidences. Read-only; the claims themselves are stored by
the archive import.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Header, Query

from app.api.deps import resolve_user_id
from app.db.postgres import fetch, fetchrow
from app.services import algorithmic_mirror, interest_provenance

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/mirror/report")
async def mirror_report(user_id: str = Query(default="default"), authorization: Optional[str] = Header(default=None)):
    resolved = await resolve_user_id(user_id=user_id, authorization=authorization)
    # coverage is computed inside the service, so every caller (chat included)
    # is gated identically.
    return await algorithmic_mirror.build_mirror_report(resolved)


@router.get("/mirror/claims")
async def mirror_claims(user_id: str = Query(default="default"), authorization: Optional[str] = Header(default=None)):
    """The raw imported claims, unjudged — so a user can see exactly what their
    export contained before any comparison is applied to it."""
    resolved = await resolve_user_id(user_id=user_id, authorization=authorization)
    rows = await fetch(
        "SELECT platform, claim_type, raw_label, source_file, imported_at "
        "FROM platform_profile_claims WHERE user_id = $1 ORDER BY platform, label",
        resolved,
    )
    return {"user_id": resolved, "count": len(rows), "claims": [dict(r) for r in rows]}


@router.get("/provenance/report")
async def provenance_report(user_id: str = Query(default="default"), authorization: Optional[str] = Header(default=None)):
    """Interest Provenance: for each topic, evidence of seeking vs exposure."""
    resolved = await resolve_user_id(user_id=user_id, authorization=authorization)
    return await interest_provenance.build_provenance_report(resolved)


@router.get("/provenance/timeline")
async def provenance_timeline(user_id: str = Query(default="default"), authorization: Optional[str] = Header(default=None)):
    """When each topic arrived and how fast it took over, joined to whether it
    was ever sought out."""
    resolved = await resolve_user_id(user_id=user_id, authorization=authorization)
    return await interest_provenance.build_capture_timeline(resolved)
