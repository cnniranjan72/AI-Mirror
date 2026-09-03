"""Every target the planner asks for has to be servable.

The planner declares thirteen retrieval targets and the retrieval context
supplied seven. A directive whose key is absent from the context returns
nothing and logs at debug level; when the directive is marked required, the
retrieval step records a failure and the query proceeds with less than it
planned for. Nobody upstream is told.

Two intents had an unservable required source, so they failed a mandatory
directive on every single request:

    memory_question      -> memory            required=True, priority 0.8
    behavioral_question  -> behavior_history  required=True

`runtime_state` was requested by all nine intent groups and served by nothing,
though optionally and at the lowest priority.
"""
import inspect

import pytest

from cognitive_planning.planner_models import RetrievalTarget
from cognitive_planning.retrieval_planner import _INTENT_TO_TARGETS


def _planned():
    """Every (intent, target, required) the planner can emit."""
    out = []
    for intent, specs in _INTENT_TO_TARGETS.items():
        for spec in specs:
            if spec:
                target, _priority, _max_results, required = spec
                out.append((intent, target, required))
    return out


def _served_keys():
    """Keys the context assigns, read from the AST rather than the text.

    A plain substring scan is satisfied by a comment: replacing the assignment
    with `pass  # ctx["memory"] not served` leaves the string in place and the
    scan still passes. Comments do not survive parsing, so only a real
    assignment counts here.

    This remains a structural check. Assigning an empty list would defeat it
    too, which is why test_retrieval_targets_db.py loads the context against a
    real account and looks at what is in it.
    """
    import ast
    import textwrap

    from cognitive_pipeline.pipeline import CognitivePipeline

    tree = ast.parse(textwrap.dedent(
        inspect.getsource(CognitivePipeline._load_retrieval_context)))

    assigned = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "ctx"
                    and isinstance(target.slice, ast.Constant)):
                assigned.add(target.slice.value)
    return assigned


class TestRequiredSourcesAreServable:
    def test_no_intent_requires_a_target_nothing_supplies(self):
        """The defect: two intents did, on every request."""
        served = _served_keys()
        broken = sorted({
            (intent, target.value)
            for intent, target, required in _planned()
            if required and target.value not in served
        })
        assert not broken, f"required but unservable: {broken}"

    def test_memory_question_can_read_memory(self):
        served = _served_keys()
        assert RetrievalTarget.MEMORY.value in served

    def test_behavioral_question_can_read_the_watch_history(self):
        served = _served_keys()
        assert RetrievalTarget.BEHAVIOR_HISTORY.value in served


class TestTheAdditionsCarryDistinctData:
    """Serving a target by duplicating another would satisfy the check above
    while adding nothing but a larger retrieved count."""

    def test_the_history_is_events_not_consolidated_objects(self):
        from cognitive_pipeline.pipeline import CognitivePipeline

        source = inspect.getsource(CognitivePipeline._load_retrieval_context)
        marker = source[source.index('ctx["behavior_history"]') - 700:
                        source.index('ctx["behavior_history"]')]
        assert "FROM events" in marker

    def test_creator_history_aggregates_per_creator(self):
        from cognitive_pipeline.pipeline import CognitivePipeline

        # No intent marks this one required, so the sweep above does not cover
        # it; assert the assignment exists through the AST rather than relying
        # on the string appearing somewhere in the source.
        assert "creator_history" in _served_keys()

        source = inspect.getsource(CognitivePipeline._load_retrieval_context)
        marker = source[source.index('ctx["creator_history"]') - 800:
                        source.index('ctx["creator_history"]')]
        assert "GROUP BY username" in marker

    def test_memory_is_the_recall_index_ranked_by_importance(self):
        from cognitive_pipeline.pipeline import CognitivePipeline

        source = inspect.getsource(CognitivePipeline._load_retrieval_context)
        marker = source[source.index('ctx["memory"]') - 600:
                        source.index('ctx["memory"]')]
        assert "FROM memories" in marker
        assert "ORDER BY importance_score DESC" in marker


class TestRowsSurviveSerialisation:
    def test_the_average_is_cast_off_decimal(self):
        """avg() returns numeric, which asyncpg hands back as Decimal. No
        other retrieval source produces one and it reaches the prompt as a
        repr rather than a number.

        Timestamps are deliberately left as datetimes: that is what every
        other source returns and what RetrievedObject validates them as.
        Casting them to text to satisfy a json.dumps assertion broke that
        validation, which the database test caught.
        """
        from cognitive_pipeline.pipeline import CognitivePipeline

        source = inspect.getsource(CognitivePipeline._load_retrieval_context)
        assert "::float8 AS avg_watch_time" in source


class TestUnservedTargetsAreDeliberate:
    def test_runtime_state_is_left_out_on_purpose(self):
        """It is optional everywhere at priority 0.2, and what it would carry
        already reaches the later stages through character_core. Serving it
        would inflate the retrieved count without adding anything."""
        from cognitive_pipeline.pipeline import CognitivePipeline

        source = inspect.getsource(CognitivePipeline._load_retrieval_context)
        assert "runtime_state is deliberately not supplied" in source

    def test_the_unplanned_targets_are_still_unplanned(self):
        """interest_history and journal are declared on the enum and requested
        by no intent. Recorded so that a target added to the planner later
        without a source is noticed here rather than in production."""
        planned = {t for _i, t, _r in _planned()}
        unplanned = sorted(t.value for t in RetrievalTarget if t not in planned)
        assert unplanned == ["interest_history", "journal"], unplanned
