"""
Privacy API — export and permanently delete everything this platform holds
for a user. See app/services/data_privacy.py.
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import data_privacy

logger = logging.getLogger(__name__)
router = APIRouter()


class DeleteConfirmation(BaseModel):
    user_id: str
    confirm_user_id: str


@router.get("/privacy/export-all")
async def export_all_data(user_id: str = Query(default="default")):
    """Every row this platform holds for this user, across every table."""
    return await data_privacy.export_all_user_data(user_id)


@router.post("/privacy/delete-all-data")
async def delete_all_data(body: DeleteConfirmation):
    """Permanently delete every row for this user. Requires the caller to
    echo the exact user_id back as confirm_user_id — a lightweight
    type-to-confirm guard against an accidental click triggering an
    irreversible deletion."""
    if body.confirm_user_id != body.user_id:
        raise HTTPException(status_code=400, detail="confirm_user_id does not match user_id")
    deleted = await data_privacy.delete_all_user_data(body.user_id)
    total = sum(v for v in deleted.values() if v > 0)
    return {"user_id": body.user_id, "deleted_rows_by_table": deleted, "total_deleted": total}
