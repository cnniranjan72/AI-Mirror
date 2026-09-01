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
from app.services import algorithmic_mirror

logger = logging.getLogger(__name__)
router = APIRouter()


async def _estimate_coverage(user_id: str) -> Optional[float]:
    """Coverage on the same five signals the Report page discloses.

    Recomputed here rather than read from the client so the verdict gate cannot
    be lifted by a caller passing a flattering number.
    """
    try:
        row = await fetchrow(
            """
            SELECT
              (SELECT COUNT(*) FROM events            WHERE user_id = $1) AS events,
              (SELECT COUNT(*) FROM behavior_objects  WHERE user_id = $1) AS topics,
              (SELECT COUNT(*) FROM evidence          WHERE user_id = $1) AS evidence,
              (SELECT COUNT(*) FROM inferences        WHERE user_id = $1) AS inferences,
              (SELECT COUNT(*) FROM identity_snapshots WHERE user_id = $1) AS snapshots
            """,
            user_id,
        )
        if not row:
            return None
        targets = {"events": 200, "topics": 12, "evidence": 40, "inferences": 8, "snapshots": 5}
        ratios = [min(1.0, (row[key] or 0) / target) for key, target in targets.items()]
        return sum(ratios) / len(ratios)
    except Exception as e:
        # Coverage is a gate on how confidently the report speaks, so failing
        # to compute it must make the report MORE cautious, not less: None
        # marks the verdict unreliable downstream.
        logger.warning("Could not estimate coverage for %s: %s", user_id, e)
        return None


@router.get("/mirror/report")
async def mirror_report(user_id: str = Query(default="default"), authorization: Optional[str] = Header(default=None)):
    resolved = await resolve_user_id(user_id=user_id, authorization=authorization)
    coverage = await _estimate_coverage(resolved)
    return await algorithmic_mirror.build_mirror_report(resolved, coverage=coverage)


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
