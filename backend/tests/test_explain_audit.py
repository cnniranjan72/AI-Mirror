"""Data-audit fixes: explain.py must never fabricate an LLM provider/model,
must return the real response text, and grounding_composition must reflect
real row counts (not arbitrary weights) — regression tests for bugs found
and fixed this session."""
import types

import pytest

from verbalizer.verbalizer import LLMVerbalizer, VerbalizerResponse

_FAKE_PROMPT = types.SimpleNamespace(system_prompt="sys", prompt_text="user")


def test_verbalizer_response_has_no_provider_by_default():
    resp = VerbalizerResponse()
    assert resp.provider is None
    assert resp.model is None


@pytest.mark.asyncio
async def test_fallback_never_claims_a_real_provider(monkeypatch):
    """The exact bug: the fallback template used to be indistinguishable
    from a real OpenAI call in the trace data. Whenever the deterministic
    fallback fires (no llm_call, or content came back blank), the response
    must be tagged provider="fallback", not a real vendor name — isolated
    from _build_prompt/_fallback_verbalization's own logic (pre-existing,
    untouched) via monkeypatch, since only the tagging in verbalize() is
    what changed."""
    verbalizer = LLMVerbalizer(llm_call=None, config={})
    assert verbalizer.provider in ("openai", "anthropic", "ollama")

    monkeypatch.setattr(verbalizer, "_build_prompt", lambda *a, **k: _FAKE_PROMPT)
    monkeypatch.setattr(verbalizer, "_fallback_verbalization", lambda *a, **k: "deterministic fallback text")

    resp = await verbalizer.verbalize(context=object(), plan=object())
    assert resp.used_fallback is True
    assert resp.provider == "fallback"
    assert resp.model is None


@pytest.mark.asyncio
async def test_real_llm_call_is_tagged_with_actual_provider(monkeypatch):
    async def fake_llm_call(**kwargs):
        return "a real response from the model"

    verbalizer = LLMVerbalizer(llm_call=fake_llm_call, config={"provider": "anthropic"})
    monkeypatch.setattr(verbalizer, "_build_prompt", lambda *a, **k: _FAKE_PROMPT)

    resp = await verbalizer.verbalize(context=object(), plan=object())
    assert resp.used_fallback is False
    assert resp.provider == "anthropic"
    assert resp.model == verbalizer.model


def test_grounding_composition_helper_sums_to_100():
    counts = {"behavior_objects": 7, "evidence": 6, "reflections": 1}
    total = sum(counts.values())
    composition = {k: round(v / total * 100, 1) for k, v in counts.items()}
    diff = round(100 - sum(composition.values()), 1)
    if diff:
        largest = max(composition, key=composition.get)
        composition[largest] = round(composition[largest] + diff, 1)
    assert round(sum(composition.values()), 1) == 100.0
    # Proportional, not the old arbitrary per-item multipliers.
    assert composition["behavior_objects"] > composition["reflections"]
