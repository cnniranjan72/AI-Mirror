"""The accuracy ledger: what the system claimed, and whether it was right.

Every other feature here audits somebody else. The Mirror checks a platform's
stated claims against observed behaviour; Provenance asks whether an interest
was chosen or fed. This one turns the same question on AIMirror: when it told
you something about yourself, was it correct?

Accuracy alone would be a weak answer, because it is trivially gamed by never
claiming anything confidently. The stronger question is CALIBRATION — when the
system says 0.8, is it right about 80% of the time? A calibrated system can be
wrong often, as long as it knew it might be. An overconfident one is the
failure this measures.

Statistical discipline, matching algorithmic_mirror and interest_provenance:
a number computed from four data points is noise wearing a decimal point, so
buckets below MIN_BUCKET_SAMPLES report no rate at all, and the overall report
withholds a verdict below MIN_TOTAL_SAMPLES. Wilson intervals are used rather
than the normal approximation, which is badly wrong at exactly the small
samples and extreme proportions this will spend most of its life in.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from app.db.postgres import execute, fetch, fetchrow

logger = logging.getLogger(__name__)

# Confidence buckets. Edges are half-open [lo, hi) except the last, so a
# claim at exactly 1.0 lands somewhere.
BUCKETS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]

# Below this a bucket's rate is not reported. Ten is already generous — the
# 95% interval on 7/10 still spans roughly 0.40 to 0.89 — but demanding more
# would mean showing nothing at all for a long time, so the interval is shown
# alongside every rate instead of pretending the point estimate is the answer.
MIN_BUCKET_SAMPLES = 10

# Below this the report states no overall verdict. Same reasoning as
# MIN_COVERAGE_FOR_VERDICT in algorithmic_mirror: a confident summary from a
# handful of clicks is worse than admitting there is not enough yet.
MIN_TOTAL_SAMPLES = 20

# How far the observed rate may sit from the bucket's claimed confidence
# before the system is called overconfident. Slack is needed because bucket
# midpoints are coarse: a 0.6-0.8 bucket full of 0.61 claims should not be
# scored against 0.7.
CALIBRATION_TOLERANCE = 0.15

VALID_VERDICTS = ("right", "wrong", "unsure")
VALID_CLAIM_TYPES = ("inference", "reflection")

_SOURCE = {
    "inference": ("inferences", "inference_id", "label"),
    "reflection": ("reflections", "reflection_id", "summary"),
}


async def record_verdict(
    user_id: str, claim_type: str, claim_id: str, verdict: str
) -> Dict[str, Any]:
    """Record what the user says about one claim.

    The claim's confidence is read from the source row and COPIED here.
    Calibration is a question about what the system claimed at the time, and
    the pipeline recomputes confidences on every run — a later join would
    quietly rescore old answers against new numbers.
    """
    if claim_type not in VALID_CLAIM_TYPES:
        raise ValueError(f"unknown claim_type: {claim_type}")
    if verdict not in VALID_VERDICTS:
        raise ValueError(f"unknown verdict: {verdict}")

    table, id_column, label_column = _SOURCE[claim_type]
    row = await fetchrow(
        f"SELECT confidence, {label_column} AS label FROM {table} "
        f"WHERE {id_column} = $1 AND user_id = $2",
        claim_id, user_id,
    )
    if not row:
        # Scoped to user_id above, so this is also the authorization check:
        # you cannot rate a claim the system made about somebody else.
        return {"recorded": False, "reason": "claim_not_found"}

    confidence = float(row["confidence"] or 0.0)
    await execute(
        """
        INSERT INTO claim_verdicts
            (user_id, claim_type, claim_id, verdict, confidence_at_verdict, claim_label)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (user_id, claim_type, claim_id) DO UPDATE
            SET verdict = EXCLUDED.verdict,
                -- confidence_at_verdict is deliberately NOT refreshed: the
                -- user is changing their answer, not the claim being scored.
                claim_label = EXCLUDED.claim_label,
                updated_at = NOW()
        """,
        user_id, claim_type, claim_id, verdict, confidence, (row["label"] or "")[:500],
    )
    return {"recorded": True, "claim_type": claim_type, "claim_id": claim_id,
            "verdict": verdict, "confidence_at_verdict": round(confidence, 3)}


def wilson_interval(successes: int, total: int, z: float = 1.96) -> List[float]:
    """95% confidence interval for a proportion.

    Wilson rather than the normal approximation on purpose. At n=10 with 10
    successes the normal approximation gives [1.0, 1.0] — a claim of perfect
    certainty from ten clicks. Wilson gives roughly [0.72, 1.0], which is the
    honest reading.
    """
    if total <= 0:
        return [0.0, 1.0]
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [round(max(0.0, center - margin), 3), round(min(1.0, center + margin), 3)]


def _brier(scored: List[Dict[str, Any]]) -> Optional[float]:
    """Mean squared error between claimed confidence and outcome.

    Lower is better; 0.25 is what you get by claiming 0.5 about everything.
    It rewards being both accurate AND appropriately confident, which is the
    property a single accuracy percentage cannot express.
    """
    if not scored:
        return None
    return round(
        sum((row["confidence_at_verdict"] - (1.0 if row["verdict"] == "right" else 0.0)) ** 2
            for row in scored) / len(scored),
        4,
    )


async def build_calibration_report(user_id: str) -> Dict[str, Any]:
    """How often the system was right, broken down by how sure it claimed to be."""
    rows = [dict(r) for r in await fetch(
        """
        SELECT claim_type, claim_id, verdict, confidence_at_verdict, claim_label, created_at
        FROM claim_verdicts WHERE user_id = $1 ORDER BY created_at DESC
        """,
        user_id,
    )]

    # 'unsure' is a real answer, but it has no truth value, so it cannot be
    # scored. Counted separately rather than dropped, because how often people
    # cannot tell is itself worth seeing.
    scored = [r for r in rows if r["verdict"] in ("right", "wrong")]
    unsure = len(rows) - len(scored)
    right = sum(1 for r in scored if r["verdict"] == "right")

    buckets = []
    for low, high in BUCKETS:
        in_bucket = [
            r for r in scored
            if low <= r["confidence_at_verdict"] < high
            or (high == 1.0 and r["confidence_at_verdict"] == 1.0)
        ]
        hits = sum(1 for r in in_bucket if r["verdict"] == "right")
        entry = {
            "range": f"{low:.1f}-{high:.1f}",
            "claimed_confidence": round((low + high) / 2, 2),
            "samples": len(in_bucket),
            "correct": hits,
        }
        if len(in_bucket) >= MIN_BUCKET_SAMPLES:
            observed = hits / len(in_bucket)
            entry["observed_rate"] = round(observed, 3)
            entry["interval"] = wilson_interval(hits, len(in_bucket))
            gap = observed - entry["claimed_confidence"]
            entry["gap"] = round(gap, 3)
            entry["assessment"] = (
                "calibrated" if abs(gap) <= CALIBRATION_TOLERANCE
                else "overconfident" if gap < 0
                else "underconfident"
            )
        else:
            # Named explicitly so the UI cannot mistake a missing rate for 0%.
            entry["observed_rate"] = None
            entry["assessment"] = "insufficient_data"
            entry["needed"] = MIN_BUCKET_SAMPLES - len(in_bucket)
        buckets.append(entry)

    measurable = len(scored) >= MIN_TOTAL_SAMPLES
    report: Dict[str, Any] = {
        "user_id": user_id,
        "measurable": measurable,
        "summary": {
            "verdicts_total": len(rows),
            "scored": len(scored),
            "unsure": unsure,
            "correct": right,
            "min_samples_for_verdict": MIN_TOTAL_SAMPLES,
        },
        "buckets": buckets,
        "brier_score": _brier(scored),
    }

    if not measurable:
        report["accuracy"] = None
        report["verdict"] = (
            f"Not enough answers yet. {len(scored)} of {MIN_TOTAL_SAMPLES} needed "
            f"before this can say anything about how accurate the system is."
        )
        return report

    accuracy = right / len(scored)
    report["accuracy"] = round(accuracy, 3)
    report["accuracy_interval"] = wilson_interval(right, len(scored))

    judged = [b for b in buckets if b["assessment"] not in ("insufficient_data",)]
    overconfident = [b for b in judged if b["assessment"] == "overconfident"]
    report["verdict"] = _verdict_line(accuracy, judged, overconfident)
    return report


def _verdict_line(accuracy: float, judged: List[Dict], overconfident: List[Dict]) -> str:
    accuracy_text = f"You marked {accuracy:.0%} of the system's claims correct."
    if not judged:
        return (
            f"{accuracy_text} No confidence band has {MIN_BUCKET_SAMPLES} answers yet, "
            f"so whether its confidence is honest cannot be judged."
        )
    if overconfident:
        bands = ", ".join(b["range"] for b in overconfident)
        return (
            f"{accuracy_text} It is overconfident in the {bands} band"
            f"{'s' if len(overconfident) > 1 else ''} — it was right less often "
            f"than it claimed."
        )
    return (
        f"{accuracy_text} Its stated confidence matches how often it was right, "
        f"within {CALIBRATION_TOLERANCE:.0%}."
    )


async def list_open_claims(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Claims the user has not answered yet — what the ledger needs next.

    Ordered by confidence descending: a confident claim that turns out to be
    wrong is the most informative answer the user can give, and the one this
    report exists to catch.
    """
    rows = await fetch(
        """
        SELECT i.inference_id AS claim_id, 'inference' AS claim_type,
               i.label, i.description, i.confidence, i.inferred_at AS created_at
        FROM inferences i
        LEFT JOIN claim_verdicts v
               ON v.claim_id = i.inference_id AND v.user_id = i.user_id
              AND v.claim_type = 'inference'
        WHERE i.user_id = $1 AND v.id IS NULL
        ORDER BY i.confidence DESC
        LIMIT $2
        """,
        user_id, limit,
    )
    return [{
        "claim_id": r["claim_id"],
        "claim_type": r["claim_type"],
        "label": r["label"],
        "description": r["description"],
        "confidence": round(float(r["confidence"] or 0.0), 3),
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
    } for r in rows]
