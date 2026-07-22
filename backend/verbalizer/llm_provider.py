import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


async def openai_call(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4",
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.error("openai package not installed. Run `pip install openai`")
        raise

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        raise ValueError("OPENAI_API_KEY not configured")

    client = AsyncOpenAI(api_key=api_key)
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
    model: str = "claude-3-sonnet-20241022",
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.error("anthropic package not installed. Run `pip install anthropic`")
        raise

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.content[0].text if response.content else ""


def get_llm_call(provider: Optional[str] = None):
    provider = provider or os.getenv("LLM_PROVIDER", "").lower()
    if provider == "anthropic":
        return anthropic_call
    return openai_call