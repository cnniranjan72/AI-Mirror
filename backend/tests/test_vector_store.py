"""vector_store.similarity_search/hybrid_search must actually be callable —
regression test for a real bug found live in production: they passed the
raw Python list query_embedding straight to an asyncpg `::vector` cast,
which only insert_embedding() converted to pgvector's text format first.
asyncpg has no codec for the raw list, so every call failed with
"invalid input for query argument $2: [...] (expected str, got list)" —
this only surfaced when a query fell back from the main pipeline to the
RAG path (e.g. a fresh account with too little data yet), producing a
bare 500 on POST /query with no useful client-side error.
"""
import uuid

import pytest

from app.services import vector_store

pytestmark = pytest.mark.db


@pytest.mark.asyncio
async def test_similarity_search_accepts_a_real_embedding(db, disposable_user_id):
    embedding = [0.01 * i for i in range(384)]
    await vector_store.insert_embedding(
        user_id=disposable_user_id, text="a test memory", embedding=embedding, doc_type="event",
    )

    results = await vector_store.similarity_search(
        user_id=disposable_user_id, query_embedding=embedding, top_k=5,
    )
    assert len(results) == 1
    assert results[0]["text"] == "a test memory"
    assert results[0]["distance"] < 0.01  # querying with the exact same vector


@pytest.mark.asyncio
async def test_hybrid_search_accepts_a_real_embedding(db, disposable_user_id):
    embedding = [0.02 * i for i in range(384)]
    await vector_store.insert_embedding(
        user_id=disposable_user_id, text="a searchable memory about cooking", embedding=embedding,
    )

    results = await vector_store.hybrid_search(
        user_id=disposable_user_id, query_embedding=embedding, query_text="cooking", top_k=5,
    )
    assert len(results) == 1
    assert results[0]["text"] == "a searchable memory about cooking"


@pytest.mark.asyncio
async def test_similarity_search_with_no_matches_returns_empty(db):
    empty_user = f"pytest_novec_{uuid.uuid4().hex[:8]}"
    embedding = [0.5] * 384
    results = await vector_store.similarity_search(user_id=empty_user, query_embedding=embedding)
    assert results == []
