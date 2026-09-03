"""Seeding has to survive the request it runs in.

/seed stored 800 events as 800 single-row INSERTs and then ran the whole
pipeline, all inside one HTTP request. Each insert is a round trip; measured
against the managed database that is roughly 330 s of latency before any
consolidation starts. Roughly half of those requests died first.

The damage is not a failed seed - it is a *half* seed. The events are committed
and the derived state is not, nothing ever revisits stored events, and the
account is permanently unanswerable while looking populated: the dashboard
shows an event count and every question returns "No behavioral data found yet".
Measured on the deployed instance: 7 of 15 demo accounts, four of them holding
all 800 events.

The insert is now one statement (2.29 s for 800 rows, verified against the same
database inside a rolled-back transaction). These tests hold the two things
that make it correct rather than merely fast: the columns must stay aligned
across three positional lists, and a bad row must not be able to produce a
half-seeded account again.
"""
import ast
import inspect
import re

import pytest

from app.api import seed as seed_mod


# The event fields, in the order the statement's arrays are passed.
EXPECTED_COLUMN_ORDER = [
    "reel_id", "username", "caption", "hashtags",
    "audio", "watch_time", "timestamp", "session_id",
]


def _sql() -> str:
    """The INSERT statement _store_events sends."""
    src = inspect.getsource(seed_mod._store_events)
    m = re.search(r'"""\s*(INSERT INTO events.*?)"""', src, re.S)
    assert m, "could not find the INSERT statement"
    return m.group(1)


def test_insert_is_one_statement_not_a_loop():
    """The defect was the loop, so the loop is what must not come back."""
    tree = ast.parse(inspect.getsource(seed_mod.seed_demo_data).lstrip())
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)):
            body = ast.dump(node)
            assert "INSERT INTO events" not in body, \
                "events are being inserted inside a loop again"

    # And the statement itself covers many rows rather than one.
    sql = _sql()
    assert "unnest(" in sql
    assert "VALUES (" not in sql, "single-row VALUES form is back"


def test_columns_and_arrays_stay_aligned():
    """Eight parallel arrays, three positional lists, one chance to swap two.

    A swap here is silent: usernames land in captions, the seed still succeeds,
    and the demo profile is quietly wrong. So check the statement's own three
    orderings agree - the INSERT column list, the SELECT list, and the unnest
    alias - and that they match the order _store_events builds the arrays in.
    """
    sql = _sql()

    columns = re.search(r"INSERT INTO events \(([^)]*)\)", sql, re.S).group(1)
    columns = [c.strip() for c in columns.replace("\n", " ").split(",") if c.strip()]
    assert columns[0] == "user_id", columns
    # events.audio holds what the event calls audio_info; the rest share names.
    assert columns[1:] == [
        "reel_id", "username", "caption", "hashtags",
        "audio", "watch_time", "timestamp", "session_id",
    ], columns

    alias = re.search(r"AS e\(([^)]*)\)", sql).group(1)
    alias = [a.strip() for a in alias.split(",")]

    select = re.search(r"SELECT \$1, (.*?)\s*FROM unnest", sql, re.S).group(1)
    select = [s.strip().split("::")[0] for s in select.split(",")]
    assert select == alias, "SELECT order does not match the unnest alias"
    assert len(alias) == len(columns) - 1, "one array per column after user_id"


def test_arrays_are_built_in_the_statement_order():
    """The Python side must feed the arrays in the order the SQL reads them."""
    src = inspect.getsource(seed_mod._store_events)
    keys = re.findall(r'for e in events\]|\be\["(\w+)"\]', src)
    keys = [k for k in keys if k]
    # audio_info is the event's name for what the column calls audio.
    normalised = ["audio" if k == "audio_info" else k for k in keys]
    assert normalised == EXPECTED_COLUMN_ORDER, normalised


@pytest.mark.asyncio
async def test_every_event_gets_its_row_id(monkeypatch):
    """The pipeline links behaviour objects to events by these ids.

    Keyed by content id rather than by position, because RETURNING makes no
    promise about the order rows come back in.
    """
    captured = {}

    async def fake_fetch(sql, *args):
        captured["sql"] = sql
        captured["args"] = args
        reel_ids = args[1]
        # Deliberately reversed: nothing may depend on the returned order.
        return [{"id": 100 + i, "reel_id": r}
                for i, r in reversed(list(enumerate(reel_ids)))]

    monkeypatch.setattr(seed_mod, "fetch", fake_fetch)

    events = [{
        "reel_id": "r%d" % i, "username": "u%d" % i, "caption": "c%d" % i,
        "hashtags": ["#a"], "audio": "a.mp3", "watch_time": 1.5 + i,
        "timestamp": "2026-01-0%dT00:00:00+00:00" % (i + 1),
        "session_id": "s%d" % i,
    } for i in range(3)]

    stored, mapping = await seed_mod._store_events("u", events)

    assert stored == 3
    assert mapping == {"r0": 100, "r1": 101, "r2": 102}

    # Each array carries that column's values, in event order.
    args = captured["args"]
    assert args[0] == "u"
    assert args[1] == ["r0", "r1", "r2"]
    assert args[2] == ["u0", "u1", "u2"]
    assert args[3] == ["c0", "c1", "c2"]
    assert args[6] == [1.5, 2.5, 3.5]
    assert [a[:10] for a in args[8]] == ["s0", "s1", "s2"]


@pytest.mark.asyncio
async def test_a_bad_row_fails_the_seed_rather_than_half_doing_it(monkeypatch):
    """A half-seeded account is the defect; an error the caller sees is not.

    The old loop caught per-event failures and carried on, which is how an
    account ends up looking populated and answering nothing.
    """
    async def boom(sql, *args):
        raise ValueError("bad row")

    monkeypatch.setattr(seed_mod, "fetch", boom)

    with pytest.raises(ValueError):
        await seed_mod._store_events("u", [{
            "reel_id": "r", "username": "u", "caption": "c", "hashtags": [],
            "audio": "a", "watch_time": 1.0,
            "timestamp": "2026-01-01T00:00:00+00:00", "session_id": "s",
        }])

    # There is no per-event exception handler left to swallow it.
    tree = ast.parse(inspect.getsource(seed_mod._store_events).lstrip())
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)], \
        "_store_events swallows failures again"


def test_hashtags_are_sent_as_json_text_and_cast():
    """The column is jsonb; asyncpg will not adapt a Python list into it."""
    src = inspect.getsource(seed_mod._store_events)
    assert "json.dumps(e[\"hashtags\"])" in src
    assert "h::jsonb" in _sql()
