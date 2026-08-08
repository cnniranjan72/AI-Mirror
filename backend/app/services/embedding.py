"""
Embedding Layer — Hugging Face's hosted Inference API for the same model
this app always used (sentence-transformers/all-MiniLM-L6-v2, 384-dim),
instead of loading it in-process.

Why: the local path pulled in torch + sentence-transformers (600MB-1GB of
dependencies, a model held resident in RAM) — fine for a dev laptop, but
too heavy for Render's free tier and tight even on cheap paid tiers. HF's
API serves the identical model, so this is a transport change only: same
vectors, same 384 dims, no pgvector schema change, no accuracy difference.
"""

import logging
import os
from typing import List

import httpx

logger = logging.getLogger(__name__)

HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# api-inference.huggingface.co (the old serverless Inference API host) is
# retired — HF now routes all providers, including their own "hf-inference"
# one, through router.huggingface.co. The plain .../models/{model} path
# routes this particular model to a SentenceSimilarityPipeline by default
# (400: "missing 1 required positional argument: 'sentences'") — the
# explicit /pipeline/feature-extraction suffix is what forces plain
# embeddings instead. Confirmed against the real live endpoint.
HF_API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}/pipeline/feature-extraction"


async def encode_batch(texts: List[str]) -> List[List[float]]:
    """Encode multiple texts into 384-dim vectors via HF's hosted API."""
    token = os.getenv("HF_API_TOKEN")
    if not token:
        raise ValueError("HF_API_TOKEN not configured")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            HF_API_URL,
            headers={"Authorization": f"Bearer {token}"},
            # normalize=True matches sentence-transformers' own
            # normalize_embeddings=True the local model always used — keeps
            # cosine-similarity behavior identical to before this switch.
            # wait_for_model absorbs HF's cold-start queueing instead of
            # erroring out on the caller.
            json={"inputs": texts, "normalize": True, "options": {"wait_for_model": True}},
        )
        resp.raise_for_status()
        return resp.json()


async def encode(text: str) -> List[float]:
    """Encode a single text string into a 384-dim vector."""
    vecs = await encode_batch([text])
    return vecs[0]
