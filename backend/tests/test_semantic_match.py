"""Semantic fallback for topic matching.

Lexical matching produced a real false accusation in a live demo: seven
searches for "astrophotography setup" did not share a word with the topic
`astronomy`, so the topic was reported as FED — telling the user an interest
had been installed in them when they had gone looking for it seven times.

These tests pin down the two properties that keep the fallback from doing
harm of its own: it never overrides a lexical match, and it always degrades to
lexical-only rather than failing, since it depends on a network call.

No network. The embedder is stubbed throughout.
"""
import pytest

from app.services import semantic_match
from app.services.semantic_match import cosine, best_semantic_match, SIMILARITY_THRESHOLD


class TestCosine:
    def test_identical_vectors(self):
        assert cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_scale_invariant(self):
        """Magnitude must not matter — only direction."""
        assert cosine([1.0, 1.0], [5.0, 5.0]) == pytest.approx(1.0)

    @pytest.mark.parametrize("u,v", [([0.0, 0.0], [1.0, 1.0]), ([1.0, 1.0], [0.0, 0.0])])
    def test_zero_vector_does_not_divide_by_zero(self, u, v):
        assert cosine(u, v) == 0.0


class TestBestMatch:
    VECTORS = {
        "astronomy":              [1.0, 0.0, 0.0],
        "astrophotography setup": [0.9, 0.44, 0.0],   # ~0.90 similarity
        "bitcoin trading":        [0.0, 0.0, 1.0],    # orthogonal
    }

    def test_finds_a_related_candidate(self):
        hit = best_semantic_match("astrophotography setup", ["astronomy", "bitcoin trading"], self.VECTORS)
        assert hit["candidate"] == "astronomy"
        assert hit["similarity"] > SIMILARITY_THRESHOLD

    def test_rejects_unrelated_candidates(self):
        assert best_semantic_match("bitcoin trading", ["astronomy"], self.VECTORS) is None

    def test_returns_none_when_the_query_was_not_embedded(self):
        assert best_semantic_match("unseen text", ["astronomy"], self.VECTORS) is None

    def test_returns_none_with_no_vectors_at_all(self):
        """The degraded path: embedding unavailable means lexical-only."""
        assert best_semantic_match("astronomy", ["astrophotography setup"], {}) is None

    def test_picks_the_closest_of_several(self):
        vectors = dict(self.VECTORS, telescope=[0.99, 0.14, 0.0])
        hit = best_semantic_match("astrophotography setup", ["bitcoin trading", "telescope", "astronomy"], vectors)
        assert hit["candidate"] == "telescope"

    def test_threshold_is_honoured(self):
        vectors = {"a": [1.0, 0.0], "b": [0.2, 0.98]}   # ~0.2, below threshold
        assert best_semantic_match("a", ["b"], vectors) is None


class TestEmbedTextsDegradesGracefully:
    """This is an optional enhancement to a method that already works, so every
    failure mode has to return {} rather than raise."""

    @pytest.mark.asyncio
    async def test_empty_input(self):
        assert await semantic_match.embed_texts([]) == {}
        assert await semantic_match.embed_texts(["", "   "]) == {}

    @pytest.mark.asyncio
    async def test_embedding_failure_returns_empty(self, monkeypatch):
        async def boom(_texts):
            raise RuntimeError("HF_API_TOKEN not configured")

        import app.services.embedding as embedding
        monkeypatch.setattr(embedding, "encode_batch", boom)
        assert await semantic_match.embed_texts(["astronomy"]) == {}

    @pytest.mark.asyncio
    async def test_mismatched_vector_count_returns_empty(self, monkeypatch):
        """A short response must not silently mis-pair texts with vectors."""
        async def short(_texts):
            return [[1.0, 0.0]]

        import app.services.embedding as embedding
        monkeypatch.setattr(embedding, "encode_batch", short)
        assert await semantic_match.embed_texts(["astronomy", "robotics"]) == {}

    @pytest.mark.asyncio
    async def test_oversized_request_is_skipped(self, monkeypatch):
        """One report must not turn into an unbounded embedding job."""
        called = False

        async def spy(texts):
            nonlocal called
            called = True
            return [[1.0] for _ in texts]

        import app.services.embedding as embedding
        monkeypatch.setattr(embedding, "encode_batch", spy)

        many = [f"topic {i}" for i in range(semantic_match.MAX_TEXTS_PER_REPORT + 1)]
        assert await semantic_match.embed_texts(many) == {}
        assert called is False

    @pytest.mark.asyncio
    async def test_deduplicates_before_embedding(self, monkeypatch):
        seen = {}

        async def spy(texts):
            seen["n"] = len(texts)
            return [[1.0, 0.0] for _ in texts]

        import app.services.embedding as embedding
        monkeypatch.setattr(embedding, "encode_batch", spy)

        await semantic_match.embed_texts(["astronomy", "astronomy", " astronomy "])
        assert seen["n"] == 1


class TestLexicalStillWins:
    """The fallback must never override a match a shared word already found —
    lexical results are the auditable ones."""

    pytestmark = pytest.mark.db

    @pytest.mark.asyncio
    async def test_lexical_match_is_reported_as_lexical(self, db, disposable_user_id, monkeypatch):
        import json
        from app.db.postgres import execute
        from app.services.algorithmic_mirror import build_mirror_report

        # Embedding that would happily match anything to anything.
        async def everything_matches(texts):
            return [[1.0, 0.0] for _ in texts]

        import app.services.embedding as embedding
        monkeypatch.setattr(embedding, "encode_batch", everything_matches)

        await execute(
            """
            INSERT INTO behavior_objects
                (unique_id, user_id, topic, keywords, temporal_statistics,
                 importance_score, confidence_score, metadata)
            VALUES ($1,$2,'robotics',$3::jsonb,$4::jsonb,0.5,0.5,$5::jsonb)
            """,
            f"bo_rob_{disposable_user_id}", disposable_user_id,
            json.dumps(["robotics"]), json.dumps({"occurrence_count": 12}),
            json.dumps({"cluster_type": "topic"}),
        )
        await execute(
            "INSERT INTO platform_profile_claims (user_id, platform, claim_type, label, raw_label) "
            "VALUES ($1,'meta','ad_interest','robotics','Robotics')",
            disposable_user_id,
        )

        report = await build_mirror_report(disposable_user_id, coverage=0.8)
        assert len(report["corroborated"]) == 1
        assert report["corroborated"][0]["evidence"]["match_method"] == "lexical"
