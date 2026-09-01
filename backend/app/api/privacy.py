"""
Privacy API — export and permanently delete everything this platform holds
for a user. See app/services/data_privacy.py.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import enforce_write_match, resolve_user_id
from app.services import data_privacy

logger = logging.getLogger(__name__)
router = APIRouter()


class DeleteConfirmation(BaseModel):
    user_id: str
    confirm_user_id: str
    # Off by default: erasing what the system learned and deleting the account
    # are different requests, and the existing flow means the first. Opting in
    # also removes the login, email, password hash and stored LLM key.
    delete_account: bool = False


@router.get("/privacy/export-all")
async def export_all_data(user_id: str = Depends(resolve_user_id)):
    """Every row this platform holds for this user, across every table."""
    return await data_privacy.export_all_user_data(user_id)


@router.post("/privacy/delete-all-data")
async def delete_all_data(body: DeleteConfirmation, authorization: Optional[str] = Header(default=None)):
    """Permanently delete this user's behavioural data, and optionally the
    account itself. Requires the caller to echo the exact user_id back as
    confirm_user_id — a lightweight type-to-confirm guard against an
    accidental click triggering an irreversible deletion.

    The response always states what SURVIVED. The `users` row carries the
    email, display name, password hash and the user's own encrypted LLM API
    key, so a deletion that reported only its successes would be telling the
    user their data was gone while holding a third-party credential.
    """
    enforce_write_match(authorization, body.user_id)
    if body.confirm_user_id != body.user_id:
        raise HTTPException(status_code=400, detail="confirm_user_id does not match user_id")

    deleted = await data_privacy.delete_all_user_data(body.user_id)
    total = sum(v for v in deleted.values() if v > 0)
    response = {
        "user_id": body.user_id,
        "deleted_rows_by_table": deleted,
        "total_deleted": total,
    }

    if body.delete_account:
        account = await data_privacy.delete_account(body.user_id)
        response["account"] = account
        if not account.get("deleted") and account.get("reason") == "owns_organization":
            # The behavioural data IS gone; only the account survived. Say so
            # rather than returning a bare success.
            response["retained"] = await data_privacy.account_retention_note(body.user_id)
    else:
        response["retained"] = await data_privacy.account_retention_note(body.user_id)

    return response
