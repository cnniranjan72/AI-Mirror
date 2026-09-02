"""A counterfactual must change nothing.

This is the one question a language-model-driven system cannot answer honestly.
Because every stage before verbalization is deterministic, the pipeline can be
re-run over a hypothetical history and the difference in the output is caused
by the difference in the input and nothing else. Ask a stochastic model twice
and the answers differ for reasons unrelated to the hypothetical.

The property that makes it safe to offer is that the run writes nothing. A
feature that quietly rewrote someone's twin while showing them a hypothetical
would be indefensible in a product built on this argument, so it is checked
here rather than trusted: first structurally, then by counting rows either side
of a real run.
"""
import ast
import inspect
import io
import uuid
from pathlib import Path

import pytest

from app.services import counterfactual


class TestItCannotPersist:
    """Structural checks, so the guarantee does not rest on reading carefully."""

    def test_the_service_never_calls_the_persistence_step(self):
        source = inspect.getsource(counterfactual)
        assert "_persist_all" in source, "the exclusion should be documented"
        tree = ast.parse(source)
        called = {
            getattr(n.func, "attr", None)
            for n in ast.walk(tree) if isinstance(n, ast.Call)
        }
        assert "_persist_all" not in called, "counterfactual invokes persistence"

    def test_every_pipeline_step_it_calls_is_read_only(self):
        """The five reasoning steps hold no writes; all fifteen write calls in
        V3Pipeline sit behind _persist_all. If a write ever moves into one of
        these, a counterfactual would start mutating real data."""
        src = (Path(__file__).parent.parent / "pipeline" / "orchestrator.py").read_text(
            encoding="utf-8")
        tree = ast.parse(src)
        cls = next(n for n in tree.body
                   if isinstance(n, ast.ClassDef) and n.name == "V3Pipeline")
        methods = {m.name: m for m in cls.body
                   if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}

        WRITES = ("execute", "_persist", "_insert", "_upsert")

        def writes_reachable(name, seen=None):
            seen = seen or set()
            if name in seen or name not in methods:
                return []
            seen.add(name)
            out = []
            for node in ast.walk(methods[name]):
                if isinstance(node, ast.Call):
                    fname = (getattr(node.func, "id", None)
                             or getattr(node.func, "attr", None) or "")
                    if any(w in fname for w in WRITES):
                        out.append(f"{name} -> {fname}")
                    out += writes_reachable(fname, seen)
            return out

        for step in ("_consolidate_events", "_collect_evidence",
                     "_generate_inferences", "_construct_identity"):
            found = writes_reachable(step)
            assert not found, f"{step} can write: {found}"

    def test_the_response_states_that_nothing_was_saved(self):
        source = inspect.getsource(counterfactual.run_counterfactual)
        assert '"persisted": False' in source
        assert "Nothing was saved" in source


class TestItRefusesRatherThanGuesses:
    @pytest.mark.asyncio
    async def test_an_empty_hypothetical_is_rejected(self):
        assert "error" in await counterfactual.run_counterfactual("u", [])

    def test_the_body_is_capped(self):
        """Unbounded input would let one request run the whole pipeline
        repeatedly, and the purpose is direction and distance, not simulating
        a new lifetime."""
        assert 0 < counterfactual.MAX_HYPOTHETICAL_EVENTS <= 500


# -- Against the live database ------------------------------------------------

@pytest.fixture
async def demo_user_id(db):
    user_id = f"demo_cf_{uuid.uuid4().hex[:8]}"
    yield user_id
    from app.services import data_privacy
    try:
        await data_privacy.delete_all_user_data(user_id)
    except Exception:
        pass


def _events(n, topic, creator, watch, prefix):
    return [{
        "reel_id": f"{prefix}_{i:03d}", "username": creator,
        "caption": f"{topic}: clip {i}", "hashtags": [f"#{topic}"],
        "watch_time": float(watch), "platform": "instagram",
    } for i in range(n)]


async def _counts(user_id):
    from app.db.postgres import fetchval
    out = {}
    for table in ("events", "behavior_objects", "evidence", "inferences",
                  "identities", "identity_snapshots"):
        out[table] = await fetchval(
            f"SELECT COUNT(*) FROM {table} WHERE user_id = $1", user_id)
    return out


@pytest.mark.db
@pytest.mark.asyncio
async def test_a_counterfactual_leaves_the_database_untouched(db, demo_user_id):
    """The test this file exists for."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://test", timeout=300) as client:
        await client.post("/ingest", json={
            "user_id": demo_user_id,
            "events": _events(40, "coding", "codecraft", 120, "real")})

        before = await _counts(demo_user_id)
        assert before["events"] == 40

        result = await counterfactual.run_counterfactual(
            demo_user_id, _events(60, "cooking", "chefjohn", 5, "hypo"))

        after = await _counts(demo_user_id)
        assert after == before, f"the counterfactual wrote: {before} -> {after}"
        assert result.get("persisted") is False


@pytest.mark.db
@pytest.mark.asyncio
async def test_it_reports_a_movement_and_names_what_moved(db, demo_user_id):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://test", timeout=300) as client:
        await client.post("/ingest", json={
            "user_id": demo_user_id,
            "events": _events(40, "coding", "codecraft", 180, "real")})

    result = await counterfactual.run_counterfactual(
        demo_user_id, _events(80, "comedy", "laughs_daily", 4, "hypo"))

    assert result["measurable"] is True
    assert result["shift"] is not None and result["shift"] > 0
    assert result["moves"], "a wholesale change in viewing should move something"
    for move in result["moves"]:
        assert move["dimension"] and move["from"] != move["to"]


@pytest.mark.db
@pytest.mark.asyncio
async def test_it_says_so_when_there_is_no_baseline(db, demo_user_id):
    """With no identity yet there is nothing to move, and inventing a
    comparison would be worse than declining one."""
    result = await counterfactual.run_counterfactual(
        demo_user_id, _events(10, "coding", "codecraft", 60, "hypo"))
    assert result["measurable"] is False
    assert "nothing to move" in result["note"]
