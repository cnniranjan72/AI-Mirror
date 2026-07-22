import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
DEFAULT_OLLAMA_MODEL = "llama3.2"


async def openai_call(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    # A model id may arrive from a provider-agnostic caller (e.g. the verbalizer
    # default). Reject ids that clearly belong to another provider.
    if not model or not model.lower().startswith(("gpt", "o1", "o3", "chatgpt")):
        model = DEFAULT_OPENAI_MODEL

    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.error("openai package not installed. Run `pip install openai`")
        raise

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        raise ValueError("OPENAI_API_KEY not configured")

    # Fail fast: on quota/rate errors we fall back to deterministic text, so
    # long SDK retry backoffs and hangs only add latency before that fallback.
    client = AsyncOpenAI(
        api_key=api_key,
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "0")),
        timeout=float(os.getenv("LLM_TIMEOUT", "30")),
    )
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


async def anthropic_call(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    # Ignore ids that belong to another provider (see openai_call).
    if not model or not model.lower().startswith("claude"):
        model = DEFAULT_ANTHROPIC_MODEL

    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.error("anthropic package not installed. Run `pip install anthropic`")
        raise

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = AsyncAnthropic(
        api_key=api_key,
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "0")),
        timeout=float(os.getenv("LLM_TIMEOUT", "30")),
    )
    response = await client.messages.create(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.content[0].text if response.content else ""


async def ollama_call(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """Local Ollama via its OpenAI-compatible endpoint (no quota, no cost).

    Reuses the OpenAI SDK pointed at Ollama's /v1 server. The model must be a
    tag that has been pulled locally (e.g. `ollama pull llama3.2`).
    """
    # gpt-*/claude-* defaults can leak in from a provider-agnostic caller.
    if not model or model.lower().startswith(("gpt", "o1", "o3", "chatgpt", "claude")):
        model = os.getenv("LLM_MODEL_OLLAMA") or DEFAULT_OLLAMA_MODEL

    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.error("openai package not installed. Run `pip install openai`")
        raise

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    client = AsyncOpenAI(
        base_url=base_url,
        api_key="ollama",  # required by the SDK but ignored by Ollama
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "0")),
        timeout=float(os.getenv("LLM_TIMEOUT", "120")),  # local CPU can be slow
    )
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def get_llm_call(provider: Optional[str] = None):
    provider = provider or os.getenv("LLM_PROVIDER", "").lower()
    if provider == "anthropic":
        return anthropic_call
    if provider == "ollama":
        return ollama_call
    return openai_call