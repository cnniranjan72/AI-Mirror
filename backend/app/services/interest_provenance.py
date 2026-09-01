"""Interest Provenance — did you choose this, or were you fed it?

The Algorithmic Mirror asks what a platform thinks you are. This asks the
harder question: how much of that did the platform CREATE?

For every topic the twin tracks, two quantities are separable in the data:

    exposure   — how often the content reached you (views)
    seeking    — evidence you went looking for it (searches, likes, saves,
                 shares, comments)

A topic with heavy exposure and no seeking is not an interest you have. It is
one that was installed. A topic you searched for repeatedly is yours.

WHAT THIS DELIBERATELY DOES NOT USE
-----------------------------------
`events.following` looks like a perfect intent signal and is worthless as one:
EventItem.following defaults to True, so 99.2% of rows in production carry it.
It records a default, not an observation. Using it would make almost every
topic look self-chosen and the feature would be a flattering lie.

Of the honest flags, liked/saved/shared/commented appear on ~1% of real rows,
which is why search history (see migration_v17) is the load-bearing input. An
account with no imported searches genuinely cannot be scored, and this module
says so rather than reporting everything as "fed" — the difference between
"you didn't choose this" and "we have no way to tell" is the whole ballgame.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

from app.db.postgres import fetch

logger = logging.getLogger(__name__)

# Below this many deliberate signals across the whole account, agency is not
# measurable: every topic would score zero from absence of data rather than
# absence of intent.
MIN_DELIBERATE_SIGNALS = 5

# A topic needs this much exposure before "you never sought it" means anything.
MIN_EXPOSURE_TO_JUDGE = 5

# Agency bands. A topic below FED_CEILING with real exposure is the finding.
FED_CEILING = 0.10
MIXED_CEILING = 0.40

_STOPWORDS = frozenset("""
and or the a an of for with in on to from how what why best top new video
videos watch full free online review tutorial guide vs your you my me
""".split())


def _tokens(text: str) -> Set[str]:
    return {
        t for t in re.split(r"[^a-z0-9]+", (text or "").lower())
        if len(t) >= 3 and t not in _STOPWORDS
    }


async def _load_topics(user_id: str) -> List[Dict[str, Any]]:
    rows = await fetch(
        """
        SELECT topic, keywords, metadata,
               COALESCE((temporal_statistics->>'occurrence_count')::float, 0) AS exposure
        FROM behavior_objects
        WHERE user_id = $1
        """,
        user_id,
    )
    import json
    out = []
    for row in rows:
        record = dict(row)
        metadata = record.get("metadata")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        # Creator objects are affinities, not subjects — scoring "Content by X"
        # for agency would be a category error, same as in the interest graph.
        if isinstance(metadata, dict) and metadata.get("cluster_type") == "creator":
            continue
        if (record.get("topic") or "").startswith("Content by "):
            continue

        keywords = record.get("keywords")
        if isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except Exception:
                keywords = []
        record["keywords"] = keywords if isinstance(keywords, list) else []
        out.append(record)
    return out


async def _load_searches(user_id: str) -> List[Dict[str, Any]]:
    rows = await fetch(
        "SELECT platform, query, raw_query, searched_at FROM search_signals WHERE user_id = $1",
        user_id,
    )
    return [dict(r) for r in rows]


async def _load_engagement(user_id: str) -> List[Dict[str, Any]]:
    """Events carrying a deliberate act. `following` is excluded — see the
    module docstring; it is a default, not a signal."""
    rows = await fetch(
        """
        SELECT caption, hashtags, username,
               liked, saved, shared, commented
        FROM events
        WHERE user_id = $1
          AND (liked OR saved OR shared OR commented)
        """,
        user_id,
    )
    import json
    out = []
    for row in rows:
        record = dict(row)
        tags = record.get("hashtags")
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = []
        record["hashtags"] = tags if isinstance(tags, list) else []
        out.append(record)
    return out


def _topic_vocabulary(topic: Dict[str, Any]) -> Set[str]:
    vocab = _tokens(topic.get("topic", ""))
    for keyword in topic.get("keywords") or []:
        vocab |= _tokens(str(keyword))
    return vocab


def _classify(agency: Optional[float]) -> str:
    if agency is None:
        return "unknown"
    if agency <= FED_CEILING:
        return "fed"
    if agency <= MIXED_CEILING:
        return "mixed"
    return "chosen"


async def build_provenance_report(user_id: str) -> Dict[str, Any]:
    topics = await _load_topics(user_id)
    searches = await _load_searches(user_id)
    engagements = await _load_engagement(user_id)

    total_deliberate = len(searches) + len(engagements)
    measurable = total_deliberate >= MIN_DELIBERATE_SIGNALS

    # Pre-tokenise once; this is O(topics x signals) and both grow with import size.
    search_tokens = [(s, _tokens(s["query"])) for s in searches]
    engagement_tokens = [
        (e, _tokens(" ".join([e.get("caption") or ""] + [str(t) for t in e.get("hashtags") or []])))
        for e in engagements
    ]

    scored = []
    for topic in topics:
        vocab = _topic_vocabulary(topic)
        exposure = int(topic.get("exposure") or 0)

        matched_searches = [s["raw_query"] for s, toks in search_tokens if vocab & toks]
        engaged_count = sum(1 for _e, toks in engagement_tokens if vocab & toks)
        deliberate = len(matched_searches) + engaged_count

        if not measurable or exposure < MIN_EXPOSURE_TO_JUDGE:
            # Not "you didn't choose it" — we cannot tell.
            agency = None
        else:
            # Share of exposure accompanied by a deliberate act, capped at 1.
            # Searching more often than you watched still means "chosen", not
            # "chosen 300%".
            agency = min(1.0, deliberate / exposure)

        scored.append({
            "topic": topic.get("topic"),
            "exposure": exposure,
            "searches": len(matched_searches),
            "example_searches": matched_searches[:3],
            "engagements": engaged_count,
            "deliberate_signals": deliberate,
            "agency": agency,
            "verdict": _classify(agency),
        })

    # Fed topics first and by exposure: the most-watched thing you never once
    # sought is the finding worth leading with.
    scored.sort(key=lambda t: (
        {"fed": 0, "mixed": 1, "chosen": 2, "unknown": 3}[t["verdict"]],
        -t["exposure"],
    ))

    fed = [t for t in scored if t["verdict"] == "fed"]
    chosen = [t for t in scored if t["verdict"] == "chosen"]
    judged = [t for t in scored if t["agency"] is not None]

    fed_exposure = sum(t["exposure"] for t in fed)
    judged_exposure = sum(t["exposure"] for t in judged)

    return {
        "user_id": user_id,
        "measurable": measurable,
        "topics": scored,
        "summary": {
            "topics_total": len(scored),
            "topics_judged": len(judged),
            "fed": len(fed),
            "mixed": sum(1 for t in scored if t["verdict"] == "mixed"),
            "chosen": len(chosen),
            "unknown": sum(1 for t in scored if t["verdict"] == "unknown"),
            "search_signals": len(searches),
            "engagement_signals": len(engagements),
            # Share of judged watching spent on topics with no evidence of
            # seeking. The headline number, and the one worth being careful with.
            "fed_share_of_attention": (fed_exposure / judged_exposure) if judged_exposure else None,
        },
        "caveats": [
            "Seeking is measured from searches and explicit engagement "
            "(likes, saves, shares, comments). Discovering something through a "
            "friend, a link, or another app leaves no trace here and will look "
            "like it was fed to you.",
            "`following` is deliberately ignored: the field defaults to true on "
            "ingest, so it records a default rather than a choice.",
            "Matching is lexical. A search phrased differently from the topic's "
            "own vocabulary will not be credited to it; every topic lists the "
            "searches it did match.",
        ] + ([] if measurable else [
            f"Fewer than {MIN_DELIBERATE_SIGNALS} deliberate signals were found "
            "for this account, so agency cannot be measured at all. Import a "
            "Google Takeout export that includes search history — without it, "
            "there is no evidence of seeking to weigh against exposure."
        ]),
    }
