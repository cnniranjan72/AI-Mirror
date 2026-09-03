"""The user's reading of their own question beats the classifier's.

The classifier picks how a question is read, and the reading picks which stores
the answer is drawn from. On phrasing the rules were not written from it is
right about 56% of the time (tests/test_intent_generalisation.py holds that
separation), so roughly half of naturally-worded questions were being answered
from the wrong material with no way to see it or say otherwise.

PlannerOrchestrator.build_plan has accepted an override_intent since it was
written and nothing ever passed one. These tests cover the path that now does,
and the two things that make an override worth having rather than merely
present:

  - it must change what gets retrieved, or it is decoration;
  - it must keep what the query itself yielded, or the correction retrieves
    less than the mistake did.

The second is the trap. The obvious implementation - construct an IntentPlan
with just the type - drops key_topics, key_entities and the time reference,
which come from the words and which the retrieval planner reads.
"""
import pytest

from cognitive_planning.intent_planner import IntentPlanner, requirements_for
from cognitive_planning.planner_models import UserIntentType
from cognitive_planning.planner_orchestrator import PlannerOrchestrator


QUERY = "what have i been listening to a lot lately"


def _planner():
    return IntentPlanner()


def test_override_changes_which_stores_are_read():
    """An override that does not move retrieval would be a label, not a fix."""
    orch = PlannerOrchestrator()
    classified = orch.build_plan(user_id="u", query=QUERY)
    forced = orch.build_plan(
        user_id="u", query=QUERY,
        override_intent=_planner().plan_for(QUERY, "identity_question"),
    )

    assert forced.intent_plan.intent_type == UserIntentType.IDENTITY_QUESTION
    before = {d.target.value for d in classified.retrieval_plan.directives}
    after = {d.target.value for d in forced.retrieval_plan.directives}
    assert before != after, "override left the retrieval plan unchanged"
    # identity_question is the one reading that reaches the self model.
    assert "self_model" in after


def test_override_keeps_what_the_query_yielded():
    """Entities, topics and time come from the words, and the words are the same.

    Dropping them would hand the retrieval planner less to work with than the
    classification the user was correcting.
    """
    p = _planner()
    q = "did i watch more python videos this week than last month"
    classified = p.classify(q)
    forced = p.plan_for(q, "behavioral_question")

    assert forced.key_topics == classified.key_topics
    assert forced.key_entities == classified.key_entities
    assert forced.time_reference == classified.time_reference
    assert forced.primary_question == q
    # And at least one of them is non-empty, or this test proves nothing.
    assert forced.key_topics or forced.key_entities or forced.time_reference


def test_override_is_certain_and_unambiguous():
    """It is not a guess, so nothing downstream should hedge on it."""
    forced = _planner().plan_for(QUERY, "coaching")
    assert forced.intent_confidence == 1.0
    assert forced.ambiguity_score == 0.0
    assert forced.alternatives == []


# What each reading requires, written out rather than imported.
#
# Checking requirements_for against itself is what the first version of these
# tests did, and a mutation run caught it: changing a row of the table moved
# both sides together, so a coaching question silently stopped requesting goal
# data and every assertion still passed. This table is the independent
# reference. It is deliberately redundant with the implementation - that
# redundancy is the entire test.
EXPECTED_REQUIREMENTS = {
    "information": set(),
    "recommendation": set(),
    "explanation": set(),
    "reflection": {"requires_temporal_analysis", "requires_identity_access"},
    "comparison": {"requires_comparison", "requires_behavioral_data"},
    "prediction": {
        "requires_temporal_analysis", "requires_behavioral_data",
        "requires_prediction",
    },
    "coaching": {"requires_goal_data"},
    "identity_question": {"requires_identity_access"},
    "memory_question": {"requires_memory_access"},
    "behavioral_question": {"requires_identity_access", "requires_behavioral_data"},
    "unknown": set(),
}

ALL_REQUIREMENT_FLAGS = {
    "requires_comparison", "requires_temporal_analysis", "requires_identity_access",
    "requires_memory_access", "requires_behavioral_data", "requires_goal_data",
    "requires_prediction",
}


@pytest.mark.parametrize("intent_type", list(UserIntentType))
def test_requirements_table_is_what_it_claims(intent_type):
    """Pin the table itself, so a changed row has to be a deliberate change."""
    actual = {f for f, on in requirements_for(intent_type).items() if on}
    assert actual == EXPECTED_REQUIREMENTS[intent_type.value]
    assert set(requirements_for(intent_type)) == ALL_REQUIREMENT_FLAGS


@pytest.mark.parametrize("intent_type", list(UserIntentType))
def test_an_override_requires_what_that_reading_requires(intent_type):
    """A forced reading must ask for exactly what that reading asks for.

    Not "the same as requirements_for says" - the same as the table above,
    which does not move when the implementation does.
    """
    forced = _planner().plan_for("anything at all", intent_type.value)
    on = {f for f in ALL_REQUIREMENT_FLAGS if getattr(forced, f)}
    assert on == EXPECTED_REQUIREMENTS[intent_type.value]


def test_classification_requires_what_that_reading_requires():
    """The same guard on the path the classifier takes.

    classify() and plan_for() share one derivation, and this is what stops the
    sharing from becoming a way for both to be wrong at once.
    """
    p = _planner()
    seen = set()
    for q in (
        "who am i",
        "what should i do next",
        "why do i keep doing that",
        "how have i changed",
        "compare this month to last",
        "what will i do tomorrow",
        "help me cut back on this",
        "what did i watch yesterday",
        "how much time do i spend on this",
    ):
        plan = p.classify(q)
        seen.add(plan.intent_type)
        on = {f for f in ALL_REQUIREMENT_FLAGS if getattr(plan, f)}
        assert on == EXPECTED_REQUIREMENTS[plan.intent_type.value], q
    # Guard against the queries collapsing to one intent, which would leave the
    # loop above checking a single row.
    assert len(seen) >= 4, seen


def test_unknown_reading_is_rejected_not_guessed():
    with pytest.raises(ValueError):
        _planner().plan_for(QUERY, "wishful_thinking")


def test_pipeline_ignores_an_unrecognised_override():
    """A client on an older enum should get the classifier, not a failed query.

    The alternative - raising - turns a cosmetic version skew into a dead chat
    box.
    """
    from backend.cognitive_pipeline.pipeline import _intent_override

    orch = PlannerOrchestrator()
    assert _intent_override(orch, QUERY, "wishful_thinking") is None
    assert _intent_override(orch, QUERY, None) is None
    assert _intent_override(orch, QUERY, "") is None

    forced = _intent_override(orch, QUERY, "coaching")
    assert forced is not None
    assert forced.intent_type == UserIntentType.COACHING


def test_pipeline_threads_the_override_to_the_planner():
    """The parameter has to reach build_plan, not just exist on the signature.

    This is the defect the feature was built to fix: build_plan has always had
    override_intent and the pipeline never passed anything to it.
    """
    import ast
    import inspect
    import textwrap

    from backend.cognitive_pipeline import pipeline as mod

    for name in ("process_query", "_execute_pipeline"):
        params = inspect.signature(getattr(mod.CognitivePipeline, name)).parameters
        assert "override_intent" in params, name

    tree = ast.parse(textwrap.dedent(inspect.getsource(mod.CognitivePipeline._execute_pipeline)))
    passed = [
        kw.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "build_plan"
        for kw in node.keywords
        if kw.arg == "override_intent"
    ]
    assert len(passed) == 1, "build_plan is not called with override_intent"
    # And what it passes must be derived from the argument, not a constant.
    names = {n.id for n in ast.walk(passed[0]) if isinstance(n, ast.Name)}
    assert "override_intent" in names or any(
        isinstance(n, ast.Attribute) for n in ast.walk(passed[0])
    ), "override_intent is passed something that ignores the caller"


def test_api_reports_the_reading_actually_used():
    """The response must read the reading off the plan, not echo the request.

    Echoing back would report an override as honoured even when the pipeline
    rejected the name and fell through to the classifier - the one case where
    the user most needs to be told their correction did not take.
    """
    import ast
    import inspect

    from app.api import query as qmod

    import textwrap

    src = inspect.getsource(qmod.query_insights)
    tree = ast.parse(textwrap.dedent(src))

    assigned = {
        node.targets[0].id: node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    assert "used_intent" in assigned, "no reading is derived from the result"
    derived = ast.dump(assigned["used_intent"])
    assert "intent_plan" in derived, "the reported reading is not read off the plan"
    assert "req" not in derived, "the reported reading is echoed from the request"


def test_options_offered_are_the_real_enum_minus_unknown():
    """A hardcoded list would drift; unknown is not something a user means."""
    from app.api.query import INTENT_OPTIONS

    offered = [o["value"] for o in INTENT_OPTIONS]
    assert set(offered) == {t.value for t in UserIntentType} - {"unknown"}
    assert len(offered) == len(set(offered))
    for option in INTENT_OPTIONS:
        assert option["label"] and option["label"] != option["value"], option
