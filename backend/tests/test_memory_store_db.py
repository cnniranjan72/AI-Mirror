"""The recall index against a real database.

Separated from test_memory_store.py because the properties here cannot be
checked by reading source. A source assertion that the SQL contains
"access_count = access_count + 1" passes happily when the statement has been
given a WHERE clause that matches nothing - which is exactly the mutation that
slipped past the first version of these tests.
"""
import uuid

import pytest

from app.services import memory_store

pytestmark = pytest.mark.db


@pytest.mark.asyncio
async def test_recall_increments_the_access_count(db, disposable_user_id):
    """access_count and last_accessed sat in the schema unwritten, so nothing
    could tell a memory consulted daily from one never looked at."""
    await memory_store.remember(
        user_id=disposable_user_id, memory_type="semantic",
        subject="cooking", content="cooking recurs in this history",
        importance=0.9,
    )

    first = await memory_store.recall(disposable_user_id, limit=5)
    assert len(first) == 1
    assert first[0]["recalled_before"] == 0

    second = await memory_store.recall(disposable_user_id, limit=5)
    assert second[0]["recalled_before"] == 1, "recall must record itself"

    third = await memory_store.recall(disposable_user_id, limit=5)
    assert third[0]["recalled_before"] == 2


@pytest.mark.asyncio
async def test_the_same_subject_reinforces_rather_than_duplicates(db, disposable_user_id):
    """The reflections table accumulated 29 unusable rows by appending one per
    ingest; this must update in place."""
    for content in ("first wording", "second wording"):
        await memory_store.remember(
            user_id=disposable_user_id, memory_type="semantic",
            subject="travel", content=content, importance=0.8,
        )

    held = await memory_store.recall(disposable_user_id, limit=10)
    assert len(held) == 1
    assert held[0]["content"] == "second wording"


@pytest.mark.asyncio
async def test_unimportant_material_is_not_stored(db, disposable_user_id):
    stored = await memory_store.remember(
        user_id=disposable_user_id, memory_type="semantic",
        subject="trivia", content="barely worth noting",
        importance=memory_store.MIN_IMPORTANCE - 0.01,
    )
    assert stored is False
    assert await memory_store.recall(disposable_user_id) == []


@pytest.mark.asyncio
async def test_an_unknown_type_is_refused(db, disposable_user_id):
    stored = await memory_store.remember(
        user_id=disposable_user_id, memory_type="not_a_type",
        subject="x", content="y", importance=0.9,
    )
    assert stored is False


@pytest.mark.asyncio
async def test_recall_can_be_filtered_by_type(db, disposable_user_id):
    await memory_store.remember(
        user_id=disposable_user_id, memory_type="semantic",
        subject="a", content="a semantic memory", importance=0.9)
    await memory_store.remember(
        user_id=disposable_user_id, memory_type="reflection",
        subject="b", content="a reflection", importance=0.9)

    only = await memory_store.recall(
        disposable_user_id, limit=10, memory_types=["reflection"])
    assert {m["memory_type"] for m in only} == {"reflection"}


@pytest.mark.asyncio
async def test_recall_returns_the_most_important_first(db, disposable_user_id):
    for subject, importance in (("low", 0.4), ("high", 0.95), ("mid", 0.7)):
        await memory_store.remember(
            user_id=disposable_user_id, memory_type="semantic",
            subject=subject, content=subject, importance=importance)

    held = await memory_store.recall(disposable_user_id, limit=10)
    assert [m["content"] for m in held] == ["high", "mid", "low"]
