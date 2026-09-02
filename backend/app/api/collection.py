"""Collection control API - stop and resume behavioural collection.

  GET  /collection/status   -> whether collection is running, and since when
  POST /collection/pause    -> stop it, or start it again

The product could already export everything it held and delete it. It could not
be told to stop watching, which for a behavioural tracker is the control that
most needs to exist.

The write uses enforce_write_match rather than the read-side check: pausing
someone else's collection, or quietly resuming it, is a change to their account
and needs the same authority as any other write to it.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from app.api.deps import enforce_write_match, resolve_user_id
from app.services import collection_control

logger = logging.getLogger(__name__)
router = APIRouter()


class PauseRequest(BaseModel):
    user_id: str
    paused: bool


@router.get("/collection/status")
async def collection_status(user_id: str = Depends(resolve_user_id)):
    """Whether events are being collected for this account."""
    return await collection_control.get_status(user_id)


@router.post("/collection/pause")
async def set_collection_paused(
    body: PauseRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Stop or resume collection. Does not delete anything already stored."""
    enforce_write_match(authorization, body.user_id)
    return await collection_control.set_paused(body.user_id, body.paused)
