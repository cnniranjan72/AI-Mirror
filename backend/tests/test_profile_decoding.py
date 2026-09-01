"""GET /profile must survive a user who actually has a persona.

No JSON codec is registered on the connection pool (app/db/postgres.py), so
asyncpg returns every JSONB column as raw text. explain.py already works
around that with _parse_json_fields; get_latest_persona did not, and handed
the strings straight to rl_layer.compute_alignment, which does:

    traits = persona.get("traits", {})
    attention = traits.get("attention_score", 0)

Live, that produced 500 "'str' object has no attribute 'get'" on /profile for
every user who HAD a persona, and 200 for everyone who did not — so the
endpoint looked healthy on a fresh account and broke precisely when it had
something to say. It was reaching production undetected because nothing
exercised the populated path.
"""
import pytest

from app.services import rl_layer
from app.services.persona import _decode


class TestDecode:
    def test_parses_a_json_object_string(self):
        assert _decode('{"attention_score": 0.4}', {}) == {"attention_score": 0.4}

    def test_parses_a_json_array_string(self):
        assert _decode('["a", "b"]', []) == ["a", "b"]

    def test_passes_through_an_already_decoded_value(self):
        """A codec could be registered later, or a caller may pass a dict."""
        assert _decode({"x": 1}, {}) == {"x": 1}
        assert _decode([1, 2], []) == [1, 2]

    def test_null_becomes_the_fallback(self):
        assert _decode(None, {}) == {}
        assert _decode(None, []) == []

    def test_unparseable_text_becomes_the_fallback_not_an_exception(self):
        """A malformed row must not take the whole endpoint down."""
        assert _decode("not json at all", {}) == {}
        assert _decode("", []) == []


class TestTheEndpointPathThatBroke:
    def test_compute_alignment_works_on_decoded_traits(self):
        persona = {"traits": _decode('{"attention_score": 0.5, "engagement_score": 0.4,'
                                     ' "content_diversity": 0.3, "curiosity_score": 0.2}', {})}
        result = rl_layer.compute_alignment(persona, {"total_events": 10, "avg_watch_time": 12})

        assert 0.0 <= result["overall_score"] <= 1.0
        assert set(result["dimensions"]) == set(rl_layer.ALIGNMENT_DIMENSIONS)

    def test_the_raw_string_is_what_used_to_break_it(self):
        """Documents the actual failure, so the decode step cannot be removed
        as redundant."""
        with pytest.raises(AttributeError, match="'str' object has no attribute 'get'"):
            rl_layer.compute_alignment({"traits": '{"attention_score": 0.5}'}, {})

    def test_a_persona_with_no_traits_still_produces_alignment(self):
        result = rl_layer.compute_alignment({"traits": _decode(None, {})}, {"total_events": 0})
        assert 0.0 <= result["overall_score"] <= 1.0

    def test_the_context_key_stays_within_the_valid_set(self):
        """compute_alignment feeds context_key, which feeds the shared policy
        table — a decoding change must not start inventing contexts."""
        persona = {"traits": {"attention_score": 0.1, "engagement_score": 0.9,
                              "content_diversity": 0.5, "curiosity_score": 0.5}}
        alignment = rl_layer.compute_alignment(persona, {"total_events": 5})
        assert rl_layer.context_key(alignment) in rl_layer.VALID_CONTEXT_KEYS
