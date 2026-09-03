"""What an account is told when it cannot be answered about yet.

Reads come from a frozen identity snapshot, so an account without one stops the
pipeline before it plans anything. The request then fell through to the simple
retrieval path, which found nothing and rendered the default template around
it: "Here's what I found relevant to your query: / No behavioral data found
yet. / This is based on 0 behavioral data points." A claim to have searched and
a report of nothing, in one breath - and it is the first thing a new account
sees, because asking a question is the first thing anyone does.

The same sentence also covered a genuinely broken account, so nobody could tell
the two apart.

These tests hold the distinctions that make the replacement honest rather than
merely friendlier:

  - an answerable account gets no explanation, so a real failure stays visible
    as a failure instead of being dressed up as missing data;
  - an account with plenty of events is not told to go and collect more;
  - the turn is remembered whichever path answered it.
"""
import inspect

import pytest

from app.services import readiness


def state(**kw):
    base = {"state": readiness.STATE_READY, "events": 0,
            "behaviours": 0, "snapshots": 0}
    base.update(kw)
    return base


class FakeRow(dict):
    pass


@pytest.mark.asyncio
async def test_a_snapshot_means_answerable_whatever_else_is_missing(monkeypatch):
    async def fake(sql, *args):
        return FakeRow(events=0, behaviours=0, snapshots=1)

    monkeypatch.setattr(readiness, "fetchrow", fake)
    assert (await readiness.account_state("u"))["state"] == readiness.STATE_READY


@pytest.mark.asyncio
async def test_the_states_are_distinguished(monkeypatch):
    cases = [
        ((0, 0, 0), readiness.STATE_NO_EVENTS),
        ((40, 0, 0), readiness.STATE_NOT_CONSOLIDATED),
        ((40, 6, 0), readiness.STATE_NO_IDENTITY),
        ((40, 6, 2), readiness.STATE_READY),
    ]
    for (events, behaviours, snapshots), expected in cases:
        async def fake(sql, *args, _e=events, _b=behaviours, _s=snapshots):
            return FakeRow(events=_e, behaviours=_b, snapshots=_s)

        monkeypatch.setattr(readiness, "fetchrow", fake)
        got = await readiness.account_state("u")
        assert got["state"] == expected, (events, behaviours, snapshots, got)


@pytest.mark.asyncio
async def test_a_failed_read_does_not_invent_an_excuse(monkeypatch):
    """If the state cannot be read, the account must be treated as answerable.

    The alternative is telling someone their account is empty because a count
    query failed, which is a confident wrong answer about their own data.
    """
    async def boom(sql, *args):
        raise RuntimeError("db gone")

    monkeypatch.setattr(readiness, "fetchrow", boom)
    got = await readiness.account_state("u")
    assert got["state"] == readiness.STATE_READY
    assert readiness.explain(got) is None


def test_an_answerable_account_gets_no_explanation():
    """A real failure must stay a failure.

    This is the load-bearing one. If explain() returned something soothing for
    a ready account, every breakage would read to the user as "no data yet" and
    to the operator as normal.
    """
    assert readiness.explain(state(state=readiness.STATE_READY, snapshots=1)) is None


def test_an_empty_account_is_told_how_to_start():
    msg = readiness.explain(state(state=readiness.STATE_NO_EVENTS))
    assert msg
    assert "extension" in msg.lower()
    assert "demo" in msg.lower()


def test_an_early_account_is_told_to_keep_going():
    msg = readiness.explain(
        state(state=readiness.STATE_NOT_CONSOLIDATED, events=4))
    assert "4 events" in msg
    assert str(readiness._CLUSTER_FLOOR) in msg


def test_an_account_with_plenty_of_events_is_not_blamed():
    """159 events with nothing derived is not a shortage of history.

    Every account measured produced its first cluster within a dozen events, so
    telling this person to keep browsing would be blaming them for a gap on our
    side - and it was: those accounts were interrupted seeds.
    """
    msg = readiness.explain(
        state(state=readiness.STATE_NOT_CONSOLIDATED, events=159))
    assert "159" in msg
    assert "my side" in msg
    assert "keep browsing" not in msg.lower()
    assert "isn't enough history" not in msg.lower()


def test_the_boundary_is_where_the_measurement_put_it():
    """Below the threshold reads as early, at or above it reads as our gap."""
    n = readiness._EXPECT_A_PATTERN_BY
    early = readiness.explain(state(state=readiness.STATE_NOT_CONSOLIDATED, events=n - 1))
    late = readiness.explain(state(state=readiness.STATE_NOT_CONSOLIDATED, events=n))
    assert "keep browsing" in early.lower()
    assert "my side" in late
    # The measurement: a first cluster appeared within 12 events on every
    # account checked, so the boundary must sit above that and not absurdly
    # far above it.
    assert 12 < n <= 100


def test_a_stalled_pipeline_says_so_without_giving_orders():
    msg = readiness.explain(
        state(state=readiness.STATE_NO_IDENTITY, events=40, behaviours=6))
    assert "6 patterns" in msg
    assert "my side" in msg


def test_singulars_read_like_english():
    one = readiness.explain(state(state=readiness.STATE_NOT_CONSOLIDATED, events=1))
    assert "1 event," in one and "1 events" not in one
    one_pattern = readiness.explain(
        state(state=readiness.STATE_NO_IDENTITY, events=9, behaviours=1))
    assert "1 pattern " in one_pattern and "1 patterns" not in one_pattern


def test_no_message_claims_to_have_searched():
    """The defect was a template that said it had looked and found nothing."""
    for name, kw in (
        (readiness.STATE_NO_EVENTS, {}),
        (readiness.STATE_NOT_CONSOLIDATED, {"events": 4}),
        (readiness.STATE_NOT_CONSOLIDATED, {"events": 400}),
        (readiness.STATE_NO_IDENTITY, {"events": 40, "behaviours": 6}),
    ):
        msg = readiness.explain(state(state=name, **kw))
        low = msg.lower()
        assert "here's what i found" not in low
        assert "based on 0" not in low
        assert "no behavioral data found" not in low


def test_the_query_endpoint_answers_from_the_account_state():
    """The handler must consult the state before falling back to retrieval,
    and must report which state it was."""
    import textwrap

    from app.api import query as qmod

    src = textwrap.dedent(inspect.getsource(qmod.query_insights))
    assert "readiness.account_state" in src
    assert "readiness.explain" in src
    assert "data_state=state[\"state\"]" in src
    assert "data_state" in qmod.QueryResponse.model_fields

    # And the state check comes before the retrieval fallback, or the
    # misleading template answers first and nothing else matters.
    assert src.index("readiness.explain") < src.index("rag.query")


def test_every_answering_path_remembers_the_turn():
    """Only the successful path used to persist.

    A new account's first conversation - the one explaining why its history is
    empty - was returned and then dropped.
    """
    import textwrap

    from app.api import query as qmod

    src = textwrap.dedent(inspect.getsource(qmod.query_insights))
    assert src.count("_remember(") >= 3, (
        "an answering path is not persisting its turn")
    assert "chat_memory.save_message" not in src, (
        "a path is saving directly instead of through the one helper")


@pytest.mark.asyncio
async def test_a_persistence_failure_does_not_fail_the_request(monkeypatch):
    """Losing the transcript is bad; losing the answer over it is worse.

    Asserted by calling it rather than by reading the source: a mutation run
    killed the first version of this test, which checked that the words
    "except Exception" appeared. Replacing the handler's body with `raise`
    leaves those words exactly where they were.
    """
    from app.api import query as qmod

    calls = []

    async def boom(*args, **kwargs):
        calls.append(args)
        raise RuntimeError("chat store down")

    monkeypatch.setattr(qmod.chat_memory, "save_message", boom)
    await qmod._remember("u", "c", "why?", "because")  # must not raise
    assert calls, "the helper never attempted to save"


@pytest.mark.asyncio
async def test_both_halves_of_a_turn_are_saved(monkeypatch):
    """A turn is the question and the answer; storing one is worse than none,
    because the transcript then reads as though nobody replied."""
    from app.api import query as qmod

    saved = []

    async def record(user_id, conversation_id, role, content, **kw):
        saved.append((role, content))

    monkeypatch.setattr(qmod.chat_memory, "save_message", record)
    await qmod._remember("u", "c", "why?", "because")

    assert saved == [("user", "why?"), ("assistant", "because")]


@pytest.mark.asyncio
async def test_an_empty_answer_is_not_persisted(monkeypatch):
    """Nothing was said, so there is no turn to keep."""
    from app.api import query as qmod

    saved = []

    async def record(*args, **kwargs):
        saved.append(args)

    monkeypatch.setattr(qmod.chat_memory, "save_message", record)
    await qmod._remember("u", "c", "why?", "")
    assert saved == []
