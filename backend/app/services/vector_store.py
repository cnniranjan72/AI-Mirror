"""
Vector Store — Postgres + pgvector
insert_embedding(), similarity_search(), hybrid_search()
"""

import json
import logging
from typing import Dict, List, Any, Optional

from app.db.postgres import fetch, fetchrow, execute, executemany

logger = logging.getLogger(__name__)


async def insert_embedding(
    user_id: str,
    text: str,
    embedding: List[float],
    doc_type: str = "event",
    metadata: Optional[Dict[str, Any]] = None,
    source_event_id: Optional[int] = None,
) -> int:
    # Validate embedding dimension
    if len(embedding) != 384:
        raise ValueError(f"Embedding dimension mismatch: expected 384, got {len(embedding)}")
    
    logger.info(f"[EMBED] Vector length: {len(embedding)}")
    
    # Convert list to pgvector format string
    vec_str = "[" + ",".join(map(str, embedding)) + "]"
    
    row = await fetchrow(
        """
        INSERT INTO embeddings (user_id, text, embedding, doc_type, metadata, source_event_id)
        VALUES ($1, $2, $3::vector, $4, $5::jsonb, $6)
        RETURNING id
        """,
        user_id,
        text,
        vec_str,
        doc_type,
        json.dumps(metadata or {}),
        source_event_id,
    )
    logger.info(f"[DB] Stored embedding id={row['id']} type={doc_type} user={user_id}")
    return row["id"]


async def insert_embeddings_batch(
    user_id: str,
    texts: List[str],
    embeddings: List[List[float]],
    doc_type: str = "event",
    metadatas: Optional[List[Dict]] = None,
) -> int:
    if metadatas is None:
        metadatas = [{}] * len(texts)

    # Validate all embeddings
    for i, emb in enumerate(embeddings):
        if len(emb) != 384:
            raise ValueError(f"Embedding {i} dimension mismatch: expected 384, got {len(emb)}")
    
    logger.info(f"[EMBED] Generated {len(embeddings)} embeddings (dimension: 384)")

    # Insert one by one to avoid executemany type conversion issues
    inserted_count = 0
    for text, emb, metadata in zip(texts, embeddings, metadatas):
        await insert_embedding(
            user_id=user_id,
            text=text,
            embedding=emb,
            doc_type=doc_type,
            metadata=metadata,
        )
        inserted_count += 1
    
    logger.info(f"[DB] Batch inserted {inserted_count} embeddings for user={user_id}")
    return inserted_count


async def similarity_search(
    user_id: str,
    query_embedding: List[float],
    top_k: int = 5,
    doc_types: Optional[List[str]] = None,
    recency_weight: float = 0.0001,
) -> List[Dict[str, Any]]:
    # Validate query embedding
    if len(query_embedding) != 384:
        raise ValueError(f"Query embedding dimension mismatch: expected 384, got {len(query_embedding)}")
    
    params: list = [user_id]
    filters = ["user_id = $1"]
    idx = 1

    if doc_types:
        idx += 1
        filters.append(f"doc_type = ANY(${idx})")
        params.append(doc_types)

    where = " AND ".join(filters)
    idx += 1
    params.append(query_embedding)
    idx += 1
    lim_p = f"${idx}"
    params.append(top_k)

    sql = f"""
        SELECT id, text, metadata, doc_type, created_at,
               embedding <-> ${idx-1}::vector AS distance,
               (embedding <-> ${idx-1}::vector)
                 + (EXTRACT(EPOCH FROM (NOW() - created_at)) * {recency_weight}) AS score
        FROM embeddings
        WHERE {where}
        ORDER BY score
        LIMIT {lim_p}
    """
    rows = await fetch(sql, *params)
    return [
        {
            "id": r["id"],
            "text": r["text"],
            "metadata": r["metadata"],
            "doc_type": r["doc_type"],
            "distance": float(r["distance"]),
            "score": float(r["score"]),
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


async def hybrid_search(
    user_id: str,
    query_embedding: List[float],
    query_text: str,
    top_k: int = 5,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    doc_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    # Validate query embedding
    if len(query_embedding) != 384:
        raise ValueError(f"Query embedding dimension mismatch: expected 384, got {len(query_embedding)}")
    
    params: list = [user_id, query_embedding, query_text, vector_weight, keyword_weight, top_k]
    type_filter = ""
    if doc_types:
        type_filter = "AND doc_type = ANY($7)"
        params.append(doc_types)

    sql = f"""
        SELECT id, text, metadata, doc_type, created_at,
               (1 - (embedding <-> $2::vector)) AS sim_score,
               ts_rank(content_tsv, plainto_tsquery('english', $3)) AS kw_score,
               (1 - (embedding <-> $2::vector)) * $4
                 + ts_rank(content_tsv, plainto_tsquery('english', $3)) * $5 AS hybrid_score
        FROM embeddings
        WHERE user_id = $1 {type_filter}
        ORDER BY hybrid_score DESC
        LIMIT $6
    """
    rows = await fetch(sql, *params)
    return [
        {
            "id": r["id"],
            "text": r["text"],
            "metadata": r["metadata"],
            "doc_type": r["doc_type"],
            "sim_score": float(r["sim_score"]),
            "kw_score": float(r["kw_score"]),
            "hybrid_score": float(r["hybrid_score"]),
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


async def count(user_id: Optional[str] = None) -> int:
    if user_id:
        return await fetchrow("SELECT COUNT(*) AS c FROM embeddings WHERE user_id=$1", user_id)
    return await fetchrow("SELECT COUNT(*) AS c FROM embeddings")
