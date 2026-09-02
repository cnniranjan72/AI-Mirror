"""What state a behaviour is actually in, as of now.

The lifecycle is one of the architecture's stated contributions: six states,
EMERGING through ARCHIVED, tracking a behaviour from first appearance to
abandonment. Measured against the deployed instance, every one of 226 behaviour
objects was in one of two states - 217 growing, 9 emerging. Stable, declining,
dormant and archived had never once occurred.

Two causes, both structural.

The state was a function of the ingest batch that last contained the topic.
`growth_rate > 0.5 -> GROWING` and so on, evaluated at consolidation time. A
topic the user stopped watching is by definition never in a batch again, so the
only code path that could downgrade it cannot run. Ninety-six objects unseen
for over thirty days were still labelled growing; the oldest had last been seen
600 days earlier and was still, officially, growing.

And `growth_rate` is not a growth rate. It is `occurrence_count / days_since_first`
- occurrences per day, necessarily positive, averaging 3.08 and reaching 60 on
real data. So `> 0.5` ("more than one event every other day") caught almost
everything, and DECLINING, which tested `growth_rate < 0`, could never fire at
all.

The fix is to ask the question at the time of asking. State is derived here from
how long the behaviour has been silent, measured against how often it used to
appear, plus a trajectory computed from the events themselves rather than from a
misnamed rate.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

# Silence is judged against the behaviour's own rhythm: a topic that recurred
# three times a day and has been quiet for a month is gone, while one that
# surfaces every couple of months is not. Three times its typical gap.
#
# On the deployed corpus this ratio makes no measurable difference - 2, 3 and 5
# all classify identically - because real gaps are strongly bimodal: a
# behaviour is either current or long abandoned, with little in between.
DORMANCY_RATIO = 3.0

# The floor that stops a burst of activity from looking abandoned two days
# later. A behaviour seen ten times yesterday has a typical gap of hours, and
# without this any ordinary pause would trip the ratio.
#
# This is the parameter that actually matters. Moving it from 14 to 30 days
# reclassifies 42% of the deployed corpus from dormant to stable. Fourteen is
# the more accurate reading there: the affected behaviours recurred several
# times a day and have been silent for twenty-five, which is abandonment, not a
# quiet fortnight.
DORMANT_AFTER_DAYS = 14

# Long enough that the behaviour is history rather than a lapse.
ARCHIVED_AFTER_DAYS = 180

# Below this there is no rhythm to be absent from.
MIN_OCCURRENCES_FOR_RHYTHM = 3

# A behaviour younger than this has not had time to be anything but new.
EMERGING_MAX_AGE_DAYS = 14

# Share of a behaviour's occurrences falling in the recent half of its life.
# At 0.5 activity is even; below this it is genuinely tailing off. Not 0.5
# itself, because ordinary variation would flip the label back and forth.
DECLINING_RECENT_SHARE = 0.35

# The mirror image, for a behaviour whose activity is concentrated recently.
GROWING_RECENT_SHARE = 0.65

STATES = ("emerging", "growing", "stable", "declining", "dormant", "archived")


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


def _days_between(later: datetime, earlier: Optional[datetime]) -> Optional[float]:
    if earlier is None:
        return None
    return (later - earlier).total_seconds() / 86400.0


def recent_share(event_times, now: Optional[datetime] = None) -> Optional[float]:
    """Share of a behaviour's occurrences in the recent half of its lifespan.

    This is the trajectory the misnamed `growth_rate` never provided. Splitting
    at the midpoint between first and last occurrence rather than at a fixed
    date keeps it meaningful for behaviours of very different ages: a topic
    spanning two years and one spanning two weeks are each compared against
    their own history.

    Returns None when there is too little to divide.
    """
    stamps = sorted(t for t in (_as_datetime(e) for e in (event_times or [])) if t)
    if len(stamps) < 4:
        return None

    first, last = stamps[0], stamps[-1]
    span = (last - first).total_seconds()
    if span <= 0:
        return None

    midpoint = first.timestamp() + span / 2.0
    recent = sum(1 for t in stamps if t.timestamp() >= midpoint)
    return recent / len(stamps)


def evaluate_lifecycle(
    temporal: Dict[str, Any],
    trend: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Tuple[str, Dict[str, Any]]:
    """The behaviour's state as of `now`, and why.

    The reason travels with the state because every one of these labels is a
    claim about someone's life - "you have moved on from this" is not something
    to assert without being able to say on what basis.
    """
    now = now or datetime.now(timezone.utc)
    temporal = temporal or {}
    trend = trend or {}

    last_seen = _as_datetime(temporal.get("last_seen"))
    first_seen = _as_datetime(temporal.get("first_seen"))
    gap = _days_between(now, last_seen)
    age = _days_between(now, first_seen)
    occurrences = int(temporal.get("occurrence_count") or 0)
    per_day = float(temporal.get("daily_frequency") or 0.0)
    share = trend.get("recent_share")

    reason: Dict[str, Any] = {
        "days_since_last_seen": round(gap, 1) if gap is not None else None,
        "age_days": round(age, 1) if age is not None else None,
        "occurrences": occurrences,
        "recent_share": round(share, 3) if isinstance(share, (int, float)) else None,
    }

    if gap is None:
        reason["basis"] = "no last-seen timestamp, so no judgement is made"
        return "emerging", reason

    if gap >= ARCHIVED_AFTER_DAYS:
        reason["basis"] = (
            f"not seen in {gap:.0f} days, beyond the {ARCHIVED_AFTER_DAYS}-day "
            f"point where a behaviour is treated as history"
        )
        return "archived", reason

    # Silence against the behaviour's own rhythm, floored so an ordinary pause
    # in a frequent habit is not mistaken for abandonment.
    if occurrences >= MIN_OCCURRENCES_FOR_RHYTHM and per_day > 0:
        typical_gap = 1.0 / per_day
        threshold = max(DORMANT_AFTER_DAYS, DORMANCY_RATIO * typical_gap)
        if gap >= threshold:
            reason["typical_gap_days"] = round(typical_gap, 2)
            reason["basis"] = (
                f"silent {gap:.0f} days against a usual gap of "
                f"{typical_gap:.1f}, past the {threshold:.0f}-day line"
            )
            return "dormant", reason
    elif gap >= DORMANT_AFTER_DAYS:
        reason["basis"] = (
            f"only {occurrences} occurrences and silent {gap:.0f} days, too "
            f"little to establish a rhythm and too long to call current"
        )
        return "dormant", reason

    # Still current. What is it doing?
    if isinstance(share, (int, float)):
        if share <= DECLINING_RECENT_SHARE:
            reason["basis"] = (
                f"only {share:.0%} of its activity falls in the recent half of "
                f"its life, so it is tailing off"
            )
            return "declining", reason
        if share >= GROWING_RECENT_SHARE:
            reason["basis"] = (
                f"{share:.0%} of its activity falls in the recent half of its "
                f"life, so it is building"
            )
            return "growing", reason

    if age is not None and age <= EMERGING_MAX_AGE_DAYS:
        reason["basis"] = f"first seen {age:.0f} days ago, still new"
        return "emerging", reason

    reason["basis"] = (
        f"seen within {gap:.0f} days with activity spread evenly across "
        f"{age:.0f} days" if age is not None else "current and steady"
    )
    return "stable", reason
