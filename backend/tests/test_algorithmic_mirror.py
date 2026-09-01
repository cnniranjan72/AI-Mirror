"""The Algorithmic Mirror — verdict boundaries.

This feature accuses a platform of profiling someone inaccurately, so the tests
that matter are the ones that stop it overclaiming: what counts as support,
what is refused as untestable, and when the whole report declines to render a
verdict at all.

The pure logic (matching, non-testable detection) runs without a database; the
end-to-end report is db-marked.
"""
import pytest

from app.services.algorithmic_mirror import (
    _tokens, _is_non_testable, _match_claim, build_mirror_report,
    MIN_OBSERVATIONS_FOR_SUPPORT, MIN_COVERAGE_FOR_VERDICT,
)
from app.services.archive_import import normalize_claim_label, parse_archive

from tests.test_archive_import import _zip


def _behaviour(topic, occurrences, keywords=None):
    return {
        "topic": topic,
        "keywords": keywords or [topic],
        "occurrence_count": occurrences,
        "importance_score": 0.5,
        "confidence_score": 0.5,
    }


class TestTokenising:
    def test_drops_words_with_no_discriminating_power(self):
        """Without this, "Technology and other products" would match anything
        containing "and" or "other"."""
        assert _tokens("Technology and other products") == {"technology"}

    def test_case_and_punctuation_are_irrelevant(self):
        assert _tokens("Robotics!") == _tokens("robotics")

    def test_ignores_fragments(self):
        assert _tokens("AI & ML") == set()  # both under the 3-char floor


class TestNonTestableClaims:
    @pytest.mark.parametrize("label", [
        "away from family",
        "recently moved",
        "frequent travelers",
        "likely to buy a car",
        "household income: top 10%",
        "new parents",
        "operating system: android",
    ])
    def test_life_event_and_demographic_claims_are_refused(self, label):
        """A watch history can neither confirm nor refute these. Scoring them
        would manufacture a verdict out of silence."""
        assert _is_non_testable(label) is True

    @pytest.mark.parametrize("label", ["robotics", "cooking", "formula 1", "machine learning"])
    def test_topical_claims_are_testable(self, label):
        assert _is_non_testable(label) is False


class TestMatching:
    def test_matches_across_independent_vocabularies(self):
        """The platform says "Robotics"; the twin derived "robotics" from a
        hashtag. Requiring string equality would report a mismatch that is
        really just capitalisation."""
        match = _match_claim("Robotics", [_behaviour("robotics", 10)])
        assert match is not None
        assert match["matched_on"] == ["robotics"]

    def test_matches_via_keywords_not_only_the_topic_label(self):
        match = _match_claim("machine learning", [_behaviour("ai", 8, keywords=["machine", "learning"])])
        assert match is not None

    def test_no_shared_vocabulary_is_no_match(self):
        assert _match_claim("cryptocurrency", [_behaviour("robotics", 10)]) is None

    def test_stopword_only_overlap_is_not_a_match(self):
        assert _match_claim("other products", [_behaviour("products and other things", 10)]) is None

    def test_prefers_the_best_evidenced_candidate(self):
        """When several topics could support a claim, the strongest available
        support should be the one cited."""
        match = _match_claim("robotics", [
            _behaviour("robotics", 3), _behaviour("robotics research", 40),
        ])
        assert match["behaviour"]["occurrence_count"] == 40


class TestClaimNormalisation:
    def test_collapses_whitespace_and_case(self):
        assert normalize_claim_label("  Robotics  ") == "robotics"
        assert normalize_claim_label("Robotics") == normalize_claim_label("robotics")

    def test_does_not_conflate_distinct_claims(self):
        """A false merge here would silently make a platform's assertion vanish
        from the audit."""
        assert normalize_claim_label("robotics") != normalize_claim_label("robots")


class TestClaimExtractionFromExports:
    def test_meta_ads_interests_are_claims_not_events(self):
        """The crucial separation: an ad-interest file must never enter the
        pipeline as behaviour, or the platform's assertion would become
        evidence for itself."""
        payload = {"topics_your_interested_in": [
            {"string_map_data": {"Name": {"value": "Robotics"}}},
            {"string_map_data": {"Name": {"value": "Luxury Travel"}}},
        ]}
        result = parse_archive(_zip({"ads_interests.json": payload}))

        assert result["events"] == []
        labels = {c["label"] for c in result["profile_claims"]}
        assert labels == {"robotics", "luxury travel"}
        assert all(c["claim_type"] == "ad_interest" for c in result["profile_claims"])

    def test_raw_label_is_preserved_for_citation(self):
        payload = {"topics_your_interested_in": [{"string_map_data": {"Name": {"value": "Luxury Travel"}}}]}
        result = parse_archive(_zip({"ads_interests.json": payload}))
        assert result["profile_claims"][0]["raw_label"] == "Luxury Travel"

    def test_flat_shape_without_the_string_map_wrapper(self):
        """Newer exports drop the wrapper."""
        result = parse_archive(_zip({"ads_interests.json": {"inferred_topics": [{"name": "Robotics"}]}}))
        assert [c["label"] for c in result["profile_claims"]] == ["robotics"]

    def test_claims_are_deduplicated(self):
        payload = {"topics_your_interested_in": [
            {"string_map_data": {"Name": {"value": "Robotics"}}},
            {"string_map_data": {"Name": {"value": "robotics"}}},
        ]}
        result = parse_archive(_zip({"ads_interests.json": payload}))
        assert len(result["profile_claims"]) == 1


class TestReportVerdicts:
    pytestmark = pytest.mark.db

    @pytest.mark.asyncio
    async def test_end_to_end_verdicts(self, db, disposable_user_id):
        from app.db.postgres import execute
        import json

        # The twin's side: one well-evidenced topic, one barely-seen topic.
        for topic, count in (("robotics", 12), ("gardening", 1)):
            await execute(
                """
                INSERT INTO behavior_objects
                    (unique_id, user_id, topic, keywords, temporal_statistics,
                     importance_score, confidence_score, metadata)
                VALUES ($1,$2,$3,$4::jsonb,$5::jsonb,$6,$7,$8::jsonb)
                """,
                f"bo_{topic}_{disposable_user_id}", disposable_user_id, topic,
                json.dumps([topic]), json.dumps({"occurrence_count": count}),
                0.5, 0.5, json.dumps({"cluster_type": "topic"}),
            )

        # The platform's side.
        for label in ("robotics", "cryptocurrency", "gardening", "recently moved"):
            await execute(
                """
                INSERT INTO platform_profile_claims
                    (user_id, platform, claim_type, label, raw_label)
                VALUES ($1,'meta','ad_interest',$2,$3)
                """,
                disposable_user_id, label, label.title(),
            )

        report = await build_mirror_report(disposable_user_id, coverage=0.8)

        assert [c["label"] for c in report["corroborated"]] == ["Robotics"]
        assert report["corroborated"][0]["evidence"]["observations"] == 12

        unsupported = {c["label"] for c in report["unsupported"]}
        # No shared vocabulary at all.
        assert "Cryptocurrency" in unsupported
        # Matched, but on a single sighting — a coincidence, not corroboration.
        assert "Gardening" in unsupported

        assert [c["label"] for c in report["not_comparable"]] == ["Recently Moved"]

        # not_comparable is excluded from the denominator: counting untestable
        # claims as failures would inflate the headline number.
        assert report["summary"]["testable_claims"] == 3
        assert report["summary"]["supported_share"] == pytest.approx(1 / 3)
        assert report["verdict_reliable"] is True

    @pytest.mark.asyncio
    async def test_thin_data_refuses_to_render_a_verdict(self, db, disposable_user_id):
        """A twin that has seen almost nothing would mark nearly every claim
        unsupported purely from ignorance."""
        report = await build_mirror_report(disposable_user_id, coverage=MIN_COVERAGE_FOR_VERDICT - 0.1)
        assert report["verdict_reliable"] is False
        assert any("coverage is below" in c for c in report["caveats"])

    @pytest.mark.asyncio
    async def test_caveats_are_always_present(self, db, disposable_user_id):
        """Absence of evidence is not evidence of absence, and the report has
        to say so even when coverage is good."""
        report = await build_mirror_report(disposable_user_id, coverage=0.9)
        joined = " ".join(report["caveats"]).lower()
        assert "absence of evidence" in joined
        assert "lookalike" in joined
