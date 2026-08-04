"""
Best-effort error recording: logs via the existing StructuredFormatter and
inserts into error_events, so a failure is queryable (GET /admin/errors)
instead of only living in a stdout log nobody's tailing. Recording an error
must never itself crash the request that triggered it — DB failures here are
swallowed after logging.
"""
import logging
import traceback
from typing import Optional

logger = logging.getLogger(__name__)


async def record_error(
    exc: Exception,
    *,
    trace_id: Optional[str] = None,
    user_id: Optional[str] = None,
    path: Optional[str] = None,
    method: Optional[str] = None,
    error_type: str = "unhandled_exception",
    message: Optional[str] = None,
) -> None:
    msg = message or str(exc)
    logger.error(
        "Recorded error: %s", msg,
        extra={"trace_id": trace_id, "user_id": user_id},
        exc_info=exc,
    )
    try:
        from app.db.postgres import execute
        stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[:8000]
        await execute(
            """
            INSERT INTO error_events (trace_id, user_id, path, method, error_type, message, stack)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            trace_id, user_id, path, method, error_type, msg[:2000], stack,
        )
    except Exception:
        logger.warning("Failed to persist error_event (best-effort, non-fatal)", exc_info=True)
