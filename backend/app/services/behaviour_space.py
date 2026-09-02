"""The shape of what someone watches, projected into three dimensions.

The system stores a 384-dimensional embedding for every piece of content it
sees and has never shown that space to anyone. It is the closest thing the
product has to a picture of the raw material every other claim is built from.

Projection is PCA, deliberately, and not t-SNE or UMAP. Those produce prettier
separation and a different picture on every run, because both are stochastic
and depend on initialisation. A product whose argument is that its reasoning is
reproducible cannot show people a map of themselves that rearranges each time
they open it. PCA on fixed input gives one answer, so two viewers of the same
history see the same shape, and so does the same viewer tomorrow.

The cost is honesty about how much is lost. Three components out of 384 capture
only part of the structure, so the explained variance is computed and returned
with the points. A convincing three-dimensional cloud that represents a small
fraction of the real geometry, shown without saying so, would be exactly the
kind of overclaim this product exists to object to.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.db.postgres import fetch

logger = logging.getLogger(__name__)

# Enough to show structure without shipping a megabyte of coordinates.
MAX_POINTS = 600

# Below this there is no geometry worth projecting: three components through
# four points will always look like a tidy shape and mean nothing.
MIN_POINTS = 8


def _parse_vector(raw: Any) -> Optional[List[float]]:
    """pgvector comes back as a string like '[0.1,-0.2,...]'."""
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        return [float(v) for v in raw]
    text = str(raw).strip()
    if not text.startswith("["):
        return None
    try:
        return [float(v) for v in text[1:-1].split(",") if v.strip()]
    except ValueError:
        return None


def _decode(value: Any) -> Dict[str, Any]:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}
    return value or {}


def _label(text: Optional[str], metadata: Dict[str, Any]) -> str:
    topics = metadata.get("topics")
    if isinstance(topics, list) and topics:
        return str(topics[0])
    intent = metadata.get("intent")
    if intent:
        return str(intent)
    return (text or "").strip()[:40] or "unlabelled"


async def build_space(user_id: str, limit: int = MAX_POINTS) -> Dict[str, Any]:
    """Project this user's stored embeddings into three dimensions."""
    import numpy as np

    # Content only. The other doc_type, behavioral_summary, holds templated
    # stats lines ("User watched 1 reels with total watch time 16s...") that
    # differ by a few numerals, so their embeddings sit almost on top of each
    # other. Mixed in, they collapse the projection: one real account came out
    # at 100% variance on a single component, meaning its "space" was a line
    # wearing three dimensions.
    rows = await fetch(
        """
        SELECT text, embedding, doc_type, metadata, created_at
        FROM embeddings
        WHERE user_id = $1 AND embedding IS NOT NULL AND doc_type = 'event'
        ORDER BY created_at DESC
        LIMIT $2
        """,
        user_id, min(limit, MAX_POINTS),
    )

    vectors, meta = [], []
    for row in rows:
        vector = _parse_vector(row["embedding"])
        if not vector:
            continue
        vectors.append(vector)
        metadata = _decode(row["metadata"])
        meta.append({
            "label": _label(row["text"], metadata),
            "text": (row["text"] or "").strip()[:160],
            "kind": row["doc_type"] or "event",
            "at": row["created_at"].isoformat() if row["created_at"] else None,
        })

    if len(vectors) < MIN_POINTS:
        return {
            "user_id": user_id,
            "measurable": False,
            "points": [],
            "note": (
                f"Only {len(vectors)} embedded items. Three components through "
                f"that few points would produce a tidy shape that means nothing, "
                f"so no projection is drawn."
            ),
        }

    # Widths differ across dimensions, so centre but do not rescale: scaling
    # each dimension to unit variance would give a dimension that barely varies
    # the same say as one that carries the structure.
    matrix = np.array(vectors, dtype=float)
    centred = matrix - matrix.mean(axis=0)

    try:
        # SVD rather than an eigendecomposition of the covariance: same result,
        # better conditioned, and it needs no 384x384 intermediate.
        _u, singular, vt = np.linalg.svd(centred, full_matrices=False)
    except np.linalg.LinAlgError as e:
        logger.error("PCA failed for %s: %s", user_id, e)
        return {"user_id": user_id, "measurable": False, "points": [],
                "note": "The projection could not be computed for this data."}

    components = vt[:3]
    coords = centred @ components.T

    variance = singular ** 2
    total = float(variance.sum()) or 1.0
    explained = [round(float(v) / total, 4) for v in variance[:3]]

    # Scale to a unit cube so the client need not guess a camera distance.
    span = float(np.abs(coords).max()) or 1.0
    coords = coords / span

    points = [{
        "x": round(float(coords[i][0]), 4),
        "y": round(float(coords[i][1]), 4),
        "z": round(float(coords[i][2]), 4),
        **meta[i],
    } for i in range(len(meta))]

    labels = sorted({p["label"] for p in points})
    captured = round(sum(explained), 4)

    # When one direction carries almost everything, the data has no
    # three-dimensional structure and the cloud is a line seen at an angle.
    # Drawing it anyway would invite people to read clusters that are not
    # there, so the flag travels with the points and the page says so.
    degenerate = explained[0] >= 0.90
    if degenerate:
        return {
            "user_id": user_id,
            "measurable": False,
            "points": [],
            "degenerate": True,
            "explained_variance": explained,
            "note": (
                f"One direction accounts for {explained[0]:.0%} of the variation, "
                f"so this history has no three-dimensional shape to show: the "
                f"points lie along a line. That usually means the content seen "
                f"so far is too uniform to separate."
            ),
        }

    return {
        "user_id": user_id,
        "measurable": True,
        "points": points,
        "labels": labels,
        "dimensions_in": len(vectors[0]),
        "explained_variance": explained,
        "variance_captured": captured,
        "deterministic": True,
        "note": (
            f"{len(points)} items, each originally {len(vectors[0])} dimensions, "
            f"projected onto the three directions of greatest variation. Those "
            f"three carry {captured:.0%} of the structure, so the remaining "
            f"{1 - captured:.0%} is not visible here. The projection is PCA and "
            f"therefore fixed: the same history always draws the same shape."
        ),
    }
