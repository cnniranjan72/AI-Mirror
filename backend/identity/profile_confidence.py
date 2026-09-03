"""How much each sub-profile's own evidence actually supports it.

The architecture describes nine sub-profiles "each with an independently
computed confidence, aggregated by evidence volume and recency". Measured
against the deployed instance, seven of the nine carried no confidence field at
all - behaviour, interest graph, creator graph, attention, exploration,
consistency and habit had nowhere to put one. The two that did were binary
constants:

    confidence = 0.7 if learning_inferences else 0.5     # LearningStyle
    confidence = 0.7 if inferences else 0.5              # MotivationSignals

which is a flag for "some inference exists", not a measure of anything, and
certainly not volume or recency. Across twelve accounts those two fields took
three values between them.

The point of a per-profile figure is that the profiles do not rest on the same
evidence. An account can have hundreds of topic observations and almost no
timing data, in which case the interest graph is well supported and the habit
profile is a guess. A single identity-wide number cannot say that, and nine
copies of it say it nine times over.

Volume and recency are combined rather than averaged. A profile built on
plentiful but year-old observations is not half-confident; it is describing
somebody who may no longer exist. The product falls away in both directions,
and the components are reported alongside so the number can be argued with.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Observations at which volume stops adding confidence. Matches the saturation
# already used for identity-wide confidence (len(behaviors) / 20.0) so the
# per-profile figures and the overall one are on the same scale.
VOLUME_SATURATION = 20.0

# Recency half-life. A profile whose newest supporting observation is this old
# retains half the confidence its volume alone would give it. Thirty days is
# the same window the recency score elsewhere in the pipeline uses.
RECENCY_HALF_LIFE_DAYS = 30.0

# Never claim more than this from volume and recency alone: these say how much
# was seen and how lately, not whether the reading was right. The Accuracy
# Ledger is where correctness is scored.
CEILING = 0.95


def _as_datetime(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
    else:
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def newest(timestamps: List[Any]) -> Optional[datetime]:
    parsed = [t for t in (_as_datetime(v) for v in (timestamps or [])) if t]
    return max(parsed) if parsed else None


def profile_confidence(
    observations: int,
    last_seen: Any = None,
    saturation: float = VOLUME_SATURATION,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Confidence for one sub-profile, with the parts that produced it.

    `observations` is what this profile in particular rests on - the behaviours
    carrying watch statistics for attention, the ones carrying creators for the
    creator graph - not the account's total. That is the whole point: the nine
    figures differ because the nine inputs differ.

    Returns the value and its basis together, because a confidence shown
    without what produced it cannot be disputed.
    """
    now = now or datetime.now(timezone.utc)

    if observations <= 0:
        return {
            "confidence": 0.0,
            "observations": 0,
            "volume": 0.0,
            "recency": 0.0,
            "basis": "nothing supports this profile yet",
        }

    volume = min(1.0, observations / saturation) if saturation > 0 else 0.0

    seen = _as_datetime(last_seen)
    if seen is None:
        # No timestamp to judge by. Volume alone, discounted, rather than
        # assuming the data is current - which would be the most flattering
        # reading available.
        recency = 0.5
        recency_note = "no timestamp on the supporting data, so recency is assumed weak"
        age_days = None
    else:
        age_days = max(0.0, (now - seen).total_seconds() / 86400.0)
        recency = 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)
        recency_note = "newest supporting observation is %.0f days old" % age_days

    confidence = min(CEILING, volume * recency)

    return {
        "confidence": round(confidence, 3),
        "observations": observations,
        "volume": round(volume, 3),
        "recency": round(recency, 3),
        "age_days": round(age_days, 1) if age_days is not None else None,
        "basis": (
            "%d supporting observation%s (%.0f%% of the %d needed for full "
            "volume); %s"
            % (observations, "" if observations == 1 else "s",
               100 * volume, int(saturation), recency_note)
        ),
    }
