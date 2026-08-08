"""
Resolves a user's own LLM provider configuration (set via /settings/llm),
if they have one — the pipeline falls back to the server's shared
LLM_PROVIDER/*_API_KEY env vars when a user hasn't configured anything,
exactly like today's behavior.
"""
from typing import Any, Dict, Optional

from app.db.postgres import execute, fetchrow
from app.services import crypto


async def get_resolved_llm_config(user_id: str) -> Optional[Dict[str, Any]]:
    """None if the user has no override configured — caller should fall
    back to the server default in that case."""
    row = await fetchrow(
        "SELECT llm_provider, llm_api_key_encrypted, llm_base_url, llm_model "
        "FROM users WHERE username = $1",
        user_id,
    )
    if not row or not row["llm_provider"]:
        return None
    return {
        "provider": row["llm_provider"],
        "api_key": crypto.decrypt(row["llm_api_key_encrypted"]) if row["llm_api_key_encrypted"] else None,
        "base_url": row["llm_base_url"],
        "model": row["llm_model"],
    }


async def get_settings_preview(user_id: str) -> Dict[str, Any]:
    """Never returns the decrypted key — just enough to render Settings."""
    row = await fetchrow(
        "SELECT llm_provider, llm_api_key_encrypted, llm_base_url, llm_model "
        "FROM users WHERE username = $1",
        user_id,
    )
    if not row:
        return {"provider": None, "has_key": False, "key_preview": None, "base_url": None, "model": None}

    key_preview = None
    if row["llm_api_key_encrypted"]:
        key = crypto.decrypt(row["llm_api_key_encrypted"])
        key_preview = f"{key[:3]}...{key[-4:]}" if len(key) > 7 else "***"

    return {
        "provider": row["llm_provider"],
        "has_key": bool(row["llm_api_key_encrypted"]),
        "key_preview": key_preview,
        "base_url": row["llm_base_url"],
        "model": row["llm_model"],
    }


async def set_llm_settings(
    user_id: str, provider: str, api_key: Optional[str], base_url: Optional[str], model: Optional[str],
) -> None:
    encrypted = crypto.encrypt(api_key) if api_key else None
    await execute(
        "UPDATE users SET llm_provider = $1, llm_api_key_encrypted = $2, llm_base_url = $3, llm_model = $4 "
        "WHERE username = $5",
        provider, encrypted, base_url, model, user_id,
    )


async def clear_llm_settings(user_id: str) -> None:
    await execute(
        "UPDATE users SET llm_provider = NULL, llm_api_key_encrypted = NULL, llm_base_url = NULL, llm_model = NULL "
        "WHERE username = $1",
        user_id,
    )
