"""Repairing an account whose pipeline never ran.

Events are committed before the pipeline runs, in the same request. When that
request dies in between, the events survive and nothing derived from them does
- and nothing ever revisits stored events, so the account stays that way. It
looks populated and answers nothing.

reprocess_stuck.py rebuilds from the events already in the database. These
tests hold what makes it safe to run: it only touches accounts that have events
and nothing derived from them, it writes nothing without --apply, and it
reconstructs the link back to the real event rows that the Timeline page walks.
"""
import ast
import inspect
import re

import pytest

import reprocess_stuck as rs


def test_only_accounts_with_events_and_nothing_derived():
    """Selecting an account that already has behaviour objects would rebuild
    state that is fine, which is how a repair tool becomes a hazard."""
    sql = inspect.getsource(rs.stuck_accounts)
    assert "NOT EXISTS" in sql
    assert "FROM behavior_objects" in sql
    assert "FROM events" in sql
    # And it refuses accounts too new to have anything to consolidate.
    assert "HAVING COUNT(*) >= $2" in sql
    assert rs.MIN_EVENTS_TO_BOTHER >= 3, (
        "consolidation needs three events sharing a topic; below that an "
        "account is new, not stuck")


@pytest.mark.asyncio
async def test_dry_run_writes_nothing(monkeypatch):
    """The default has to be safe: it runs against real accounts."""
    async def fake_init():
        return None

    async def fake_close():
        return None

    async def fake_stuck(user=None):
        return [{"user_id": "u1", "events": 800}]

    rebuilt = []

    async def fake_rebuild(uid):
        rebuilt.append(uid)

    monkeypatch.setattr(rs, "init_pool", fake_init)
    monkeypatch.setattr(rs, "close_pool", fake_close)
    monkeypatch.setattr(rs, "stuck_accounts", fake_stuck)
    monkeypatch.setattr(rs, "rebuild", fake_rebuild)

    rc = await rs.main(apply=False, user=None, limit=0)
    assert rc == 0
    assert rebuilt == [], "a dry run rebuilt something"

    rc = await rs.main(apply=True, user=None, limit=0)
    assert rebuilt == ["u1"]


@pytest.mark.asyncio
async def test_events_are_linked_back_to_their_rows(monkeypatch):
    """supporting_event_ids has to point at real events.id values.

    The normalizer invents an evt_xxxx id with no link to storage. Ingest
    overwrites it with the row id and so must this, or the Timeline page's
    reverse index finds nothing for anything rebuilt.
    """
    rows = [
        {"id": 5001, "reel_id": "r1", "username": "creator_a",
         "caption": "about python", "hashtags": '["#coding"]', "audio": "a.mp3",
         "watch_time": 30.0, "timestamp": _ts(), "session_id": "s1",
         "liked": True, "saved": False, "shared": False, "commented": False,
         "following": False, "platform": "instagram", "surface": "reels"},
        {"id": 5002, "reel_id": "r2", "username": "creator_b",
         "caption": "about design", "hashtags": ["#design"], "audio": "b.mp3",
         "watch_time": 12.0, "timestamp": _ts(), "session_id": "s1",
         "liked": False, "saved": False, "shared": False, "commented": False,
         "following": False, "platform": "instagram", "surface": "reels"},
    ]

    async def fake_fetch(sql, *args):
        return rows

    monkeypatch.setattr(rs, "fetch", fake_fetch)

    normalized = await rs._normalized_events("u1")
    assert len(normalized) == 2
    by_content = {e.content_id: e.event_id for e in normalized}
    assert by_content == {"r1": "5001", "r2": "5002"}


@pytest.mark.asyncio
async def test_hashtags_survive_either_storage_shape(monkeypatch):
    """asyncpg hands jsonb back as a str on some paths and a list on others.

    Getting this wrong loses every topic - and topics are the whole point of
    the rebuild, so it would "succeed" and produce nothing.
    """
    rows = [{
        "id": 1, "reel_id": "r1", "username": "c", "caption": "x",
        "hashtags": '["#coding", "#ai"]', "audio": "a", "watch_time": 5.0,
        "timestamp": _ts(), "session_id": "s", "liked": False, "saved": False,
        "shared": False, "commented": False, "following": False,
        "platform": "instagram", "surface": "reels",
    }]

    async def fake_fetch(sql, *args):
        return rows

    monkeypatch.setattr(rs, "fetch", fake_fetch)
    as_text = await rs._normalized_events("u")

    rows[0]["hashtags"] = ["#coding", "#ai"]
    as_list = await rs._normalized_events("u")

    assert as_text[0].hashtags == as_list[0].hashtags == ["#coding", "#ai"]


def test_rebuild_carries_the_existing_identity():
    """Rebuilding must extend the account's identity, not fork a second one.

    identities is unique on user_id, so running the pipeline without loading
    the existing identity first is how a rebuild ends up inserting over a
    constraint and silently doing nothing.
    """
    tree = ast.parse(inspect.getsource(rs.rebuild).lstrip())
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "run"]
    assert len(calls) == 1
    passed = {kw.arg for kw in calls[0].keywords}
    assert "existing_identity" in passed, "rebuild ignores the stored identity"
    assert "load_identity" in inspect.getsource(rs.rebuild)


def _ts():
    from datetime import datetime, timezone
    return datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
