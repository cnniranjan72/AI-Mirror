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

import hashlib
import logging
import math
from typing import Any, Dict, Iterable, List, Optional, Set

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

# Inferences only, deliberately.
#
# "reflection" was listed here first, on the assumption that a reflection is a
# claim about the user like an inference is. The stored rows say otherwise.
# Every summary in production reads:
#
#     "Reflection covering 7 behavior objects across 2 evidence items with
#      41 total events. Key topics: ..."
#
# That is a statistic about a pipeline run, not an assertion about a person.
# There is no answer to "is this right or wrong about you", so asking would
# collect noise and score the system on it.
#
# It would also break claim_key, which fingerprints content: those counts
# change on every ingest, so each run would mint a brand new "claim" and the
# open list would fill with the same reflection over and over. reflection_type
# cannot rescue it either — every row in production is 'periodic'.
#
# The claim_verdicts CHECK constraint still permits 'reflection' so old rows
# remain valid. Re-enabling means giving reflections a summary that actually
# asserts something about the person, and a stable key that is not a row count.
VALID_CLAIM_TYPES = ("inference",)

_SOURCE = {
    "inference": ("inferences", "inference_id", "label"),
}


def claim_key(rule_name: Optional[str], label: Optional[str]) -> str:
    """A stable identity for a claim: its rule plus what it asserts.

    inference_id cannot serve, because it is minted as
    inference_{rule}_{context_id}_{utcnow().timestamp()} and context_id is
    itself ctx_{timestamp}. Every ingest deletes and regenerates the whole
    inference set, so the id of a given claim changes on every run — and a
    ledger keyed on it asked the user the same question forever.

    rule_name alone would be too coarse: EngagementDepthRule emits both
    "Engagement style is deep, attentive" and "... quick, scanning", and
    denying one must not silently deny the other.

    MUST stay identical to the md5 expression in migration_v19.sql. md5 is a
    fingerprint here, not a security primitive.
    """
    basis = f"{(rule_name or '').strip().lower()}|{(label or '').strip().lower()}"
    return hashlib.md5(basis.encode("utf-8")).hexdigest()


async def contested_claim_keys(user_id: str) -> Set[str]:
    """Claims this user has explicitly marked wrong.

    Only 'wrong' counts. 'unsure' is a real answer but it is not a denial, and
    treating hesitation as rejection would let the system quietly discard
    anything the user merely found hard to judge.
    """
    rows = await fetch(
        """
        SELECT DISTINCT claim_key FROM claim_verdicts
        WHERE user_id = $1 AND verdict = 'wrong' AND claim_key IS NOT NULL
        """,
        user_id,
    )
    return {r["claim_key"] for r in rows}


async def annotate_contested(user_id: str, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tag rows the user has denied, without dropping them.

    Used where the point is to SHOW the reasoning (the Report, /explain) rather
    than to assert it. Hiding a denied claim there would make the correction
    invisible and irreversible; the user should see that their objection stuck.
    """
    contested = await contested_claim_keys(user_id)
    out = []
    for row in rows:
        row = dict(row)
        key = row.get("claim_key") or claim_key(row.get("rule_name"), row.get("label"))
        # Always set, even when nothing is contested. Skipping the field for
        # the common case made its absence ambiguous — a caller could not tell
        # "not contested" from "this build does not report it" — and the shape
        # of a response should not depend on the data in it.
        row["contested"] = key in contested
        out.append(row)
    return out


# A SQL predicate for "the user has not denied this claim".
#
# Applied where the system ASSERTS something to the user — chat answers, the
# character's speech, wellbeing nudges. Not applied where the point is to SHOW
# the reasoning (the Report, /explain); those annotate instead, so a correction
# is visible and reversible rather than making the claim silently vanish.
#
# Written against the `inferences` alias the caller uses, hence the format slot.
# It matches on claim_key, so a denial survives the pipeline regenerating the
# whole inference set with new ids.
NOT_CONTESTED_SQL = """
    AND NOT EXISTS (
        SELECT 1 FROM claim_verdicts cv
         WHERE cv.user_id = {alias}.user_id
           AND cv.claim_type = 'inference'
           AND cv.verdict = 'wrong'
           AND cv.claim_key = {alias}.claim_key
    )
"""


def not_contested(alias: str = "inferences") -> str:
    """The predicate above, bound to a table alias."""
    return NOT_CONTESTED_SQL.format(alias=alias)


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
        f"SELECT confidence, {label_column} AS label, rule_name AS rule FROM {table} "
        f"WHERE {id_column} = $1 AND user_id = $2",
        claim_id, user_id,
    )
    if not row:
        # Scoped to user_id above, so this is also the authorization check:
        # you cannot rate a claim the system made about somebody else.
        return {"recorded": False, "reason": "claim_not_found"}

    confidence = float(row["confidence"] or 0.0)
    key = claim_key(row["rule"], row["label"])
    await execute(
        """
        INSERT INTO claim_verdicts
            (user_id, claim_type, claim_id, verdict, confidence_at_verdict,
             claim_label, claim_key)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        -- Conflict on the LOGICAL claim, not on claim_id. claim_id is an
        -- inference_id and the pipeline regenerates those every ingest, so
        -- targeting it meant changing your mind after a re-run inserted a
        -- SECOND verdict instead of updating the first — leaving a stale
        -- "wrong" row that kept suppressing the claim, and double-counting
        -- it in the score. See migration_v21.
        ON CONFLICT (user_id, claim_type, claim_key) WHERE claim_key IS NOT NULL
        DO UPDATE
            SET verdict = EXCLUDED.verdict,
                -- confidence_at_verdict is deliberately NOT refreshed: the
                -- user is changing their answer, not the claim being scored.
                claim_label = EXCLUDED.claim_label,
                -- The row that was actually on screen this time.
                claim_id = EXCLUDED.claim_id,
                updated_at = NOW()
        """,
        user_id, claim_type, claim_id, verdict, confidence,
        (row["label"] or "")[:500], key,
    )
    return {"recorded": True, "claim_type": claim_type, "claim_id": claim_id,
            "verdict": verdict, "confidence_at_verdict": round(confidence, 3),
            "claim_key": key}


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


async def list_answered_claims(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Claims the user has already answered, so an answer can be changed.

    Without this the Report tells a user their correction can be taken back
    while the Ledger only ever lists UNANSWERED claims — the denied claim
    disappears from the one screen that could reverse it.

    live_claim_id is resolved through claim_key rather than reusing the
    claim_id stored on the verdict. That stored id is the inference_id as it
    was when they answered, and the pipeline regenerates the whole inference
    set on every ingest, so it is usually stale and record_verdict would
    404 on it.

    When no live row matches, the system is no longer making that claim at
    all: live_claim_id is None and there is nothing to restore. Still listed,
    because the answer is part of the user's record and still scores.

    The live lookup goes to `inferences` because that is the only contestable
    claim type (see VALID_CLAIM_TYPES). A historical 'reflection' verdict —
    recorded while that type was briefly accepted — therefore resolves to no
    live claim, which is the correct answer for it anyway.
    """
    rows = await fetch(
        """
        SELECT v.claim_type, v.claim_id, v.verdict, v.claim_label, v.claim_key,
               v.confidence_at_verdict, v.updated_at,
               (SELECT i.inference_id FROM inferences i
                 WHERE i.user_id = v.user_id AND i.claim_key = v.claim_key
                   AND v.claim_type = 'inference'
                 ORDER BY i.inferred_at DESC LIMIT 1) AS live_claim_id
        FROM claim_verdicts v
        WHERE v.user_id = $1
        ORDER BY v.updated_at DESC
        LIMIT $2
        """,
        user_id, limit,
    )
    return [{
        "claim_type": r["claim_type"],
        "claim_id": r["claim_id"],
        # What to POST to change this answer. None means the system has stopped
        # making the claim, so there is nothing left to change.
        "live_claim_id": r["live_claim_id"],
        "still_claimed": r["live_claim_id"] is not None,
        "verdict": r["verdict"],
        "label": r["claim_label"],
        "confidence_at_verdict": round(float(r["confidence_at_verdict"] or 0.0), 3),
        "answered_at": r["updated_at"].isoformat() if r["updated_at"] else None,
    } for r in rows]


async def list_open_claims(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Claims the user has not answered yet — what the ledger needs next.

    Ordered by confidence descending: a confident claim that turns out to be
    wrong is the most informative answer the user can give, and the one this
    report exists to catch.
    """
    rows = await fetch(
        """
        -- DISTINCT ON collapses the duplicate rows regeneration leaves behind
        -- so one logical claim is asked once, but Postgres requires its
        -- ORDER BY to lead with the DISTINCT ON expression. Ordering by
        -- confidence therefore has to happen OUTSIDE, or the list comes back
        -- sorted by an md5 hash and "most confident first" is a lie.
        SELECT * FROM (
            SELECT DISTINCT ON (i.claim_key)
                   i.inference_id AS claim_id, 'inference' AS claim_type,
                   i.label, i.description, i.confidence,
                   i.inferred_at AS created_at, i.claim_key
            FROM inferences i
            LEFT JOIN claim_verdicts v
                   ON v.user_id = i.user_id
                  AND v.claim_type = 'inference'
                  -- The stable key, NOT inference_id: ids are regenerated on
                  -- every ingest, so joining on them re-asks answered
                  -- questions forever.
                  AND v.claim_key = i.claim_key
            WHERE i.user_id = $1 AND i.claim_key IS NOT NULL AND v.id IS NULL
            ORDER BY i.claim_key, i.confidence DESC
        ) unanswered
        ORDER BY confidence DESC
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
