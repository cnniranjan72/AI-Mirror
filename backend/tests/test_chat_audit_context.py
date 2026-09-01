"""The twin can discuss its own audit findings — without inventing them.

The product's central guarantee is that the deterministic pipeline decides and
the language model only phrases. Handing chat the audit results puts that
guarantee under direct pressure: "you were fed this interest" is a conclusion
with a measurement behind it, and a model given raw exposure numbers would
happily reach it on vibes.

So the findings reach the prompt as PRE-COMPUTED facts carrying their own
reliability flags, and the summariser is instructed to pass a refusal through
rather than fill the gap. These tests pin down that chat can never be more
confident than the Report.

No network, no LLM — only the prompt-context summariser is exercised.
"""
import pytest

from backend.rag.context_builder import CharacterContext
from backend.verbalizer.verbalizer import LLMVerbalizer, _audit_question_kind


def _summarize(**kwargs) -> str:
    """Render the context block the model is given."""
    context = CharacterContext(user_id="test_user", **kwargs)
    return LLMVerbalizer()._summarize_context(context)


RELIABLE_AUDIT = {
    "claims_total": 10,
    "verdict_reliable": True,
    "summary": {"corroborated": 4, "unsupported": 4, "not_comparable": 2, "supported_share": 0.5},
    "unsupported": [{"label": "Cryptocurrency"}, {"label": "Online Casinos"}],
    "missed": [{"topic": "pottery"}],
}

MEASURABLE_PROVENANCE = {
    "measurable": True,
    "summary": {"fed_share_of_attention": 0.77},
    "topics": [
        {"topic": "outrage", "verdict": "fed", "exposure": 46, "searches": 0},
        {"topic": "robotics", "verdict": "chosen", "exposure": 14, "searches": 7},
    ],
}


class TestFindingsReachThePrompt:
    def test_platform_audit_numbers_are_stated(self):
        text = _summarize(platform_audit=RELIABLE_AUDIT)
        assert "Platform profile audit" in text
        assert "10 claims imported" in text
        assert "50% of testable claims are supported" in text
        assert "Cryptocurrency" in text

    def test_provenance_verdicts_are_stated_with_their_counts(self):
        text = _summarize(interest_provenance=MEASURABLE_PROVENANCE)
        assert "Interest provenance" in text
        assert "77%" in text
        assert "outrage: fed" in text
        assert "46 views, 0 searches" in text

    def test_both_are_labelled_as_measured(self):
        """The label is what tells the model these are conclusions to phrase,
        not evidence to reason over."""
        text = _summarize(platform_audit=RELIABLE_AUDIT, interest_provenance=MEASURABLE_PROVENANCE)
        assert text.count("measured, not inferred") == 2


class TestChatIsNeverMoreConfidentThanTheReport:
    """The property that matters most."""

    def test_an_unreliable_audit_is_passed_through_as_a_refusal(self):
        text = _summarize(platform_audit={**RELIABLE_AUDIT, "verdict_reliable": False})
        assert "NOT enough behavioural data to judge them" in text
        # The verdict itself must not appear anywhere.
        assert "50%" not in text
        assert "Cryptocurrency" not in text

    def test_unmeasurable_provenance_forbids_guessing(self):
        text = _summarize(interest_provenance={**MEASURABLE_PROVENANCE, "measurable": False})
        assert "NOT enough deliberate-signal data" in text
        assert "never guess" in text
        assert "77%" not in text
        assert "outrage: fed" not in text

    def test_unknown_verdicts_are_omitted_rather_than_softened(self):
        """A topic the scorer could not judge must not appear as a finding at
        all — reporting it with a hedge invites the model to hedge it away."""
        text = _summarize(interest_provenance={
            "measurable": True,
            "summary": {"fed_share_of_attention": 0.5},
            "topics": [{"topic": "mystery", "verdict": "unknown", "exposure": 3, "searches": 0}],
        })
        assert "mystery" not in text


class TestNothingToSay:
    def test_absent_audits_add_nothing_to_the_prompt(self):
        """An account that never imported an export must not pay prompt budget
        for empty sections."""
        text = _summarize()
        assert "Platform profile audit" not in text
        assert "Interest provenance" not in text

    @pytest.mark.parametrize("audit", [{}, {"claims_total": 0}])
    def test_no_claims_means_no_audit_section(self, audit):
        assert "Platform profile audit" not in _summarize(platform_audit=audit)

    @pytest.mark.parametrize("prov", [{}, {"topics": []}])
    def test_no_topics_means_no_provenance_section(self, prov):
        assert "Interest provenance" not in _summarize(interest_provenance=prov)


class TestCoverageGateDefault:
    """`coverage=None` used to mean "assume reliable", so any caller that forgot
    to pass it — chat, for one — got a verdict for free."""

    pytestmark = pytest.mark.db

    @pytest.mark.asyncio
    async def test_omitting_coverage_measures_it_rather_than_assuming(self, db, disposable_user_id):
        from app.db.postgres import execute
        from app.services.algorithmic_mirror import build_mirror_report

        await execute(
            "INSERT INTO platform_profile_claims (user_id, platform, claim_type, label, raw_label) "
            "VALUES ($1,'meta','ad_interest','robotics','Robotics')",
            disposable_user_id,
        )

        # A user with no events, topics or evidence has ~0 coverage, so no
        # verdict may be rendered even though a claim exists.
        report = await build_mirror_report(disposable_user_id)
        assert report["verdict_reliable"] is False
        assert report["coverage"] is not None

class _Intent:
    def __init__(self, question):
        self.primary_question = question


class TestQuestionRouting:
    """Keyword matching, not a classifier: this decides whether to state a
    measured finding, so it has to be as deterministic as the finding."""

    @pytest.mark.parametrize("q", [
        "Which of my interests was I fed rather than chose?",
        "did I choose this or was it pushed on me",
        "what did the algorithm feed me",
        "which interests are genuinely my own",
    ])
    def test_provenance_questions(self, q):
        assert _audit_question_kind(q) == "provenance"

    @pytest.mark.parametrize("q", [
        "what does Meta think I am interested in",
        "what ads am I targeted with",
        "is their profile of me accurate",
        "what does instagram claim about me",
    ])
    def test_platform_questions(self, q):
        assert _audit_question_kind(q) == "platform"

    @pytest.mark.parametrize("q", ["what are my top topics", "how confident are you", ""])
    def test_unrelated_questions_route_nowhere(self, q):
        assert _audit_question_kind(q) is None


class TestDeterministicAnswers:
    """The audit answer must work with NO language model. For a product whose
    claim is that the deterministic pipeline decides, a finding that only
    appears when an LLM is configured would have the dependency backwards."""

    def _lines(self, question, **ctx):
        context = CharacterContext(user_id="test_user", **ctx)
        return LLMVerbalizer()._audit_answer_lines(context, _Intent(question))

    def test_names_the_fed_topics_with_their_counts(self):
        lines = self._lines("what was I fed?", interest_provenance=MEASURABLE_PROVENANCE)
        joined = " ".join(lines)
        assert "77%" in joined
        assert "outrage: fed to you" in joined
        assert "46 views, 0 searches" in joined

    def test_names_the_chosen_topics_too(self):
        lines = self._lines("what did I choose?", interest_provenance=MEASURABLE_PROVENANCE)
        assert any("robotics: chosen" in l for l in lines)

    def test_platform_question_reports_the_audit(self):
        lines = self._lines("what does Meta think I like?", platform_audit=RELIABLE_AUDIT)
        joined = " ".join(lines)
        assert "50%" in joined
        assert "Cryptocurrency" in joined

    def test_unmeasurable_says_so_instead_of_guessing(self):
        lines = self._lines(
            "was I fed this?",
            interest_provenance={**MEASURABLE_PROVENANCE, "measurable": False},
        )
        joined = " ".join(lines)
        assert "can't tell yet" in joined
        assert "77%" not in joined
        assert "outrage" not in joined

    def test_unreliable_platform_audit_withholds_the_verdict(self):
        lines = self._lines(
            "is their profile accurate?",
            platform_audit={**RELIABLE_AUDIT, "verdict_reliable": False},
        )
        joined = " ".join(lines)
        assert "isn't enough of your behaviour recorded yet" in joined
        assert "50%" not in joined

    def test_returns_nothing_when_the_question_is_unrelated(self):
        """Falls through to the ordinary evidence answer rather than
        volunteering an audit nobody asked about."""
        assert self._lines("what are my top topics?", interest_provenance=MEASURABLE_PROVENANCE) == []

    def test_returns_nothing_when_there_is_no_audit_data(self):
        assert self._lines("what was I fed?") == []
