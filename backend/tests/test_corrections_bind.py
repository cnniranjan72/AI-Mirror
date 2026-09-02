"""A correction has to survive the pipeline, and it has to change what is said.

Two defects motivated this, both demonstrated against the live database before
being fixed.

The first: inference_id is minted as
inference_{rule}_{context_id}_{utcnow().timestamp()}, context_id is itself
ctx_{timestamp}, and every ingest runs DELETE FROM inferences then re-inserts
the whole set. The ledger keyed verdicts on that id, so a user could answer a
claim, the pipeline could re-run, and the identical claim came back as
unanswered. Forever.

The second: nothing consumed the verdicts. A user could mark a claim wrong and
the system would keep asserting it in chat. A scorecard the system ignores is
theatre.

claim_key fixes the first by identifying a claim by its content. The split
between annotate and exclude fixes the second: surfaces that SHOW reasoning
mark a denied claim, surfaces that ASSERT drop it. Hiding it everywhere would
make the user's own correction invisible and irreversible.
"""
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import calibration as cal


class TestClaimKey:
    def test_same_claim_produces_the_same_key(self):
        a = cal.claim_key("EngagementDepthRule", "Engagement style is deep, attentive")
        b = cal.claim_key("EngagementDepthRule", "Engagement style is deep, attentive")
        assert a == b

    def test_it_ignores_case_and_surrounding_space(self):
        """Regeneration can reformat; that is not a different claim."""
        assert cal.claim_key("Rule", "A Claim") == cal.claim_key("  rule ", "a claim  ")

    def test_the_same_rule_with_a_different_assertion_is_a_different_claim(self):
        """The reason rule_name alone is not enough. EngagementDepthRule emits
        both of these, and denying one must not silently deny the other."""
        deep = cal.claim_key("EngagementDepthRule", "Engagement style is deep, attentive")
        quick = cal.claim_key("EngagementDepthRule", "Engagement style is quick, scanning")
        assert deep != quick

    def test_different_rules_asserting_the_same_words_differ(self):
        assert cal.claim_key("RuleA", "same") != cal.claim_key("RuleB", "same")

    def test_missing_parts_do_not_raise(self):
        assert cal.claim_key(None, None)
        assert cal.claim_key("rule", None) != cal.claim_key(None, "label")

    def test_it_matches_the_sql_used_to_backfill(self):
        """The invariant that would fail SILENTLY: migration_v19.sql computes
        claim_key in Postgres for existing rows while Python computes it for
        new ones. If the two expressions drift, old verdicts stop matching new
        claims and corrections quietly stop binding.

        migration_v20 settled this by making claim_key a GENERATED column, so
        Postgres owns the single definition and no insert can omit it. Python
        keeps its copy only for matching rows in memory, and the two must
        still agree - checked for real through Postgres in
        test_the_generated_key_matches_python below.
        """
        sql = (Path(__file__).parent.parent / "app" / "db" / "migration_v20.sql").read_text()
        assert "GENERATED ALWAYS AS" in sql, "claim_key must not be insertable"
        assert "md5(" in sql
        # Same normalisation on both sides: lower + trim, joined by a pipe.
        assert "lower(btrim(coalesce(rule_name" in sql
        assert "lower(btrim(coalesce(label" in sql


class TestWhatCountsAsDenial:
    def test_only_wrong_denies(self):
        """An "unsure" answer is real but it is not a rejection. Treating
        hesitation as denial would let the system discard anything the user
        merely found hard to judge.

        Checks the code with the docstring stripped - the prose explains the
        distinction, so a naive substring search on the whole source finds
        "unsure" there and passes for the wrong reason. Behaviour is covered
        by test_unsure_does_not_suppress_anything.
        """
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(cal.contested_claim_keys).strip())
        function = tree.body[0]
        if (isinstance(function.body[0], ast.Expr)
                and isinstance(function.body[0].value, ast.Constant)):
            function.body.pop(0)   # drop the docstring
        code = ast.unparse(function)

        assert "wrong" in code
        assert "unsure" not in code


class TestTheSplit:
    def test_assert_surfaces_exclude(self):
        sql = cal.not_contested("inferences")
        assert "NOT EXISTS" in sql
        assert "wrong" in sql
        assert "cv.claim_key = inferences.claim_key" in sql

    def test_the_predicate_binds_to_the_given_alias(self):
        assert "i.claim_key" in cal.not_contested("i")
        assert "inferences.claim_key" not in cal.not_contested("i")

    def test_it_matches_on_the_stable_key_not_the_id(self):
        """Matching on inference_id is the original bug: ids are regenerated
        every ingest, so the denial would stop applying immediately."""
        assert "inference_id" not in cal.not_contested("inferences")

    @pytest.mark.asyncio
    async def test_annotation_keeps_the_claim_visible(self, monkeypatch):
        async def fake_fetch(*_a, **_k):
            return [{"claim_key": cal.claim_key("R", "denied")}]
        monkeypatch.setattr(cal, "fetch", fake_fetch)

        rows = await cal.annotate_contested("u", [
            {"rule_name": "R", "label": "denied"},
            {"rule_name": "R", "label": "kept"},
        ])
        assert len(rows) == 2, "annotation must not drop rows"
        assert rows[0]["contested"] is True
        assert rows[1]["contested"] is False

    @pytest.mark.asyncio
    async def test_annotation_is_a_no_op_with_no_denials(self, monkeypatch):
        async def fake_fetch(*_a, **_k):
            return []
        monkeypatch.setattr(cal, "fetch", fake_fetch)
        rows = await cal.annotate_contested("u", [{"rule_name": "R", "label": "x"}])
        assert len(rows) == 1


# -- Against the live database -----------------------------------------------

CLAIMS = [
    ("EngagementDepthRule", "Engagement style is deep, attentive"),
    ("EngagementDepthRule", "Engagement style is quick, scanning"),
    ("CreatorDiversityRule", "Broad creator exploration"),
]
DENIED = "Engagement style is deep, attentive"
SAME_RULE_OTHER = "Engagement style is quick, scanning"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def demo_user_id(db):
    user_id = f"demo_bind_{uuid.uuid4().hex[:8]}"
    yield user_id
    from app.services import data_privacy
    try:
        await data_privacy.delete_all_user_data(user_id)
    except Exception:
        pass


async def _regenerate(user_id):
    """What every ingest does: wipe the set and re-mint it with fresh ids."""
    from app.db.postgres import execute

    await execute("DELETE FROM inferences WHERE user_id = $1", user_id)
    ids = {}
    for rule, label in CLAIMS:
        inference_id = (f"inference_{rule}_ctx_{datetime.utcnow().timestamp()}"
                        f"_{uuid.uuid4().hex[:4]}")
        await execute(
            """INSERT INTO inferences (inference_id, user_id, inference_type, label,
                   description, confidence, rule_name, context_id,
                   inferred_at, valid_from)
               VALUES ($1,$2,'interest',$3,$4,0.9,$5,$6,NOW(),NOW())""",
            inference_id, user_id, label, f"because: {label}", rule,
            f"ctx_{datetime.utcnow().timestamp()}",
        )
        ids[label] = inference_id
    return ids


async def _deny(client, user_id, inference_id, verdict="wrong"):
    resp = await client.post("/calibration/verdict", json={
        "user_id": user_id, "claim_type": "inference",
        "claim_id": inference_id, "verdict": verdict,
    })
    assert resp.status_code == 200, resp.text


async def _assertable(user_id):
    """What the chat and the character are allowed to say."""
    from app.db.postgres import fetch

    rows = await fetch(
        "SELECT label FROM inferences WHERE user_id = $1" + cal.not_contested("inferences"),
        user_id,
    )
    return {r["label"] for r in rows}


@pytest.mark.db
@pytest.mark.asyncio
async def test_an_answered_claim_is_not_asked_again_after_regeneration(db, demo_user_id, client):
    """The original defect, end to end."""
    ids = await _regenerate(demo_user_id)
    await _deny(client, demo_user_id, ids[DENIED])

    await _regenerate(demo_user_id)  # every id is now different

    open_claims = (await client.get(f"/calibration/open?user_id={demo_user_id}")).json()
    labels = [c["label"] for c in open_claims]
    assert DENIED not in labels, "the answered claim came back as unanswered"
    assert SAME_RULE_OTHER in labels, "an unanswered claim went missing"


@pytest.mark.db
@pytest.mark.asyncio
async def test_a_denied_claim_is_not_asserted(db, demo_user_id, client):
    ids = await _regenerate(demo_user_id)
    await _deny(client, demo_user_id, ids[DENIED])
    await _regenerate(demo_user_id)

    labels = await _assertable(demo_user_id)
    assert DENIED not in labels
    assert SAME_RULE_OTHER in labels, "denying one claim suppressed a different one"


@pytest.mark.db
@pytest.mark.asyncio
async def test_a_denied_claim_stays_visible_where_reasoning_is_shown(db, demo_user_id, client):
    """It must be marked, not vanished — otherwise the correction is invisible
    and the user cannot take it back."""
    ids = await _regenerate(demo_user_id)
    await _deny(client, demo_user_id, ids[DENIED])
    await _regenerate(demo_user_id)

    shown = (await client.get(f"/reasoning/inferences?user_id={demo_user_id}")).json()
    by_label = {r["label"]: r for r in shown}
    assert by_label[DENIED]["contested"] is True
    assert by_label[SAME_RULE_OTHER]["contested"] is False


@pytest.mark.db
@pytest.mark.asyncio
async def test_changing_your_mind_restores_the_claim(db, demo_user_id, client):
    """A correction has to be reversible, or it is a trap rather than a control."""
    ids = await _regenerate(demo_user_id)
    await _deny(client, demo_user_id, ids[DENIED], "wrong")
    assert DENIED not in await _assertable(demo_user_id)

    await _deny(client, demo_user_id, ids[DENIED], "right")
    assert DENIED in await _assertable(demo_user_id)


@pytest.mark.db
@pytest.mark.asyncio
async def test_unsure_does_not_suppress_anything(db, demo_user_id, client):
    ids = await _regenerate(demo_user_id)
    await _deny(client, demo_user_id, ids[DENIED], "unsure")
    assert DENIED in await _assertable(demo_user_id)


@pytest.mark.db
@pytest.mark.asyncio
async def test_the_generated_key_matches_python(db, demo_user_id):
    """The cross-language invariant, through real rows. Postgres generates
    claim_key; Python computes it to match rows in memory. If the two ever
    disagree, corrections stop binding and nothing else fails."""
    from app.db.postgres import fetch

    await _regenerate(demo_user_id)
    rows = await fetch(
        "SELECT rule_name, label, claim_key FROM inferences WHERE user_id = $1",
        demo_user_id,
    )
    assert rows, "nothing to compare"
    for row in rows:
        assert row["claim_key"] == cal.claim_key(row["rule_name"], row["label"]), (
            f"drift for {row['rule_name']!r}/{row['label']!r}"
        )


@pytest.mark.db
@pytest.mark.asyncio
async def test_claim_key_cannot_be_omitted_by_an_insert(db, demo_user_id):
    """The failure migration_v20 exists to prevent: a row inserted without a
    claim_key is silently invisible to the ledger - never offered for review,
    no error raised. A generated column makes that impossible."""
    from app.db.postgres import execute, fetchval

    await execute(
        """INSERT INTO inferences (inference_id, user_id, inference_type, label,
               description, confidence, rule_name, inferred_at, valid_from)
           VALUES ($1,$2,'interest',$3,$4,0.5,$5,NOW(),NOW())""",
        f"inference_nokey_{uuid.uuid4().hex[:8]}", demo_user_id,
        "Claim with no explicit key", "d", "SomeRule",
    )
    key = await fetchval(
        "SELECT claim_key FROM inferences WHERE user_id = $1 AND rule_name = $2",
        demo_user_id, "SomeRule",
    )
    assert key == cal.claim_key("SomeRule", "Claim with no explicit key")


@pytest.mark.db
@pytest.mark.asyncio
async def test_one_logical_claim_is_asked_once_despite_duplicate_rows(db, demo_user_id, client):
    """Regeneration can leave several rows sharing a claim_key. The open list
    must not ask the same thing twice."""
    from app.db.postgres import execute

    await _regenerate(demo_user_id)
    rule, label = CLAIMS[0]
    await execute(
        """INSERT INTO inferences (inference_id, user_id, inference_type, label,
               description, confidence, rule_name, context_id,
               inferred_at, valid_from)
           VALUES ($1,$2,'interest',$3,$4,0.9,$5,$6,NOW(),NOW())""",
        f"inference_dup_{uuid.uuid4().hex[:8]}", demo_user_id, label, "dup", rule,
        "ctx_dup",
    )

    open_claims = (await client.get(f"/calibration/open?user_id={demo_user_id}")).json()
    labels = [c["label"] for c in open_claims]
    assert labels.count(label) == 1, f"asked twice: {labels}"
