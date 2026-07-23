"""
Chat conversation memory — persistent, per-conversation turn history so the
character can recall earlier turns within a conversation.
"""
import logging
from typing import Dict, List, Any, Optional

from app.db.postgres import fetch, fetchrow

logger = logging.getLogger(__name__)


async def save_message(
    user_id: str,
    conversation_id: str,
    role: str,
    content: str,
    trace_id: Optional[str] = None,
) -> int:
    row = await fetchrow(
        """
        INSERT INTO chat_messages (user_id, conversation_id, role, content, trace_id)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        user_id, conversation_id, role, content or "", trace_id,
    )
    return row["id"]


async def get_history(
    user_id: str,
    conversation_id: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Return the conversation's turns in chronological order (oldest first)."""
    rows = await fetch(
        """
        SELECT id, role, content, trace_id, created_at
        FROM chat_messages
        WHERE user_id = $1 AND conversation_id = $2
        ORDER BY created_at DESC, id DESC
        LIMIT $3
        """,
        user_id, conversation_id, limit,
    )
    ordered = list(reversed(rows))
    return [{
        "id": r["id"],
        "role": r["role"],
        "content": r["content"],
        "trace_id": r["trace_id"],
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
    } for r in ordered]


async def get_recent_turns(user_id: str, conversation_id: str, max_turns: int = 6) -> List[Dict[str, str]]:
    """Compact {role, content} pairs for prompting the LLM (most recent turns)."""
    history = await get_history(user_id, conversation_id, limit=max_turns * 2)
    return [{"role": h["role"], "content": h["content"]} for h in history]
