"""The accuracy ledger has to be honest about itself, or it is worse than nothing.

This is the feature that turns the product's own argument back on it: when
AIMirror told you something about yourself, was it right? A number here that
flatters the system would be the exact failure the Mirror and Provenance
reports exist to call out in platforms.

So what is pinned is mostly the statistics and the refusals:

  * a rate is never reported from a sample too small to mean anything, and
    "not enough data" is never rendered as 0%
  * the interval is Wilson, because the normal approximation claims certainty
    at precisely the small samples this will live in
  * "unsure" is counted but not scored - it is an answer, not an outcome
  * the confidence being scored is the one claimed AT THE TIME, so the
    pipeline recomputing confidences cannot rewrite the system's record
"""
import math

import pytest

from app.services import calibration as cal


class TestWilsonInterval:
    def test_perfect_score_does_not_claim_certainty(self):
        """The reason Wilson is used at all. The normal approximation gives
        [1.0, 1.0] for 10/10 - a claim of total certainty from ten clicks."""
        low, high = cal.wilson_interval(10, 10)
        assert high == 1.0
        assert low < 0.8, f"10/10 should not imply near-certainty, got lower bound {low}"

    def test_zero_score_does_not_claim_certainty_either(self):
        low, high = cal.wilson_interval(0, 10)
        assert low == 0.0
        assert high > 0.2

    def test_interval_contains_the_point_estimate(self):
        for successes, total in [(1, 10), (5, 10), (9, 10), (50, 100), (3, 7)]:
            low, high = cal.wilson_interval(successes, total)
            assert low <= successes / total <= high, f"{successes}/{total}"

    def test_interval_narrows_as_evidence_accumulates(self):
        small = cal.wilson_interval(7, 10)
        large = cal.wilson_interval(700, 1000)
        assert (large[1] - large[0]) < (small[1] - small[0])

    def test_empty_sample_is_maximally_uncertain(self):
        assert cal.wilson_interval(0, 0) == [0.0, 1.0]

    def test_bounds_stay_inside_zero_and_one(self):
        for successes, total in [(0, 1), (1, 1), (1, 2), (99, 100)]:
            low, high = cal.wilson_interval(successes, total)
            assert 0.0 <= low <= high <= 1.0


class TestBrierScore:
    def test_none_without_data(self):
        assert cal._brier([]) is None

    def test_perfect_confident_predictions_score_zero(self):
        scored = [{"confidence_at_verdict": 1.0, "verdict": "right"}] * 5
        assert cal._brier(scored) == 0.0

    def test_confidently_wrong_is_the_worst_score(self):
        scored = [{"confidence_at_verdict": 1.0, "verdict": "wrong"}] * 5
        assert cal._brier(scored) == 1.0

    def test_hedging_everything_scores_a_quarter(self):
        """Claiming 0.5 about everything gives 0.25 regardless of outcome -
        the baseline a system beats only by actually knowing something."""
        scored = [
            {"confidence_at_verdict": 0.5, "verdict": "right"},
            {"confidence_at_verdict": 0.5, "verdict": "wrong"},
        ]
        assert cal._brier(scored) == 0.25

    def test_it_punishes_overconfidence_more_than_hedging(self):
        """Two wrong claims: one hedged, one certain. The certain one must
        score worse, which plain accuracy cannot express."""
        hedged = cal._brier([{"confidence_at_verdict": 0.5, "verdict": "wrong"}])
        certain = cal._brier([{"confidence_at_verdict": 0.95, "verdict": "wrong"}])
        assert certain > hedged


def _verdicts(*specs):
    """(confidence, verdict, count) -> rows shaped like the table."""
    rows = []
    for confidence, verdict, count in specs:
        rows.extend([{
            "claim_type": "inference", "claim_id": f"c{len(rows)}_{i}",
            "verdict": verdict, "confidence_at_verdict": confidence,
            "claim_label": "x", "created_at": None,
        } for i in range(count)])
    return rows


async def _report(monkeypatch, rows):
    async def fake_fetch(*_a, **_k):
        return rows
    monkeypatch.setattr(cal, "fetch", fake_fetch)
    return await cal.build_calibration_report("u")


class TestRefusalToOverclaim:
    @pytest.mark.asyncio
    async def test_no_verdict_below_the_sample_floor(self, monkeypatch):
        report = await _report(monkeypatch, _verdicts((0.9, "right", 5)))
        assert report["measurable"] is False
        assert report["accuracy"] is None
        assert str(cal.MIN_TOTAL_SAMPLES) in report["verdict"]

    @pytest.mark.asyncio
    async def test_a_thin_bucket_reports_none_not_zero(self, monkeypatch):
        """The failure that would make this feature actively misleading:
        rendering 'no data' as a 0% accuracy bar."""
        report = await _report(monkeypatch, _verdicts((0.9, "right", 3)))
        bucket = next(b for b in report["buckets"] if b["range"] == "0.8-1.0")
        assert bucket["samples"] == 3
        assert bucket["observed_rate"] is None
        assert bucket["assessment"] == "insufficient_data"
        assert bucket["needed"] == cal.MIN_BUCKET_SAMPLES - 3

    @pytest.mark.asyncio
    async def test_an_empty_ledger_is_not_an_error(self, monkeypatch):
        report = await _report(monkeypatch, [])
        assert report["measurable"] is False
        assert report["summary"]["scored"] == 0
        assert report["brier_score"] is None


class TestCalibrationJudgement:
    @pytest.mark.asyncio
    async def test_it_names_overconfidence(self, monkeypatch):
        """A 0.8-1.0 bucket (midpoint 0.9) right only half the time."""
        report = await _report(monkeypatch, _verdicts(
            (0.9, "right", 10), (0.9, "wrong", 10),
        ))
        bucket = next(b for b in report["buckets"] if b["range"] == "0.8-1.0")
        assert bucket["observed_rate"] == 0.5
        assert bucket["assessment"] == "overconfident"
        assert "overconfident" in report["verdict"]

    @pytest.mark.asyncio
    async def test_it_accepts_a_well_calibrated_band(self, monkeypatch):
        """Midpoint 0.9, right 90% of the time."""
        report = await _report(monkeypatch, _verdicts(
            (0.9, "right", 18), (0.9, "wrong", 2),
        ))
        bucket = next(b for b in report["buckets"] if b["range"] == "0.8-1.0")
        assert bucket["assessment"] == "calibrated"
        assert "overconfident" not in report["verdict"]

    @pytest.mark.asyncio
    async def test_underconfidence_is_a_distinct_finding(self, monkeypatch):
        """Claiming 0.1 and being right most of the time is also miscalibrated,
        and must not be quietly filed as good news."""
        report = await _report(monkeypatch, _verdicts(
            (0.1, "right", 18), (0.1, "wrong", 2),
        ))
        bucket = next(b for b in report["buckets"] if b["range"] == "0.0-0.2")
        assert bucket["assessment"] == "underconfident"

    @pytest.mark.asyncio
    async def test_being_accurate_overall_does_not_hide_a_bad_band(self, monkeypatch):
        """The whole point of bucketing. 80% overall accuracy while the
        most confident claims are coin flips."""
        report = await _report(monkeypatch, _verdicts(
            (0.3, "right", 30),                      # low-confidence, all right
            (0.9, "right", 10), (0.9, "wrong", 10),  # high-confidence, half wrong
        ))
        assert report["accuracy"] == 0.8
        top = next(b for b in report["buckets"] if b["range"] == "0.8-1.0")
        assert top["assessment"] == "overconfident"
        assert "overconfident" in report["verdict"]


class TestUnsure:
    @pytest.mark.asyncio
    async def test_unsure_is_counted_but_not_scored(self, monkeypatch):
        report = await _report(monkeypatch, _verdicts(
            (0.9, "right", 20), (0.9, "unsure", 7),
        ))
        assert report["summary"]["verdicts_total"] == 27
        assert report["summary"]["scored"] == 20
        assert report["summary"]["unsure"] == 7
        assert report["accuracy"] == 1.0  # unsure must not count as wrong

    @pytest.mark.asyncio
    async def test_unsure_alone_is_not_measurable(self, monkeypatch):
        report = await _report(monkeypatch, _verdicts((0.9, "unsure", 30)))
        assert report["measurable"] is False
        assert report["summary"]["scored"] == 0


class TestBucketBoundaries:
    @pytest.mark.asyncio
    async def test_every_scored_verdict_lands_in_exactly_one_bucket(self, monkeypatch):
        rows = _verdicts(*[(c, "right", 1) for c in
                           (0.0, 0.19, 0.2, 0.39, 0.4, 0.59, 0.6, 0.79, 0.8, 0.99, 1.0)])
        report = await _report(monkeypatch, rows)
        assert sum(b["samples"] for b in report["buckets"]) == len(rows)

    @pytest.mark.asyncio
    async def test_confidence_of_exactly_one_is_not_dropped(self, monkeypatch):
        """Half-open ranges silently lose 1.0 unless the top bucket closes."""
        report = await _report(monkeypatch, _verdicts((1.0, "right", 4)))
        top = next(b for b in report["buckets"] if b["range"] == "0.8-1.0")
        assert top["samples"] == 4


class TestValidation:
    @pytest.mark.asyncio
    async def test_rejects_an_unknown_verdict(self):
        with pytest.raises(ValueError):
            await cal.record_verdict("u", "inference", "c1", "maybe")

    @pytest.mark.asyncio
    async def test_rejects_an_unknown_claim_type(self):
        with pytest.raises(ValueError):
            await cal.record_verdict("u", "horoscope", "c1", "right")

    def test_the_sql_table_names_are_not_caller_controlled(self):
        """record_verdict interpolates a table name into SQL. It must come
        from the fixed map, never from the request."""
        import inspect
        source = inspect.getsource(cal.record_verdict)
        assert "_SOURCE[claim_type]" in source
        assert set(cal._SOURCE) == set(cal.VALID_CLAIM_TYPES)


# -- Behaviour against the live database -------------------------------------

import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def demo_user_id(db):
    """A throwaway id under a PUBLIC prefix, cleaned up afterwards.

    Not conftest's demo_user_id, which uses `pytest_<hex>`: that is not
    a public id, so app/api/deps.py correctly rejects it with 401 and these
    endpoints never run. Using a demo_ prefix exercises the signed-out path
    the dashboard actually uses.
    """
    user_id = f"demo_cal_{uuid.uuid4().hex[:8]}"
    yield user_id
    from app.services import data_privacy
    try:
        await data_privacy.delete_all_user_data(user_id)
    except Exception:
        pass


async def _seed_inference(user_id, confidence=0.9, label="Likes wildlife content"):
    from app.db.postgres import execute

    inference_id = f"inf_{uuid.uuid4().hex[:12]}"
    await execute(
        """
        INSERT INTO inferences (inference_id, user_id, inference_type, label,
                                description, confidence, inferred_at, valid_from)
        VALUES ($1, $2, 'interest', $3, $4, $5, NOW(), NOW())
        """,
        inference_id, user_id, label, "seeded by a test", confidence,
    )
    return inference_id


@pytest.mark.db
@pytest.mark.asyncio
async def test_a_verdict_round_trips(db, demo_user_id, client):
    inference_id = await _seed_inference(demo_user_id, confidence=0.85)

    resp = await client.post("/calibration/verdict", json={
        "user_id": demo_user_id, "claim_type": "inference",
        "claim_id": inference_id, "verdict": "wrong",
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["confidence_at_verdict"] == 0.85

    report = (await client.get(
        f"/calibration/report?user_id={demo_user_id}")).json()
    assert report["summary"]["scored"] == 1
    assert report["summary"]["correct"] == 0


@pytest.mark.db
@pytest.mark.asyncio
async def test_changing_your_mind_updates_rather_than_stacking(db, demo_user_id, client):
    """Otherwise clicking repeatedly inflates the sample the report is built on."""
    inference_id = await _seed_inference(demo_user_id)

    for verdict in ("right", "wrong", "right"):
        resp = await client.post("/calibration/verdict", json={
            "user_id": demo_user_id, "claim_type": "inference",
            "claim_id": inference_id, "verdict": verdict,
        })
        assert resp.status_code == 200, resp.text

    report = (await client.get(
        f"/calibration/report?user_id={demo_user_id}")).json()
    assert report["summary"]["verdicts_total"] == 1
    assert report["summary"]["correct"] == 1


@pytest.mark.db
@pytest.mark.asyncio
async def test_the_scored_confidence_is_frozen_at_verdict_time(db, demo_user_id, client):
    """The pipeline recomputes confidences on every run. If the report joined
    the live value instead of the stored one, re-running the pipeline would
    silently rescore the system's past claims - it could look better simply
    by becoming less sure after the fact."""
    from app.db.postgres import execute

    inference_id = await _seed_inference(demo_user_id, confidence=0.9)
    await client.post("/calibration/verdict", json={
        "user_id": demo_user_id, "claim_type": "inference",
        "claim_id": inference_id, "verdict": "wrong",
    })

    await execute("UPDATE inferences SET confidence = 0.1 WHERE inference_id = $1",
                  inference_id)

    report = (await client.get(
        f"/calibration/report?user_id={demo_user_id}")).json()
    top = next(b for b in report["buckets"] if b["range"] == "0.8-1.0")
    assert top["samples"] == 1, "the verdict was rescored against the new confidence"


@pytest.mark.db
@pytest.mark.asyncio
async def test_you_cannot_rate_a_claim_about_someone_else(db, demo_user_id, client):
    """record_verdict scopes its lookup by user_id, so another user's claim
    is simply not found - no cross-user write, and no oracle telling you the
    id exists."""
    other = f"demo_other_{uuid.uuid4().hex[:8]}"
    from app.services import data_privacy

    try:
        theirs = await _seed_inference(other)
        resp = await client.post("/calibration/verdict", json={
            "user_id": demo_user_id, "claim_type": "inference",
            "claim_id": theirs, "verdict": "right",
        })
        assert resp.status_code == 404
    finally:
        await data_privacy.delete_all_user_data(other)


@pytest.mark.db
@pytest.mark.asyncio
async def test_open_claims_lead_with_the_most_confident(db, demo_user_id, client):
    """A confident claim that turns out to be wrong is the most informative
    answer available, and the one this report exists to surface."""
    await _seed_inference(demo_user_id, confidence=0.3, label="low")
    await _seed_inference(demo_user_id, confidence=0.95, label="high")

    open_claims = (await client.get(
        f"/calibration/open?user_id={demo_user_id}")).json()
    assert [c["label"] for c in open_claims][:2] == ["high", "low"]


@pytest.mark.db
@pytest.mark.asyncio
async def test_an_answered_claim_leaves_the_open_list(db, demo_user_id, client):
    inference_id = await _seed_inference(demo_user_id)
    assert len((await client.get(
        f"/calibration/open?user_id={demo_user_id}")).json()) == 1

    await client.post("/calibration/verdict", json={
        "user_id": demo_user_id, "claim_type": "inference",
        "claim_id": inference_id, "verdict": "right",
    })
    assert (await client.get(
        f"/calibration/open?user_id={demo_user_id}")).json() == []


@pytest.mark.db
@pytest.mark.asyncio
async def test_erasure_takes_the_verdicts_too(db, client):
    """They are the user's own answers about themselves."""
    from app.db.postgres import fetchval
    from app.services import data_privacy

    user_id = f"demo_cal_{uuid.uuid4().hex[:8]}"
    inference_id = await _seed_inference(user_id)
    await client.post("/calibration/verdict", json={
        "user_id": user_id, "claim_type": "inference",
        "claim_id": inference_id, "verdict": "right",
    })
    assert await fetchval(
        "SELECT COUNT(*) FROM claim_verdicts WHERE user_id = $1", user_id) == 1

    await data_privacy.delete_all_user_data(user_id)
    assert await fetchval(
        "SELECT COUNT(*) FROM claim_verdicts WHERE user_id = $1", user_id) == 0
