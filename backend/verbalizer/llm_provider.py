import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OLLAMA_MODEL = "llama3.2"

DEFAULT_MODEL_BY_PROVIDER = {
    "openai": DEFAULT_OPENAI_MODEL,
    "anthropic": DEFAULT_ANTHROPIC_MODEL,
    "gemini": DEFAULT_GEMINI_MODEL,
    "ollama": DEFAULT_OLLAMA_MODEL,
}


def resolve_provider(provider: Optional[str] = None) -> str:
    """Same resolution get_llm_call uses, exposed separately so callers can
    know (and honestly report) which provider will actually be called."""
    provider = provider or os.getenv("LLM_PROVIDER", "").lower()
    return provider if provider in DEFAULT_MODEL_BY_PROVIDER else "openai"


async def openai_call(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    api_key: Optional[str] = None,
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

    # A per-user key (from users.llm_api_key_encrypted, decrypted by the
    # caller) takes priority over the server's shared key.
    api_key = api_key or os.getenv("OPENAI_API_KEY")
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
    api_key: Optional[str] = None,
) -> str:
    # Ignore ids that belong to another provider (see openai_call).
    if not model or not model.lower().startswith("claude"):
        model = DEFAULT_ANTHROPIC_MODEL

    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.error("anthropic package not installed. Run `pip install anthropic`")
        raise

    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
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


async def gemini_call(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    api_key: Optional[str] = None,
) -> str:
    if not model or not model.lower().startswith("gemini"):
        model = DEFAULT_GEMINI_MODEL

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.error("google-genai package not installed. Run `pip install google-genai`")
        raise

    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set")
        raise ValueError("GEMINI_API_KEY not configured")

    client = genai.Client(api_key=api_key)
    response = await client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    return response.text or ""


async def ollama_call(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    """Ollama (or any OpenAI-compatible endpoint) via the OpenAI SDK pointed
    at a custom base_url. A deployed backend can't reach a user's own
    laptop, so base_url must be reachable from wherever this server runs —
    it only defaults to localhost when the backend itself is being run
    locally. The model must be a tag already pulled on that server
    (e.g. `ollama pull llama3.2`).
    """
    # gpt-*/claude-*/gemini-* defaults can leak in from a provider-agnostic caller.
    if not model or model.lower().startswith(("gpt", "o1", "o3", "chatgpt", "claude", "gemini")):
        model = os.getenv("LLM_MODEL_OLLAMA") or DEFAULT_OLLAMA_MODEL

    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.error("openai package not installed. Run `pip install openai`")
        raise

    base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key or "ollama",  # required by the SDK; ignored by stock Ollama
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
    provider = resolve_provider(provider)
    if provider == "anthropic":
        return anthropic_call
    if provider == "gemini":
        return gemini_call
    if provider == "ollama":
        return ollama_call
    return openai_call
