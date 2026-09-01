"""Interest Provenance — chosen vs fed.

The distinction these tests exist to protect: "you never sought this out" and
"we have no way to tell" produce the same raw number (zero deliberate signals)
and mean completely opposite things. Reporting the second as the first would
tell every user their interests were manufactured, which is both false and
exactly the kind of confident-from-nothing output this codebase keeps having
to be defended against.
"""
import pytest

from app.services.interest_provenance import (
    _tokens, _classify, build_provenance_report,
    MIN_DELIBERATE_SIGNALS, MIN_EXPOSURE_TO_JUDGE, FED_CEILING, MIXED_CEILING,
)
from app.services.archive_import import parse_archive

from tests.test_archive_import import _zip


class TestClassification:
    def test_no_seeking_is_fed(self):
        assert _classify(0.0) == "fed"

    def test_heavy_seeking_is_chosen(self):
        assert _classify(0.9) == "chosen"

    def test_between_the_bands_is_mixed(self):
        assert _classify((FED_CEILING + MIXED_CEILING) / 2) == "mixed"

    def test_none_is_unknown_not_fed(self):
        """The whole point: absent data must never be scored as absent intent."""
        assert _classify(None) == "unknown"


class TestTokenising:
    def test_drops_search_boilerplate(self):
        # "how to" and "tutorial" appear in a huge share of queries and would
        # match every topic if kept.
        assert _tokens("how to best robotics tutorial") == {"robotics"}

    def test_matches_across_phrasings(self):
        assert _tokens("robotics arm") & _tokens("robotics kinematics")


class TestSearchExtraction:
    """Search history was previously discarded by the watch parser."""

    def test_searches_are_captured_not_dropped(self):
        activity = [
            {"header": "YouTube", "title": "Searched for robotics arm build",
             "time": "2025-03-01T10:00:00.000Z"},
            {"header": "YouTube", "title": "Watched robotics arm build log",
             "titleUrl": "https://youtube.com/watch?v=a",
             "subtitles": [{"name": "chan"}], "time": "2025-03-01T10:05:00.000Z"},
        ]
        result = parse_archive(_zip({"watch-history.json": activity}))

        assert len(result["events"]) == 1, "searches must not become behaviour events"
        assert len(result["search_signals"]) == 1
        assert result["search_signals"][0]["raw_query"] == "robotics arm build"
        assert result["search_signals"][0]["query"] == "robotics arm build"

    def test_same_query_at_different_times_counts_twice(self):
        """Searching the same term on two days is two real signals."""
        activity = [
            {"header": "YouTube", "title": "Searched for pottery", "time": "2025-03-01T10:00:00.000Z"},
            {"header": "YouTube", "title": "Searched for pottery", "time": "2025-04-01T10:00:00.000Z"},
        ]
        result = parse_archive(_zip({"watch-history.json": activity}))
        assert len(result["search_signals"]) == 2

    def test_identical_duplicate_rows_collapse(self):
        activity = [
            {"header": "YouTube", "title": "Searched for pottery", "time": "2025-03-01T10:00:00.000Z"},
            {"header": "YouTube", "title": "Searched for pottery", "time": "2025-03-01T10:00:00.000Z"},
        ]
        result = parse_archive(_zip({"watch-history.json": activity}))
        assert len(result["search_signals"]) == 1


class TestReport:
    pytestmark = pytest.mark.db

    async def _topic(self, user_id, topic, exposure):
        from app.db.postgres import execute
        import json
        await execute(
            """
            INSERT INTO behavior_objects
                (unique_id, user_id, topic, keywords, temporal_statistics,
                 importance_score, confidence_score, metadata)
            VALUES ($1,$2,$3,$4::jsonb,$5::jsonb,0.5,0.5,$6::jsonb)
            """,
            f"bo_{topic}_{user_id}", user_id, topic, json.dumps([topic]),
            json.dumps({"occurrence_count": exposure}), json.dumps({"cluster_type": "topic"}),
        )

    async def _search(self, user_id, query, when):
        from datetime import datetime
        from app.db.postgres import execute
        await execute(
            "INSERT INTO search_signals (user_id, platform, query, raw_query, searched_at) "
            "VALUES ($1,'youtube',$2,$3,$4)",
            user_id, query, query, datetime.fromisoformat(when.replace("Z", "+00:00")),
        )

    @pytest.mark.asyncio
    async def test_without_deliberate_signals_nothing_is_judged(self, db, disposable_user_id):
        """The critical case. Zero searches must yield "unknown", NOT a report
        claiming every interest was manufactured."""
        await self._topic(disposable_user_id, "robotics", 40)

        report = await build_provenance_report(disposable_user_id)

        assert report["measurable"] is False
        assert all(t["verdict"] == "unknown" for t in report["topics"])
        assert all(t["agency"] is None for t in report["topics"])
        assert report["summary"]["fed"] == 0
        assert any("cannot be measured" in c for c in report["caveats"])

    @pytest.mark.asyncio
    async def test_separates_chosen_from_fed(self, db, disposable_user_id):
        await self._topic(disposable_user_id, "robotics", 20)
        await self._topic(disposable_user_id, "gambling", 60)

        # Enough deliberate signals to make the account measurable, all of them
        # pointing at robotics.
        for i in range(6):
            await self._search(disposable_user_id, "robotics arm", f"2025-0{i+1}-01T10:00:00Z")

        report = await build_provenance_report(disposable_user_id)
        assert report["measurable"] is True

        by_topic = {t["topic"]: t for t in report["topics"]}
        assert by_topic["robotics"]["searches"] == 6
        assert by_topic["robotics"]["verdict"] in ("mixed", "chosen")
        assert by_topic["gambling"]["searches"] == 0
        assert by_topic["gambling"]["verdict"] == "fed"

    @pytest.mark.asyncio
    async def test_barely_seen_topics_are_not_judged(self, db, disposable_user_id):
        """"You never sought it" is meaningless for something seen twice."""
        await self._topic(disposable_user_id, "robotics", 30)
        await self._topic(disposable_user_id, "obscure", MIN_EXPOSURE_TO_JUDGE - 1)
        for i in range(MIN_DELIBERATE_SIGNALS + 1):
            await self._search(disposable_user_id, "robotics", f"2025-0{i+1}-01T10:00:00Z")

        report = await build_provenance_report(disposable_user_id)
        by_topic = {t["topic"]: t for t in report["topics"]}
        assert by_topic["obscure"]["verdict"] == "unknown"

    @pytest.mark.asyncio
    async def test_fed_topics_lead_the_list(self, db, disposable_user_id):
        """The most-watched thing you never sought is the finding; it should
        not be buried under things you did choose."""
        await self._topic(disposable_user_id, "robotics", 20)
        await self._topic(disposable_user_id, "ragebait", 90)
        for i in range(6):
            await self._search(disposable_user_id, "robotics", f"2025-0{i+1}-01T10:00:00Z")

        report = await build_provenance_report(disposable_user_id)
        assert report["topics"][0]["topic"] == "ragebait"

    @pytest.mark.asyncio
    async def test_following_flag_is_never_treated_as_intent(self, db, disposable_user_id):
        """events.following defaults to True, so it marks 99% of rows. If it
        ever leaks into the scorer, everything looks self-chosen."""
        from app.db.postgres import execute
        await self._topic(disposable_user_id, "robotics", 30)
        for i in range(10):
            await execute(
                """
                INSERT INTO events (user_id, reel_id, username, caption, hashtags,
                                    watch_time, timestamp, session_id, platform,
                                    liked, saved, shared, commented, following)
                VALUES ($1,$2,'chan','robotics deep dive','[]'::jsonb,30,NOW(),'s','youtube',
                        false,false,false,false,true)
                """,
                disposable_user_id, f"reel_follow_{i}",
            )

        report = await build_provenance_report(disposable_user_id)
        # Ten following=true events must not make the account measurable.
        assert report["measurable"] is False
        assert report["summary"]["engagement_signals"] == 0
