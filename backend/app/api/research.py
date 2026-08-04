"""
Research API — opt-in status and the bulk de-identified export.
See app/services/research_export.py for the anonymization method and the
exact allowlisted fields included.

  GET  /research/status   -> {opted_in: bool} for the caller
  POST /research/opt-in   {opt_in: bool} -> {opted_in: bool}
  GET  /research/export   -> bulk de-identified dataset (any authenticated user)
"""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_auth
from app.services import research_export

logger = logging.getLogger(__name__)
router = APIRouter()


class OptInRequest(BaseModel):
    opt_in: bool


@router.get("/research/status")
async def get_status(username: str = Depends(require_auth)):
    return {"opted_in": await research_export.get_opt_in(username)}


@router.post("/research/opt-in")
async def set_opt_in(body: OptInRequest, username: str = Depends(require_auth)):
    await research_export.set_opt_in(username, body.opt_in)
    logger.info("research_opt_in set to %s for %s", body.opt_in, username)
    return {"opted_in": body.opt_in}


@router.get("/research/export")
async def export_dataset(_username: str = Depends(require_auth)):
    """Bulk de-identified export across every opted-in user. Requires being
    signed in (any account) so this isn't a fully anonymous scrape target,
    but there's no separate researcher-approval gate — self-serve by design,
    same as the rest of the product."""
    return await research_export.build_export()
