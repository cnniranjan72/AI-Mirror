"""Parsing official platform data exports.

These formats are undocumented in practice and vary by export vintage and
locale, and the input is a user-uploaded file arriving over the network. So the
properties worth pinning down are mostly about resilience: one malformed record
must never cost the user the other 40,000, and no upload may be able to exhaust
the process.

No database, no network.
"""
import io
import json
import zipfile

import pytest

from app.services.archive_import import (
    ArchiveImportError, parse_archive, _from_epoch, _from_iso,
)


def _zip(members: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload if isinstance(payload, str) else json.dumps(payload))
    return buffer.getvalue()


# Real export shapes, trimmed.
IG_VIDEOS_WATCHED = {
    "impressions_history_videos_watched": [
        {"string_map_data": {"Author": {"value": "lex_fridman_clips"},
                             "Time": {"timestamp": 1735689600}}},
        {"string_map_data": {"Author": {"value": "natgeo"},
                             "Time": {"timestamp": 1735693200}}},
    ]
}

IG_LIKES = {
    "likes_media_likes": [
        {"title": "andrej_karpathy",
         "string_list_data": [{"href": "https://instagram.com/p/abc", "timestamp": 1735696800}]}
    ]
}

YT_WATCH_HISTORY = [
    {"header": "YouTube", "title": "Watched Building a neural network from scratch",
     "titleUrl": "https://www.youtube.com/watch?v=xyz",
     "subtitles": [{"name": "Sentdex"}], "time": "2025-01-01T10:00:00.000Z"},
    # Search activity shares the file shape but is not behaviour.
    {"header": "YouTube", "title": "Searched for pytorch tutorial",
     "time": "2025-01-01T10:05:00.000Z"},
]


class TestTimestamps:
    def test_epoch_seconds(self):
        assert _from_epoch(1735689600).year == 2025

    @pytest.mark.parametrize("value", [None, "", "abc", 0, -1, 99_999_999_999])
    def test_rejects_implausible_epochs(self, value):
        """A malformed record with a huge integer would otherwise land a
        timestamp centuries out and skew every temporal statistic."""
        assert _from_epoch(value) is None

    def test_iso_with_z_suffix(self):
        parsed = _from_iso("2025-01-01T10:00:00.000Z")
        assert parsed is not None and parsed.year == 2025

    @pytest.mark.parametrize("value", [None, "", "not a date", 12345])
    def test_rejects_bad_iso(self, value):
        assert _from_iso(value) is None


class TestInstagram:
    def test_parses_videos_watched(self):
        result = parse_archive(_zip({"videos_watched.json": IG_VIDEOS_WATCHED}))
        assert result["sources"] == {"instagram_videos_watched": 2}
        assert {e["username"] for e in result["events"]} == {"lex_fridman_clips", "natgeo"}
        assert all(e["platform"] == "instagram" for e in result["events"])

    def test_view_events_claim_no_watch_time(self):
        """An export records THAT something was watched, never for how long.
        Inventing a duration would corrupt the watch statistics the identity is
        built from."""
        result = parse_archive(_zip({"videos_watched.json": IG_VIDEOS_WATCHED}))
        assert all(e["watch_time"] == 0.0 for e in result["events"])

    def test_likes_carry_the_engagement_flag(self):
        result = parse_archive(_zip({"liked_posts.json": IG_LIKES}))
        assert result["sources"] == {"instagram_likes": 1}
        event = result["events"][0]
        assert event["liked"] is True
        assert event["username"] == "andrej_karpathy"


class TestYouTube:
    def test_parses_watch_history(self):
        result = parse_archive(_zip({"watch-history.json": YT_WATCH_HISTORY}))
        # The fixture also contains one search, which is now captured as an
        # intent signal rather than discarded (see interest_provenance).
        assert result["sources"]["youtube_watch_history"] == 1
        assert result["sources"]["youtube_searches"] == 1
        event = result["events"][0]
        assert event["platform"] == "youtube"
        assert event["username"] == "Sentdex"

    def test_searches_never_become_behaviour_events(self):
        """Takeout mixes searches into the same file. They must not be counted
        as watching — they are intent, and are stored separately."""
        result = parse_archive(_zip({"watch-history.json": YT_WATCH_HISTORY}))
        assert len(result["events"]) == 1
        assert "Searched" not in result["events"][0]["caption"]
        assert len(result["search_signals"]) == 1

    def test_video_title_survives_as_caption(self):
        # It is the only free text an export gives, and topic extraction has
        # nothing else to work from.
        result = parse_archive(_zip({"watch-history.json": YT_WATCH_HISTORY}))
        assert "neural network" in result["events"][0]["caption"]


class TestResilience:
    def test_one_bad_file_does_not_sink_the_import(self):
        data = _zip({
            "watch-history.json": YT_WATCH_HISTORY,
            "broken.json": "{not valid json",
            "videos_watched.json": IG_VIDEOS_WATCHED,
        })
        result = parse_archive(data)
        assert len(result["events"]) == 3  # 1 YouTube + 2 Instagram

    @pytest.mark.parametrize("payload", [
        {"impressions_history_videos_watched": "not a list"},
        {"impressions_history_videos_watched": [None, 42, "text"]},
        {"impressions_history_videos_watched": [{"string_map_data": {}}]},  # no timestamp
        {},
    ])
    def test_malformed_records_are_skipped_not_raised(self, payload):
        result = parse_archive(_zip({"videos_watched.json": payload}))
        assert result["events"] == []

    def test_accepts_a_bare_json_file(self):
        """Users often upload the single watch-history.json rather than the
        whole Takeout archive."""
        result = parse_archive(json.dumps(YT_WATCH_HISTORY).encode(), "watch-history.json")
        assert len(result["events"]) == 1

    def test_unsupported_files_are_counted_rather_than_failing_silently(self):
        result = parse_archive(_zip({"profile.json": {"unrelated": [1, 2, 3]}}))
        assert result["events"] == []
        assert result["skipped_files"] == 1

    def test_duplicates_are_removed(self):
        """Exports overlap and re-exports repeat history wholesale; importing
        the same archive twice must not double the user's history."""
        result = parse_archive(_zip({
            "videos_watched.json": IG_VIDEOS_WATCHED,
            "also_videos_watched.json": IG_VIDEOS_WATCHED,
        }))
        assert len(result["events"]) == 2
        assert result["duplicates_removed"] == 2

    def test_events_are_ordered_oldest_first(self):
        """Identity evolution is a sequence: history has to arrive in the order
        it happened."""
        result = parse_archive(_zip({"videos_watched.json": IG_VIDEOS_WATCHED,
                                     "liked_posts.json": IG_LIKES}))
        timestamps = [e["timestamp"] for e in result["events"]]
        assert timestamps == sorted(timestamps)


class TestGuardRails:
    def test_rejects_empty_upload(self):
        with pytest.raises(ArchiveImportError, match="Empty"):
            parse_archive(b"")

    def test_rejects_a_file_that_is_neither_zip_nor_json(self):
        with pytest.raises(ArchiveImportError, match="neither"):
            parse_archive(b"\x00\x01 binary garbage", "photo.png")

    def test_rejects_a_zip_bomb(self):
        """Highly compressible content that expands past the uncompressed
        ceiling is refused before it is read into memory."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("bomb.json", "0" * (1024 * 1024 * 1024 + 1))
        with pytest.raises(ArchiveImportError, match="expands to"):
            parse_archive(buffer.getvalue())


class TestImportEndpoint:
    """POST /import/archive, end to end through the real pipeline.

    The parser tests above prove bytes become events. This proves those events
    reach the identity — the endpoint deliberately delegates to ingest_events
    rather than driving the pipeline itself, and this is what would catch that
    wiring breaking.
    """

    pytestmark = pytest.mark.db

    @pytest.mark.asyncio
    async def test_upload_creates_behavioural_data(self, db):
        import uuid
        from httpx import ASGITransport, AsyncClient
        from app.main import app
        from app.services import data_privacy

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            username = f"import_{uuid.uuid4().hex[:8]}"
            reg = await client.post(
                "/auth/register", json={"username": username, "password": "test-password-123"}
            )
            assert reg.status_code == 200, reg.text
            headers = {"Authorization": f"Bearer {reg.json()['token']}"}

            try:
                # Enough repeats of one topic to clear the minimum cluster size.
                history = [
                    {"header": "YouTube",
                     "title": f"Watched robotics engineering explained part {i}",
                     "titleUrl": f"https://www.youtube.com/watch?v=v{i}",
                     "subtitles": [{"name": "Sentdex"}],
                     "time": f"2025-01-0{i + 1}T10:00:00.000Z"}
                    for i in range(5)
                ]
                archive = _zip({"watch-history.json": history})

                resp = await client.post(
                    "/import/archive",
                    files={"file": ("takeout.zip", archive, "application/zip")},
                    data={"user_id": username},
                    headers=headers,
                )
                assert resp.status_code == 200, resp.text
                body = resp.json()
                assert body["events_found"] == 5
                assert body["events_stored"] > 0
                assert body["sources"] == {"youtube_watch_history": 5}

                summary = await client.get(f"/cognitive/summary?user_id={username}", headers=headers)
                assert summary.status_code == 200
                assert summary.json()["behavior_object_count"] > 0
            finally:
                try:
                    await data_privacy.delete_all_user_data(username)
                    # The account too: delete_all_user_data leaves the `users`
                    # row, so registering in a test leaks one per run.
                    await data_privacy.delete_account(username)
                except Exception:
                    pass

    @pytest.mark.asyncio
    async def test_unsupported_file_explains_what_was_expected(self, db):
        """A bare "no events found" leaves the user unable to tell whether they
        uploaded the wrong file or the right file in the wrong format."""
        import uuid
        from httpx import ASGITransport, AsyncClient
        from app.main import app
        from app.services import data_privacy

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            username = f"import_{uuid.uuid4().hex[:8]}"
            reg = await client.post(
                "/auth/register", json={"username": username, "password": "test-password-123"}
            )
            headers = {"Authorization": f"Bearer {reg.json()['token']}"}
            try:
                archive = _zip({"profile.json": {"unrelated": [1, 2, 3]}})
                resp = await client.post(
                    "/import/archive",
                    files={"file": ("takeout.zip", archive, "application/zip")},
                    data={"user_id": username},
                    headers=headers,
                )
                assert resp.status_code == 400
                detail = resp.json()["detail"]
                assert "Download your information" in detail
                assert "watch-history" in detail
            finally:
                try:
                    await data_privacy.delete_all_user_data(username)
                    # The account too: delete_all_user_data leaves the `users`
                    # row, so registering in a test leaks one per run.
                    await data_privacy.delete_account(username)
                except Exception:
                    pass
