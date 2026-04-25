"""
Embedding Layer
Uses sentence-transformers (all-MiniLM-L6-v2) for 384-dim embeddings.
"""

import logging
from typing import List

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_model: SentenceTransformer = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model: all-MiniLM-L6-v2")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded (dim=384)")
    return _model


def encode(text: str) -> List[float]:
    """Encode a single text string into a 384-dim vector."""
    model = _get_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def encode_batch(texts: List[str]) -> List[List[float]]:
    """Encode multiple texts into vectors."""
    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vecs]
