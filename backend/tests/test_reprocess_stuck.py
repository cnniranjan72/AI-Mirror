"""Repairing an account whose pipeline never ran.

Events are committed before the pipeline runs, in the same request. When that
request dies in between, the events survive and nothing derived from them does
- and nothing ever revisits stored events, so the account stays that way. It
looks populated and answers nothing.

reprocess_stuck.py rebuilds from the events already in the database. These
tests hold what makes it safe to run: it only touches accounts that have events
and nothing derived from them, and it writes nothing without --apply.

Reading events back out of storage is shared with the ingest path and lives in
pipeline/stored_events.py; tests/test_consolidation_window.py covers it.
"""
import ast
import inspect

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


def test_repair_reads_the_whole_history_not_a_window():
    """An ingest looks at a recent window to keep the read bounded. A repair
    is the one caller that should consider everything the account ever sent,
    since it is reconstructing state that was never built at all."""
    src = inspect.getsource(rs.rebuild)
    assert "load_recent" in src
    assert "limit=None" in src, "the repair is only rebuilding from a window"


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
