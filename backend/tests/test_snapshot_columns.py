"""Two columns on identity_snapshots that said things that were not true.

`valid_until` was stamped at one hour on every snapshot. Nothing on the read
path has ever consulted it - the query pipeline takes the newest snapshot, or
the pinned one - so 36 of the 38 stored snapshots claimed to have expired,
including every snapshot actually being served. Had anything enforced it, each
account would have gone dark an hour after its last ingest.

`is_active` was written TRUE and never cleared. All 38 rows were active at
once, and one account held fifteen of them: a column naming the live identity
that named every identity the account had ever had. app/services/
identity_restore.py records the same finding, which is why restore pins a
snapshot rather than trusting this column.

Neither is enforced on any read, so the fix is about what the data says rather
than about behaviour - which is the point. The schema and its contents are
released with the paper, and a reader of that dataset would conclude every
identity had expired and every version was live at the same time.
"""
import ast
import inspect
from datetime import datetime, timezone

import pytest

from identity.identity_snapshot import IdentitySnapshot, SnapshotManager


def _zeroed(model_cls):
    """Every required field at its zero value, by introspection.

    Same approach as tests/test_snapshot_gate.py, and for the same reason: the
    sub-profiles carry around forty required fields between them, and listing
    them here would make this file break whenever an unrelated one is added.
    Nothing below depends on any of their values.
    """
    zeros = {"float": 0.0, "int": 0, "str": "", "bool": False,
             "list": [], "dict": {}}
    values = {}
    for name, field in model_cls.model_fields.items():
        if not field.is_required():
            continue
        annotation = getattr(field.annotation, "__name__", "float")
        values[name] = zeros.get(annotation, 0.0)
    return model_cls(**values)


def FakeIdentity():
    """A real Identity, so these tests exercise the real from_identity path."""
    from identity import identity_engine as ie

    now = datetime.now(timezone.utc)
    kwargs = {}
    for name, field in ie.Identity.model_fields.items():
        if not field.is_required():
            continue
        ann = field.annotation
        if name == "identity_id":
            kwargs[name] = "id_1"
        elif name == "user_id":
            kwargs[name] = "u1"
        elif ann is float:
            kwargs[name] = 0.5
        elif ann is datetime:
            kwargs[name] = now
        else:
            kwargs[name] = _zeroed(ann)
    identity = ie.Identity(**kwargs)
    identity.dominant_topics = ["photography"]
    return identity


def test_a_snapshot_does_not_expire_on_a_clock():
    """It is superseded by the next one, which is what is_active records."""
    snap = SnapshotManager().create_snapshot(FakeIdentity())
    assert snap.valid_until is None
    assert snap.is_valid() is True


def test_no_expiry_still_reads_as_valid():
    """is_valid() already treated None as "does not expire"; this is the field
    finally agreeing with it."""
    snap = SnapshotManager().create_snapshot(FakeIdentity())
    assert snap.valid_until is None
    assert snap.is_valid() is True

    inactive = snap.copy(update={"is_active": False})
    assert inactive.is_valid() is False, (
        "an explicitly retired snapshot must not read as valid")


def test_a_caller_can_still_ask_for_a_time_boxed_snapshot():
    """Removing the false default should not remove the capability."""
    snap = SnapshotManager().create_snapshot(FakeIdentity(), validity_hours=6)
    assert snap.valid_until is not None

    configured = SnapshotManager({"default_validity_hours": 2})
    assert configured.create_snapshot(FakeIdentity()).valid_until is not None


def test_zero_hours_is_honoured_rather_than_falling_back():
    """`validity_hours or default` would read 0 as "unset" and quietly grant an
    hour, which is the bug shape that produced the original default."""
    snap = SnapshotManager({"default_validity_hours": 5}).create_snapshot(
        FakeIdentity(), validity_hours=0)
    assert snap.valid_until is None


def test_writing_a_snapshot_retires_the_account_s_earlier_ones():
    """Exactly one active snapshot per account, maintained on write.

    Done here rather than in a migration so an account corrects itself on its
    next ingest, with nothing to run by hand.
    """
    from pipeline import orchestrator

    src = inspect.getsource(orchestrator.V3Pipeline._insert_snapshot)
    tree = ast.parse(inspect.cleandoc(src).lstrip()) if False else ast.parse(
        __import__("textwrap").dedent(src))

    updates = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
        and "UPDATE identity_snapshots" in n.value and "is_active" in n.value
    ]
    assert updates, "nothing retires the previous snapshots"
    sql = " ".join(updates[0].value.split())
    assert "SET is_active = FALSE" in sql
    # Scoped to the account, and never to the row just written.
    assert "WHERE user_id = $1" in sql
    assert "snapshot_id <> $2" in sql


def test_the_retire_runs_for_the_account_that_was_written():
    """Passing the wrong arguments would retire another account's identity."""
    from pipeline import orchestrator
    import textwrap

    tree = ast.parse(textwrap.dedent(
        inspect.getsource(orchestrator.V3Pipeline._insert_snapshot)))

    call = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name) and node.func.id == "execute"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and "UPDATE identity_snapshots" in node.args[0].value):
            call = node
    assert call is not None, "the retire is not executed"
    passed = [ast.unparse(a) for a in call.args[1:]]
    assert passed == ["snapshot.user_id", "snapshot.snapshot_id"], passed


@pytest.mark.parametrize("hours", [None, 0])
def test_none_and_zero_both_mean_no_expiry(hours):
    snap = SnapshotManager().create_snapshot(FakeIdentity(), validity_hours=hours)
    assert snap.valid_until is None
