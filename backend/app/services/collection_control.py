"""Whether the system is currently allowed to collect for a given user.

The product could export everything it held and delete it, and could opt out of
research sharing. It could not be told to stop watching. A behavioural tracker
that cannot be switched off is the thing this product criticises platforms for,
and withdrawing consent is meant to be as easy as giving it.

The switch is enforced on the SERVER, at the ingest endpoint. A pause
implemented in the extension or the dashboard would be a request, not a
guarantee: anything holding the user_id could keep posting. Enforcing it here
means the answer is the same no matter what is asking.

Pausing is not deleting, and the two are deliberately separate. Events already
collected remain until the user deletes them, which is what the interface says.
A switch that silently destroyed history would be a far worse surprise than one
that only stops the flow.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from app.db.postgres import execute, fetchrow

logger = logging.getLogger(__name__)


async def is_paused(user_id: str) -> bool:
    """True when this user has stopped collection.

    Fails OPEN on a database error - deliberately, and it is the uncomfortable
    direction. Failing closed would silently stop collecting for everyone the
    moment this table became unreadable, and a tracker that quietly stops is
    harder to notice than one that keeps going. The error is logged so the
    failure is visible rather than absorbed.
    """
    try:
        row = await fetchrow(
            "SELECT paused FROM collection_settings WHERE user_id = $1", user_id
        )
    except Exception as e:
        logger.error("collection_settings unreadable for %s: %s", user_id, e)
        return False
    return bool(row and row["paused"])


async def set_paused(user_id: str, paused: bool) -> Dict[str, Any]:
    """Start or stop collection for this user."""
    await execute(
        """
        INSERT INTO collection_settings (user_id, paused, paused_at, updated_at)
        VALUES ($1, $2, CASE WHEN $2 THEN NOW() ELSE NULL END, NOW())
        ON CONFLICT (user_id) DO UPDATE
            SET paused = EXCLUDED.paused,
                -- Only reset the clock when the state actually changes, so
                -- pausing twice does not make a long pause look new.
                paused_at = CASE
                    WHEN EXCLUDED.paused AND NOT collection_settings.paused THEN NOW()
                    WHEN EXCLUDED.paused THEN collection_settings.paused_at
                    ELSE NULL
                END,
                updated_at = NOW()
        """,
        user_id, paused,
    )
    logger.info("Collection %s for %s", "paused" if paused else "resumed", user_id)
    return await get_status(user_id)


async def get_status(user_id: str) -> Dict[str, Any]:
    """The current state, plus what it does and does not cover.

    The scope sentence travels with the status rather than living only in the
    page that happens to render it, so any surface showing this cannot imply
    the pause is doing more than it does.
    """
    try:
        row = await fetchrow(
            "SELECT paused, paused_at FROM collection_settings WHERE user_id = $1",
            user_id,
        )
    except Exception as e:
        logger.error("collection_settings unreadable for %s: %s", user_id, e)
        row = None

    paused = bool(row and row["paused"])
    return {
        "user_id": user_id,
        "paused": paused,
        "paused_at": row["paused_at"].isoformat() if row and row["paused_at"] else None,
        "note": (
            "New events are being rejected. Everything collected before now is "
            "still stored — pausing does not delete it."
            if paused else
            "Events are being collected. Pausing stops new ones; it does not "
            "delete anything already held."
        ),
    }
