"""verbalize()'s override param must route to the user's own configured
provider/key instead of the server-wide default — the actual mechanism
/settings/llm exists to control. Regression coverage for the base_url
kwarg guard (only valid for ollama_call; passing it to openai_call etc.
would raise a TypeError).
"""
import types

import pytest

from verbalizer.verbalizer import LLMVerbalizer

_FAKE_PROMPT = types.SimpleNamespace(system_prompt="sys", prompt_text="user")


@pytest.mark.asyncio
async def test_override_routes_to_the_overridden_provider(monkeypatch):
    calls = []

    async def fake_anthropic_call(**kwargs):
        calls.append(("anthropic", kwargs))
        return "response from anthropic"

    async def fake_openai_call(**kwargs):
        calls.append(("openai", kwargs))
        return "response from openai (server default)"

    # Server default is openai; the user's override should still win.
    verbalizer = LLMVerbalizer(llm_call=fake_openai_call, config={"provider": "openai"})
    monkeypatch.setattr(verbalizer, "_build_prompt", lambda *a, **k: _FAKE_PROMPT)

    import verbalizer.verbalizer as verbalizer_module
    monkeypatch.setattr(verbalizer_module, "get_llm_call", lambda provider: fake_anthropic_call)

    resp = await verbalizer.verbalize(
        context=object(), plan=object(),
        override={"provider": "anthropic", "api_key": "sk-ant-user-key", "base_url": None, "model": None},
    )

    assert resp.provider == "anthropic"
    assert len(calls) == 1
    assert calls[0][0] == "anthropic"
    assert calls[0][1]["api_key"] == "sk-ant-user-key"
    assert "base_url" not in calls[0][1]


@pytest.mark.asyncio
async def test_no_override_uses_server_default(monkeypatch):
    calls = []

    async def fake_openai_call(**kwargs):
        calls.append(kwargs)
        return "server default response"

    verbalizer = LLMVerbalizer(llm_call=fake_openai_call, config={"provider": "openai"})
    monkeypatch.setattr(verbalizer, "_build_prompt", lambda *a, **k: _FAKE_PROMPT)

    resp = await verbalizer.verbalize(context=object(), plan=object(), override=None)

    assert resp.provider == "openai"
    assert len(calls) == 1
    # No override -> no api_key/base_url kwargs injected at all.
    assert "api_key" not in calls[0]
    assert "base_url" not in calls[0]


@pytest.mark.asyncio
async def test_ollama_override_passes_base_url(monkeypatch):
    calls = []

    async def fake_ollama_call(**kwargs):
        calls.append(kwargs)
        return "response from ollama"

    verbalizer = LLMVerbalizer(llm_call=None, config={"provider": "openai"})
    monkeypatch.setattr(verbalizer, "_build_prompt", lambda *a, **k: _FAKE_PROMPT)

    import verbalizer.verbalizer as verbalizer_module
    monkeypatch.setattr(verbalizer_module, "get_llm_call", lambda provider: fake_ollama_call)

    resp = await verbalizer.verbalize(
        context=object(), plan=object(),
        override={"provider": "ollama", "api_key": None, "base_url": "https://my-ollama.example.com/v1", "model": None},
    )

    assert resp.provider == "ollama"
    assert calls[0]["base_url"] == "https://my-ollama.example.com/v1"
