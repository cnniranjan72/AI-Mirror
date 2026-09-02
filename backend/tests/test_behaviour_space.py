"""A map of someone must not rearrange itself, or overstate what it shows.

The 384-dimensional embeddings behind every claim were never shown to anyone.
Projecting them is easy; projecting them honestly is the work, and two choices
carry the whole weight.

PCA rather than t-SNE or UMAP. Those separate clusters far more attractively
and produce a different picture on every run, because both are stochastic and
initialisation-dependent. A product arguing that its reasoning reproduces
cannot hand someone a map of themselves that looks different each time they
open it.

And the variance has to travel with the picture. Three components out of 384
capture a minority of the structure - about 40% on real data - so a convincing
cloud shown without that number invites people to read clusters that are mostly
projection artefact.
"""
import inspect

import numpy as np
import pytest

from app.services import behaviour_space as space


class TestTheProjectionIsDeterministic:
    def test_pca_gives_the_same_answer_twice(self):
        """The property t-SNE and UMAP cannot offer. Run the same maths on the
        same input and compare."""
        rng = np.random.default_rng(7)
        matrix = rng.normal(size=(60, 384))
        centred = matrix - matrix.mean(axis=0)

        first = np.linalg.svd(centred, full_matrices=False)[2][:3]
        second = np.linalg.svd(centred, full_matrices=False)[2][:3]
        assert np.allclose(first, second)

    def test_it_does_not_use_a_stochastic_projection(self):
        """Scanned with docstrings and comments stripped: the prose explains
        why t-SNE and UMAP are not used, so a naive search over the whole file
        finds those names and fails for the wrong reason."""
        import ast

        tree = ast.parse(inspect.getsource(space))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                if (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)):
                    node.body.pop(0)
        code = ast.unparse(tree)

        for stochastic in ("TSNE", "tsne", "UMAP", "umap", "random_state", "np.random"):
            assert stochastic not in code, f"{stochastic} would make the map unstable"

    def test_the_response_says_the_map_is_fixed(self):
        source = inspect.getsource(space.build_space)
        assert '"deterministic": True' in source
        assert "always draws the same shape" in source


class TestItStatesWhatIsLost:
    def test_explained_variance_is_returned(self):
        source = inspect.getsource(space.build_space)
        assert '"explained_variance"' in source
        assert '"variance_captured"' in source

    def test_variance_shares_sum_to_one_across_all_components(self):
        """The reported figure is a share of total variance, so three
        components must never appear to capture more than everything."""
        rng = np.random.default_rng(3)
        matrix = rng.normal(size=(50, 40))
        centred = matrix - matrix.mean(axis=0)
        singular = np.linalg.svd(centred, full_matrices=False)[1]
        variance = singular ** 2
        shares = variance / variance.sum()
        assert shares.sum() == pytest.approx(1.0)
        assert shares[:3].sum() <= 1.0


class TestItRefusesRatherThanDrawingNothing:
    def test_a_line_is_not_presented_as_a_cloud(self):
        """One real account came out at 100% variance on a single component:
        its space was a line wearing three dimensions. Drawing that invites
        people to read structure that is not there."""
        source = inspect.getsource(space.build_space)
        assert "degenerate" in source
        assert "explained[0] >= 0.90" in source

    def test_too_few_points_is_declined(self):
        assert space.MIN_POINTS >= 4
        source = inspect.getsource(space.build_space)
        assert "MIN_POINTS" in source

    def test_summaries_are_excluded_from_the_space(self):
        """behavioral_summary rows are templated stats lines differing by a few
        numerals, so their embeddings sit almost on top of each other and
        collapse the projection."""
        source = inspect.getsource(space.build_space)
        assert "doc_type = 'event'" in source


class TestVectorParsing:
    def test_pgvector_text_form_is_parsed(self):
        assert space._parse_vector("[0.5,-0.25,0.125]") == [0.5, -0.25, 0.125]

    def test_a_list_passes_through(self):
        assert space._parse_vector([1.0, 2.0]) == [1.0, 2.0]

    def test_junk_returns_none_rather_than_a_wrong_vector(self):
        for bad in (None, "", "not a vector", "[a,b]", 42):
            assert space._parse_vector(bad) is None

    def test_labels_prefer_the_topic_then_the_intent(self):
        assert space._label("x", {"topics": ["cooking"], "intent": "learn"}) == "cooking"
        assert space._label("x", {"intent": "entertainment"}) == "entertainment"
        assert space._label("some caption", {}) == "some caption"
        assert space._label("", {}) == "unlabelled"


class TestScale:
    def test_the_point_budget_is_bounded(self):
        assert 0 < space.MAX_POINTS <= 2000
