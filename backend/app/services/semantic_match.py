"""Semantic fallback for topic matching.

Every comparison in the Mirror and in Provenance was lexical: two texts matched
only if they shared a word. That is fast, free, offline and perfectly
auditable — and it produced real false accusations. In a live demo, seven
searches for "astrophotography setup" failed to match the topic `astronomy`,
so the topic was reported as FED: the user was told an interest had been
installed in them when they had in fact gone looking for it seven times.

That is the worst error this product can make, so lexical matching gets a
fallback rather than a replacement:

    1. Lexical first. Free, instant, and explainable down to the token.
    2. Only if that finds nothing, compare embeddings.

Semantic matches are always LABELLED as such and carry their similarity score.
A shared word is something a reader can verify at a glance; "these two vectors
are 0.56 apart" is not, and pretending otherwise would quietly erode the
provenance discipline the rest of the codebase is built on.

THRESHOLD
---------
Calibrated by measuring, not guessing. Against the sentence-transformers model
already used for retrieval:

    related pairs      0.343 .. 0.612   (astronomy/astrophotography = 0.561)
    unrelated pairs   -0.071 .. 0.219   (pottery/real-estate       = 0.219)

0.30 sits inside that gap, biased toward the lower edge on purpose. A missed
match wrongly tells someone an interest was fed to them, or wrongly calls a
platform's claim unfounded; a spurious match merely fails to accuse. Given
which error causes harm, catching true matches is worth the occasional
generous one.

The calibration set is small (12 pairs), so this is a defensible starting
point rather than a tuned constant.
"""
from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

# The permissive default, used where a MISS is the costly error.
#
# Interest Provenance is the case: failing to connect "astrophotography setup"
# to the topic `astronomy` reports that interest as FED — telling someone an
# interest was installed in them when they went looking for it, which is the
# most harmful thing that feature can say. A loose match there costs a topic
# being called "chosen" on thin evidence; a strict one accuses the platform of
# manufacturing an interest the user actually chose.
SIMILARITY_THRESHOLD = 0.30

# The strict threshold, used where a FALSE MATCH is the costly error.
#
# The Algorithmic Mirror asks whether a platform's claim about you is supported
# by your behaviour. A loose match there does not merely mislabel a topic: it
# reports an unevidenced claim as CORROBORATED, which launders exactly the kind
# of assertion this feature exists to catch. At 0.30 the live embeddings match
# "Automotive" to `tech` (0.424) and "Luxury goods" to `travel` (0.335), and
# the demo duly told a user the platform was right about both.
#
# Calibrated against 24 hand-labelled pairs (see the commit): genuine matches
# bottom out at 0.515 ("Software engineering" ~ coding) while spurious ones top
# out at 0.514 ("Gambling" ~ gaming, genuinely adjacent). 0.45 keeps 12 of 12
# true matches with room to spare and rejects 11 of 12 false ones.
#
# Judged on pairs chosen by hand, so treat it as a considered default rather
# than a measured optimum; widen the set before moving it.
CORROBORATION_THRESHOLD = 0.45

# Embedding every candidate is a network round trip, so a single report must not
# be able to turn into thousands of them.
MAX_TEXTS_PER_REPORT = 400


def cosine(u: Sequence[float], v: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(u, v))
    nu = sum(a * a for a in u) ** 0.5
    nv = sum(b * b for b in v) ** 0.5
    if not nu or not nv:
        return 0.0
    return dot / (nu * nv)


async def embed_texts(texts: Iterable[str]) -> Dict[str, List[float]]:
    """Embed a set of texts, returning {text: vector}.

    Returns {} on any failure. Callers treat an empty map as "semantic matching
    unavailable" and fall back to lexical results — a degraded comparison is
    always better than a failed page, and this is an optional enhancement to a
    method that already works.
    """
    unique = sorted({t.strip() for t in texts if t and t.strip()})
    if not unique:
        return {}

    if len(unique) > MAX_TEXTS_PER_REPORT:
        logger.info(
            "Semantic matching skipped: %d texts exceeds the %d cap",
            len(unique), MAX_TEXTS_PER_REPORT,
        )
        return {}

    try:
        from app.services import embedding

        vectors = await embedding.encode_batch(unique)
        if not vectors or len(vectors) != len(unique):
            logger.warning("Embedding returned %s vectors for %d texts", len(vectors or []), len(unique))
            return {}
        return dict(zip(unique, vectors))
    except Exception as e:
        # No HF token, API down, rate limited — all the same to the caller.
        logger.info("Semantic matching unavailable (%s); falling back to lexical", e)
        return {}


def best_semantic_match(
    query: str,
    candidates: Sequence[str],
    vectors: Dict[str, List[float]],
    threshold: float = SIMILARITY_THRESHOLD,
) -> Optional[Dict[str, object]]:
    """Closest candidate above the threshold, or None."""
    query_vec = vectors.get(query.strip())
    if not query_vec:
        return None

    best_name, best_score = None, 0.0
    for candidate in candidates:
        candidate_vec = vectors.get(candidate.strip())
        if not candidate_vec:
            continue
        score = cosine(query_vec, candidate_vec)
        if score > best_score:
            best_name, best_score = candidate, score

    if best_name is None or best_score < threshold:
        return None
    return {"candidate": best_name, "similarity": round(best_score, 3)}
