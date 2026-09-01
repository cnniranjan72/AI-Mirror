"""
Per-user AI provider settings — lets a user bring their own OpenAI/
Anthropic/Gemini key, or point at a reachable Ollama-compatible endpoint,
instead of relying solely on the server's shared key. See
app/services/user_llm_config.py for how this gets resolved at query time
and verbalizer/llm_provider.py for the provider call functions themselves.

  GET    /settings/llm   -> {provider, has_key, key_preview, base_url, model}
  POST   /settings/llm   {provider, api_key?, base_url?, model?} -> stores it
  DELETE /settings/llm   -> clears it (revert to the server default)
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import require_auth
from app.services import user_llm_config
from verbalizer.llm_provider import DEFAULT_MODEL_BY_PROVIDER

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_PROVIDERS = set(DEFAULT_MODEL_BY_PROVIDER.keys())


class LlmSettingsRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


@router.get("/settings/llm")
async def get_llm_settings(username: str = Depends(require_auth)):
    return await user_llm_config.get_settings_preview(username)


@router.post("/settings/llm")
async def set_llm_settings(body: LlmSettingsRequest, username: str = Depends(require_auth)):
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"provider must be one of {sorted(VALID_PROVIDERS)}")
    if body.provider != "ollama" and not body.api_key:
        raise HTTPException(status_code=400, detail="api_key is required for this provider")

    await user_llm_config.set_llm_settings(username, body.provider, body.api_key, body.base_url, body.model)
    logger.info("llm_settings updated for %s (provider=%s)", username, body.provider)
    return await user_llm_config.get_settings_preview(username)


@router.get("/settings/llm/status")
async def llm_status():
    """Whether answers are currently being phrased by a language model.

    Unauthenticated on purpose: it exposes no key material and no user data,
    and the Chat page needs it to caption its own answers honestly for
    signed-out demo visitors too.
    """
    from verbalizer.verbalizer import get_verbalizer

    return get_verbalizer().phrasing_status()


@router.delete("/settings/llm")
async def clear_llm_settings(username: str = Depends(require_auth)):
    await user_llm_config.clear_llm_settings(username)
    return {"cleared": True}
