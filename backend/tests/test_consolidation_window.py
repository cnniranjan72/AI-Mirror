"""A topic has to be allowed to accumulate across requests.

Consolidation needs three events sharing a topic or a creator before it forms
anything. Applied to one request's events in isolation - which is what
existing_clusters=[] and a per-request call amounted to - a creator whose
videos are spread over the extension's ten-event batches never reaches three in
any single batch, and never becomes a behaviour object at all. There is no
later rescue: the orchestrator merges into behaviour objects that already
exist, so a topic that never formed once never forms.

Measured against the same events consolidated together:

    demo_ddz4smtf   800 events   19% of topics never form
    demo_tx4m2pae   800 events   35% never form
    demo_vf35lyxj   159 events   50% never form

Nearly all of the loss is creator clusters, which is what one would predict: a
creator needs three of their own videos inside a ten-event window.

These tests hold the window, and the two properties that make re-reading
storage safe - an event must not be counted twice, and a genuine re-watch must
still count separately.
"""
import ast
import inspect
from datetime import datetime, timedelta, timezone

import pytest

from pipeline import stored_events


class FakeEvent:
    """Enough of a BehaviorEvent for merge(), which only reads two fields."""

    def __init__(self, content_id, timestamp, event_id="evt_x"):
        self.content_id = content_id
        self.timestamp = timestamp
        self.event_id = event_id

    def __repr__(self):
        return "FakeEvent(%s, %s)" % (self.content_id, self.timestamp)


T0 = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)


def test_window_is_bounded_but_large_enough_to_be_worth_it():
    """Unbounded, this read grows with an account's whole history.

    The size is a measurement, not a preference: on an 800-event account 100
    events yield 24 of 31 topics and 400 yield 30.
    """
    assert 100 <= stored_events.CONSOLIDATION_WINDOW <= 5000


def test_merge_does_not_count_a_stored_event_twice():
    """Ingest stores events before running the pipeline, so the batch it hands
    over is normally already inside the window."""
    stored = [FakeEvent("r1", T0, "101"), FakeEvent("r2", T0, "102")]
    incoming = [FakeEvent("r2", T0, "evt_new"), FakeEvent("r3", T0, "evt_new2")]

    merged = stored_events.merge(stored, incoming)

    assert [e.content_id for e in merged] == ["r1", "r2", "r3"]
    # The stored copy wins, so the real row id survives.
    assert [e.event_id for e in merged if e.content_id == "r2"] == ["102"]


def test_merge_keeps_an_event_the_caller_has_not_stored_yet():
    """A caller that stores afterwards must still have its events consolidated.

    This is the whole reason merge takes both sides rather than just reading
    the window.
    """
    merged = stored_events.merge([], [FakeEvent("r9", T0)])
    assert [e.content_id for e in merged] == ["r9"]


def test_merge_keeps_a_genuine_rewatch():
    """Same content, different time, is a second viewing and counts as one.

    Deduplicating on content id alone would erase exactly the repetition that
    consolidation exists to detect.
    """
    stored = [FakeEvent("r1", T0)]
    incoming = [FakeEvent("r1", T0 + timedelta(days=2))]

    merged = stored_events.merge(stored, incoming)
    assert len(merged) == 2


def test_merge_identifies_events_by_content_and_time_not_event_id():
    """The two sides disagree about event_id - storage knows the row id, a
    freshly normalized batch may still carry the invented one - so matching on
    it would deduplicate nothing."""
    src = inspect.getsource(stored_events.merge)
    assert "content_id" in src and "timestamp" in src
    tree = ast.parse(src.lstrip())
    compared = {
        n.attr for n in ast.walk(tree)
        if isinstance(n, ast.Attribute) and n.attr in ("event_id", "content_id")
    }
    assert "event_id" not in compared, "merge is matching on event_id"


def test_hashtags_survive_either_storage_shape():
    """asyncpg hands jsonb back as text on some paths and a list on others.

    Getting this wrong loses every topic silently: the events still normalize,
    they just carry nothing to group on.
    """
    assert stored_events._hashtags('["#coding", "#ai"]') == ["#coding", "#ai"]
    assert stored_events._hashtags(["#coding"]) == ["#coding"]
    assert stored_events._hashtags(None) == []
    assert stored_events._hashtags("not json at all") == []


@pytest.mark.asyncio
async def test_events_are_linked_back_to_their_rows(monkeypatch):
    """supporting_event_ids has to point at real events.id values.

    The normalizer invents an evt_xxxx with no link to storage. Ingest
    overwrites it with the row id and so must this, or the Timeline page's
    reverse index finds nothing for anything consolidated from storage.
    """
    rows = [
        {"id": 5001, "reel_id": "r1", "username": "creator_a",
         "caption": "about python", "hashtags": '["#coding"]', "audio": "a.mp3",
         "watch_time": 30.0, "timestamp": T0, "session_id": "s1",
         "liked": True, "saved": False, "shared": False, "commented": False,
         "following": False, "platform": "instagram", "surface": "reels"},
        {"id": 5002, "reel_id": "r2", "username": "creator_b",
         "caption": "about design", "hashtags": ["#design"], "audio": "b.mp3",
         "watch_time": 12.0, "timestamp": T0, "session_id": "s1",
         "liked": False, "saved": False, "shared": False, "commented": False,
         "following": False, "platform": "instagram", "surface": "reels"},
    ]

    async def fake_fetch(sql, *args):
        return rows

    monkeypatch.setattr(stored_events, "fetch", fake_fetch)

    events = await stored_events.load_recent("u1")
    assert {e.content_id: e.event_id for e in events} == {"r1": "5001", "r2": "5002"}


@pytest.mark.asyncio
async def test_window_reads_the_newest_events_but_hands_them_over_oldest_first(monkeypatch):
    """Ordering matters twice, in opposite directions.

    The LIMIT has to take the *newest* events, so a long-dormant account does
    not consolidate only its oldest history. Consolidation then wants them in
    time order, because the temporal statistics it derives - first seen, last
    seen, trend - read the sequence.
    """
    captured = {}

    async def fake_fetch(sql, *args):
        captured["sql"] = " ".join(sql.split())
        captured["args"] = args
        return []

    monkeypatch.setattr(stored_events, "fetch", fake_fetch)
    await stored_events.load_recent("u1")

    sql = captured["sql"]
    assert "ORDER BY timestamp DESC LIMIT $2" in sql, sql
    assert sql.rstrip().endswith("ORDER BY timestamp ASC"), sql
    assert captured["args"] == ("u1", stored_events.CONSOLIDATION_WINDOW)


@pytest.mark.asyncio
async def test_no_limit_reads_everything(monkeypatch):
    """The repair path asks for the whole history, so LIMIT must drop out
    rather than being passed as None and breaking the query."""
    captured = {}

    async def fake_fetch(sql, *args):
        captured["sql"] = " ".join(sql.split())
        captured["args"] = args
        return []

    monkeypatch.setattr(stored_events, "fetch", fake_fetch)
    await stored_events.load_recent("u1", limit=None)

    assert "LIMIT" not in captured["sql"], captured["sql"]
    assert captured["args"] == ("u1",)


@pytest.mark.asyncio
async def test_a_failed_read_does_not_fail_the_ingest(monkeypatch):
    """The window is an improvement on consolidating the batch alone. If the
    read fails, the batch must still be consolidated the old way rather than
    the whole ingest dying."""
    async def boom(sql, *args):
        raise RuntimeError("db gone")

    monkeypatch.setattr(stored_events, "fetch", boom)
    assert await stored_events.load_recent("u1") == []


def test_orchestrator_consolidates_the_window_not_just_the_batch():
    """The wiring is the point: a window that is loaded and then not passed to
    consolidate_events would be pure cost."""
    from pipeline import orchestrator

    src = inspect.getsource(orchestrator.V3Pipeline._consolidate_events)
    tree = ast.parse(src.lstrip())

    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "consolidate_events"]
    assert len(calls) == 1
    passed = {kw.arg: kw.value for kw in calls[0].keywords}
    assert "events" in passed
    assert isinstance(passed["events"], ast.Name), ast.dump(passed["events"])
    assert passed["events"].id != "events", (
        "consolidation is still being handed only this request's events")

    assert "load_recent" in src and "merge" in src
