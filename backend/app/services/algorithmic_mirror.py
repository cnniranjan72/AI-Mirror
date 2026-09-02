"""The Algorithmic Mirror — test a platform's profile of a person against
that person's own behaviour.

Everyone can already SEE their ad-interest list; both Meta and Google publish
it. What nobody can do is check whether it is TRUE. Falsifying a claim about a
person requires an independent, evidence-based model of that person, and that
is precisely what the cognitive pipeline produces: deterministic inference,
named rules, and provenance for every claim it makes.

So this module compares two profiles built from completely different sources:

  the platform's claims  — imported verbatim from the user's own data export
  the twin's evidence    — derived only from observed behaviour

and sorts each claim into one of four verdicts. The fourth one is the reason
this is honest rather than merely provocative.

Regulatory context (why this is a capability rather than a gimmick): EU DSA
Art. 26/39 require platforms to disclose ad-targeting parameters, and GDPR
Art. 15(1)(h) gives a right to meaningful information about automated
decisions. Both create a right to *see* the profile. Neither provides any way
to test it.

No LLM is involved anywhere in this file. Every verdict is a deterministic set
operation over cited evidence — which is what makes the output auditable, and
therefore usable as evidence itself.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

from app.db.postgres import fetch
from app.services import semantic_match

logger = logging.getLogger(__name__)

# Below this data coverage the twin has not earned the right to call a
# platform wrong. A profile built from a handful of events would mark almost
# every claim "unsupported" purely because it has seen almost nothing — which
# would be exactly the overconfident-from-thin-data failure the coverage
# disclosure exists to prevent. Verdicts are still computed and shown, but the
# report marks itself provisional and the UI leads with that.
MIN_COVERAGE_FOR_VERDICT = 0.35

# Corroboration requires at least this many observations behind the matched
# topic. One event is a coincidence, not support.
MIN_OBSERVATIONS_FOR_SUPPORT = 3

# Claims that are not testable from content behaviour, whatever the data
# volume. These are demographic, life-event or purchase-intent inferences —
# the platform may well be right, but nothing in a watch history can confirm
# or refute them, and scoring them would manufacture a verdict out of silence.
# Deliberately an explicit, inspectable list rather than a heuristic: a wrong
# guess here becomes a wrong accusation.
_NON_TESTABLE_PATTERNS = (
    # Trailing `s?` throughout: platforms label these both ways ("New parent"
    # and "New parents"), and a pattern that only matched the singular would
    # let the plural through to be scored as a testable interest.
    r"\baway from (family|hometown)\b",
    r"\brecently (moved|relocated|travel(l)?ed)\b",
    r"\bnew (parent|mover|job|relationship)s?\b",
    r"\bfrequent (traveler|traveller|flyer|shopper)s?\b",
    r"\b(anniversary|birthday|newlywed|engaged)\b",
    r"\blives? (abroad|near)\b",
    r"\b(household|income|net worth|homeowner|renter)\b",
    r"\b(likely to|in market for|purchase intent|shopping for)\b",
    r"\b(expats?|generation [xyz]|millennials?|boomers?)\b",
    r"\b(device|operating system|browser|connection type|carrier)\b",
)

_NON_TESTABLE = [re.compile(p, re.I) for p in _NON_TESTABLE_PATTERNS]

# Words that carry no discriminating power when matching a claim to a topic.
# Without this, "Technology (computers)" would match anything containing
# "and"/"other".
_MATCH_STOPWORDS = frozenset("""
and or the a an of for with in on to from other others general related misc
miscellaneous products product services service topics topic interests
interest content media online people fans lovers enthusiasts
""".split())


def _tokens(text: str) -> Set[str]:
    """Word tokens usable for matching, lowercased, stopwords dropped."""
    return {
        t for t in re.split(r"[^a-z0-9]+", (text or "").lower())
        if len(t) >= 3 and t not in _MATCH_STOPWORDS
    }


def _is_non_testable(label: str) -> bool:
    return any(pattern.search(label) for pattern in _NON_TESTABLE)


async def _load_claims(user_id: str) -> List[Dict[str, Any]]:
    rows = await fetch(
        "SELECT platform, claim_type, label, raw_label, source_file, imported_at "
        "FROM platform_profile_claims WHERE user_id = $1 ORDER BY platform, label",
        user_id,
    )
    return [dict(r) for r in rows]


async def _load_behaviour(user_id: str) -> List[Dict[str, Any]]:
    """The twin's side: topic behaviour objects with their observation counts.

    Creator objects are excluded — a creator is an affinity, not a subject, and
    matching "Content by natgeo" against an ad interest would be the same
    category error the interest graph already had to be fixed for.
    """
    # occurrence_count is not a column — it lives inside the temporal_statistics
    # JSONB blob, so it is extracted here rather than in Python to keep the
    # count and the ordering in one place.
    rows = await fetch(
        """
        SELECT topic, keywords, importance_score, confidence_score,
               evidence_references, metadata,
               COALESCE((temporal_statistics->>'occurrence_count')::float, 0) AS occurrence_count
        FROM behavior_objects
        WHERE user_id = $1
        """,
        user_id,
    )

    out = []
    for row in rows:
        record = dict(row)
        metadata = record.get("metadata")
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        if isinstance(metadata, dict) and metadata.get("cluster_type") == "creator":
            continue
        topic = record.get("topic") or ""
        if topic.startswith("Content by "):
            continue

        keywords = record.get("keywords")
        if isinstance(keywords, str):
            import json
            try:
                keywords = json.loads(keywords)
            except Exception:
                keywords = []
        record["keywords"] = keywords if isinstance(keywords, list) else []
        out.append(record)
    return out


def _match_claim(claim_label: str, behaviours: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the behaviour that best supports a claim, or None.

    Token overlap rather than string equality, because the two vocabularies are
    independent: the platform says "Robotics", the twin derived "robotics" from
    a hashtag, and a stricter comparison would report a mismatch that is really
    just punctuation. Overlap is required on a MEANINGFUL token (stopwords
    stripped), so "Technology and computers" cannot match on "and".
    """
    claim_tokens = _tokens(claim_label)
    if not claim_tokens:
        return None

    best = None
    best_score = 0
    for behaviour in behaviours:
        candidate_tokens = _tokens(behaviour.get("topic", ""))
        for keyword in behaviour.get("keywords") or []:
            candidate_tokens |= _tokens(str(keyword))

        overlap = claim_tokens & candidate_tokens
        if not overlap:
            continue
        # Prefer the most-observed matching behaviour: the strongest available
        # support for the claim, not merely the first found.
        score = len(overlap) * 1000 + int(behaviour.get("occurrence_count") or 0)
        if score > best_score:
            best_score = score
            best = {"behaviour": behaviour, "matched_on": sorted(overlap)}
    return best


async def estimate_coverage(user_id: str) -> Optional[float]:
    """Data coverage on the same five signals the Report page discloses.

    Lives here rather than in the API layer because it gates whether this
    module is entitled to render a verdict at all, and every caller needs the
    same gate. Returns None if it cannot be computed, which callers must treat
    as "not reliable" rather than "fine".
    """
    try:
        from app.db.postgres import fetchrow

        row = await fetchrow(
            """
            SELECT
              (SELECT COUNT(*) FROM events             WHERE user_id = $1) AS events,
              (SELECT COUNT(*) FROM behavior_objects   WHERE user_id = $1) AS topics,
              (SELECT COUNT(*) FROM evidence           WHERE user_id = $1) AS evidence,
              (SELECT COUNT(*) FROM inferences         WHERE user_id = $1) AS inferences,
              (SELECT COUNT(*) FROM identity_snapshots WHERE user_id = $1) AS snapshots
            """,
            user_id,
        )
        if not row:
            return None
        targets = {"events": 200, "topics": 12, "evidence": 40, "inferences": 8, "snapshots": 5}
        ratios = [min(1.0, (row[k] or 0) / t) for k, t in targets.items()]
        return sum(ratios) / len(ratios)
    except Exception as e:
        logger.warning("Could not estimate coverage for %s: %s", user_id, e)
        return None


async def build_mirror_report(user_id: str, coverage: Optional[float] = None) -> Dict[str, Any]:
    """Compare the platform's claims against the twin's evidence.

    Verdicts:
      corroborated  — the claim is supported by observed behaviour, with counts
      unsupported   — nothing in the imported history supports it
      not_comparable— the claim is not testable from content behaviour at all
      missed        — a well-evidenced interest the platform does not claim
    """
    # `coverage=None` previously meant "assume this is fine", so any caller that
    # forgot to pass it got verdict_reliable=True for free — chat would then
    # state findings the Report deliberately withholds. None now means
    # "measure it", and a coverage that cannot be measured is not sufficient.
    if coverage is None:
        coverage = await estimate_coverage(user_id)

    claims = await _load_claims(user_id)
    behaviours = await _load_behaviour(user_id)

    # Embed claims and topics once, so the fallback below costs a single round
    # trip rather than one per pair. Empty on failure -> lexical only.
    topic_names = [b.get("topic") or "" for b in behaviours]
    vectors = await semantic_match.embed_texts(
        [c["label"] for c in claims] + topic_names
    )
    by_topic = {b.get("topic"): b for b in behaviours}

    corroborated: List[Dict[str, Any]] = []
    unsupported: List[Dict[str, Any]] = []
    not_comparable: List[Dict[str, Any]] = []
    matched_topics: Set[str] = set()

    for claim in claims:
        label = claim["label"]
        entry = {
            "label": claim["raw_label"],
            "platform": claim["platform"],
            "source_file": claim.get("source_file"),
        }

        if _is_non_testable(label):
            entry["reason"] = (
                "Demographic or life-event inference — a watch history can "
                "neither confirm nor refute it."
            )
            not_comparable.append(entry)
            continue

        match = _match_claim(label, behaviours)
        match_method = "lexical"

        if not match and vectors:
            # No shared word. Before reporting a claim unsupported — which
            # accuses the platform of profiling this person wrongly — check
            # whether the two are simply phrased differently.
            # The STRICT threshold: a loose match here reports an unevidenced
            # platform claim as corroborated, which launders the very thing
            # this report exists to catch. See semantic_match for the
            # calibration.
            semantic = semantic_match.best_semantic_match(
                label, topic_names, vectors,
                threshold=semantic_match.CORROBORATION_THRESHOLD,
            )
            if semantic:
                behaviour = by_topic.get(semantic["candidate"])
                if behaviour:
                    match = {
                        "behaviour": behaviour,
                        "matched_on": [f"~{semantic['candidate']}"],
                        "similarity": semantic["similarity"],
                    }
                    match_method = "semantic"

        if not match:
            unsupported.append(entry)
            continue

        behaviour = match["behaviour"]
        observations = int(behaviour.get("occurrence_count") or 0)
        if observations < MIN_OBSERVATIONS_FOR_SUPPORT:
            # A single sighting is a coincidence, not corroboration. Reported
            # as unsupported, but saying exactly what was found so the reader
            # can judge it themselves.
            entry["weak_match"] = {
                "topic": behaviour.get("topic"),
                "observations": observations,
                "matched_on": match["matched_on"],
            }
            unsupported.append(entry)
            continue

        matched_topics.add(behaviour.get("topic"))
        entry.update({
            "evidence": {
                "topic": behaviour.get("topic"),
                "observations": observations,
                "importance": behaviour.get("importance_score"),
                "confidence": behaviour.get("confidence_score"),
                "matched_on": match["matched_on"],
                # A shared word can be verified at a glance; a vector distance
                # cannot. Saying which was used keeps the audit honest.
                "match_method": match_method,
                "similarity": match.get("similarity"),
            }
        })
        corroborated.append(entry)

    # The other direction: what the twin can evidence that the platform never
    # claimed. Restricted to well-observed topics so this does not read as
    # "the platform missed 200 things" built from single sightings.
    missed = [
        {
            "topic": behaviour.get("topic"),
            "observations": int(behaviour.get("occurrence_count") or 0),
            "importance": behaviour.get("importance_score"),
        }
        for behaviour in behaviours
        if behaviour.get("topic") not in matched_topics
        and int(behaviour.get("occurrence_count") or 0) >= MIN_OBSERVATIONS_FOR_SUPPORT
    ]
    missed.sort(key=lambda m: m["observations"], reverse=True)

    testable = len(corroborated) + len(unsupported)
    accuracy = (len(corroborated) / testable) if testable else None

    sufficient = coverage is not None and coverage >= MIN_COVERAGE_FOR_VERDICT

    return {
        "user_id": user_id,
        "claims_total": len(claims),
        "corroborated": sorted(corroborated, key=lambda c: -(c["evidence"]["observations"])),
        "unsupported": unsupported,
        "not_comparable": not_comparable,
        "missed": missed[:25],
        "summary": {
            "testable_claims": testable,
            "corroborated": len(corroborated),
            "unsupported": len(unsupported),
            "not_comparable": len(not_comparable),
            "missed": len(missed),
            # Share of TESTABLE claims that behaviour supports. Deliberately
            # excludes not_comparable from the denominator: counting untestable
            # claims as failures would inflate the headline number, which is
            # precisely the kind of overclaim this feature exists to expose.
            "supported_share": accuracy,
        },
        "coverage": coverage,
        "verdict_reliable": sufficient,
        "caveats": [
            "Absence of evidence is not evidence of absence: this compares the "
            "platform's claims only against the history you imported. Activity "
            "outside that window, or on other apps, is invisible here.",
            "Platforms infer interests from signals beyond your own activity, "
            "including lookalike modelling and off-platform data. An "
            "unsupported claim is one you cannot verify, not necessarily one "
            "that is false.",
            "Matching is lexical first, then falls back to comparing meaning "
            "when no words are shared. Matches found by meaning are labelled "
            "and carry their similarity score, because a shared word can be "
            "checked at a glance and a vector distance cannot.",
        ] + ([] if sufficient else [
            f"Your data coverage is below {int(MIN_COVERAGE_FOR_VERDICT * 100)}%. "
            "There is not yet enough behaviour here to judge a platform's "
            "profile — import more history before relying on these verdicts."
        ]),
    }
