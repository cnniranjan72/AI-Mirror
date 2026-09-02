"""How the model of a person moved, dimension by dimension.

The architecture stores immutable versioned snapshots and measures the distance
between them, but nothing ever showed that to the person it describes. The
number existed only in a log line.

It was also wrong until recently: mean attention span entered the norm as raw
seconds while the other sixteen dimensions were scores in [0,1], so the
distance tracked watch duration rather than identity. That is fixed, and this
module is the reason it matters - a drift chart built on the old metric would
have been a picture of one dimension pretending to be seventeen.

The vector is read through IdentityEvolutionEngine._identity_vector rather than
rebuilt here, so the chart and the recorded shift cannot drift apart. If the
definition changes, both move together.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.db.postgres import fetch, fetchrow

logger = logging.getLogger(__name__)

# Names for the seventeen dimensions, in the order _identity_vector emits them.
# Written for a reader rather than a schema: "how varied your creators are"
# rather than creator_diversity_score.
DIMENSIONS = [
    ("Overall confidence", "How sure the system is about you at all"),
    ("Model completeness", "How much of the picture it thinks it has"),
    ("Engagement rate", "How often you interact rather than scroll past"),
    ("Behaviour diversity", "How many distinct things you do"),
    ("Behaviour stability", "How steady those patterns are"),
    ("Interest diversity", "How spread out your topics are"),
    ("Creator diversity", "How many different people you watch"),
    ("Creator dependence", "How concentrated on a few of them"),
    ("Learning style", "Confidence in how you take things in"),
    ("Attention span", "How long you stay with something"),
    ("Novelty seeking", "How much you reach for the unfamiliar"),
    ("Exploration rate", "How often you leave your usual ground"),
    ("Consistency", "How similar one day is to the next"),
    ("Routine strength", "How fixed your habits are"),
    ("Learning motivation", "How much you watch to learn"),
    ("Entertainment seeking", "How much you watch to be entertained"),
    ("Skill building", "How much you watch to get better at something"),
]


class _Zero(float):
    """Zero that survives further attribute access.

    A missing value has to satisfy two callers at once: the vector arithmetic
    wants a number, and a missing *sub-profile* is followed by another lookup
    (`behavior_profile.avg_engagement_rate`). Returning a plain 0.0 handled the
    first and raised on the second, so one absent profile took the whole chart
    down rather than leaving a gap in it.
    """

    def __new__(cls):
        return super().__new__(cls, 0.0)

    def __getattr__(self, name):
        return _Zero()


class _Shim:
    """Presents a snapshot_data dict with the attribute access the vector
    function expects, so both paths use one definition of the vector."""

    def __init__(self, data: Dict[str, Any]):
        self._d = data or {}

    def __getattr__(self, name):
        value = self._d.get(name)
        if isinstance(value, dict):
            return _Shim(value)
        # A snapshot written under an older schema should still plot, with the
        # gaps showing as zeroes rather than failing the whole view.
        return _Zero() if value is None else value


def _decode(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}
    return value or {}


def _vector(obj) -> List[float]:
    from backend.identity.identity_evolution import IdentityEvolutionEngine

    try:
        return [float(v) for v in IdentityEvolutionEngine._identity_vector(obj)]
    except Exception as e:
        logger.warning("Could not build identity vector: %s", e)
        return []


def _distance(a: List[float], b: List[float]) -> Optional[float]:
    if not a or len(a) != len(b):
        return None
    return round(sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5, 4)


async def build_drift(user_id: str, limit: int = 12) -> Dict[str, Any]:
    """Every stored snapshot as a labelled vector, oldest first.

    The live identity is appended as a final "now" point when it differs from
    the newest snapshot, which is what makes the view useful for the common
    case: most accounts have exactly one snapshot, and the interesting question
    is how far they have moved since it was taken.
    """
    rows = await fetch(
        """
        SELECT snapshot_id, identity_version, snapshot_data, snapshot_timestamp
        FROM identity_snapshots WHERE user_id = $1
        ORDER BY snapshot_timestamp DESC LIMIT $2
        """,
        user_id, limit,
    )
    points: List[Dict[str, Any]] = []
    for row in reversed(rows):
        vector = _vector(_Shim(_decode(row["snapshot_data"])))
        if not vector:
            continue
        points.append({
            "label": f"v{row['identity_version']}",
            "kind": "snapshot",
            "at": row["snapshot_timestamp"].isoformat() if row["snapshot_timestamp"] else None,
            "values": [round(v, 4) for v in vector],
        })

    live = await fetchrow("SELECT * FROM identities WHERE user_id = $1", user_id)
    if live:
        current = _vector(_Shim({k: _decode(v) if isinstance(v, (str, dict)) else v
                                 for k, v in dict(live).items()}))
        if current and (not points or _distance(points[-1]["values"], current)):
            points.append({
                "label": "now",
                "kind": "live",
                "at": None,
                "values": [round(v, 4) for v in current],
            })

    # Distance between consecutive points, using the same norm as Eq. 2.
    steps = []
    for earlier, later in zip(points, points[1:]):
        steps.append({
            "from": earlier["label"],
            "to": later["label"],
            "shift": _distance(earlier["values"], later["values"]),
        })

    biggest = []
    if len(points) >= 2:
        first, last = points[0]["values"], points[-1]["values"]
        moves = sorted(
            (
                {
                    "dimension": DIMENSIONS[i][0],
                    "meaning": DIMENSIONS[i][1],
                    "from": first[i],
                    "to": last[i],
                    "delta": round(last[i] - first[i], 4),
                }
                for i in range(min(len(first), len(last), len(DIMENSIONS)))
            ),
            key=lambda m: -abs(m["delta"]),
        )
        biggest = [m for m in moves if abs(m["delta"]) >= 0.01][:5]

    return {
        "user_id": user_id,
        "dimensions": [{"name": n, "meaning": m} for n, m in DIMENSIONS],
        "points": points,
        "steps": steps,
        "biggest_moves": biggest,
        # sqrt(17): the largest distance possible once every dimension is
        # scaled to [0,1]. Given so the client can size the axis honestly
        # instead of normalising against whatever it happens to have seen.
        "max_possible_shift": round(len(DIMENSIONS) ** 0.5, 4),
        "measurable": len(points) >= 2,
        "note": (
            "Not enough history yet. A second point appears once the system "
            "records a new snapshot, which happens when the model of you moves "
            "far enough to warrant one."
            if len(points) < 2 else
            "Each axis is one of the seventeen measures the system keeps about "
            "you, scaled to a common range. Distance is the same figure the "
            "snapshot threshold is judged against."
        ),
    }
