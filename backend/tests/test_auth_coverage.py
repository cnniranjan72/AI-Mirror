"""Every user-scoped endpoint must enforce the auth gate.

This codebase had a real version of this gap: read endpoints once took user_id
as a plain query parameter with no relation to the caller's token, so anyone
who knew a username could read that account's data. app/api/deps.py closed it,
but nothing stopped the next endpoint from being written the old way — and the
symptom is invisible, because an unenforced endpoint behaves perfectly for its
owner.

So the rule is checked mechanically rather than left to review. Two ways it can
be broken:

  1. A handler takes user_id and never validates it at all.
  2. A handler validates it, then uses the RAW parameter anyway — the
     validated value assigned and quietly ignored.

The second is the nastier one: the enforcement call is right there in the
source, so it reads as correct and passes any grep-based audit.

What this CANNOT see: an endpoint that takes no user_id at all because the
data it touches belongs to everyone. POST /rl/feedback was exactly that — it
wrote to rl_policy, a table keyed on (context_key, action_id) and shared by
every user, so nothing here flagged it and it went unauthenticated. That was
found by probing the live service, not by this file. Shared-state writes need
their own gate; see tests/test_rl_feedback_integrity.py.

No database, no network — the route table and the AST are enough.
"""
import ast
import inspect
import io
import pathlib

import pytest

# Resolved from this file, not the working directory, so the check runs the
# same from backend/, from the repo root, or under CI.
API_DIR = pathlib.Path(__file__).resolve().parent.parent / "app" / "api"

ENFORCERS = ("resolve_user_id", "require_auth", "enforce_user_match", "enforce_write_match")

# Endpoints that legitimately take a user_id without a gate. Anything added
# here needs a reason, which is the point of making it an explicit list.
EXEMPT = {
    # Registration and login establish identity; there is no token yet.
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
}


def _user_scoped_routes():
    from app.main import app

    out = []
    for route in app.routes:
        path = getattr(route, "path", None)
        endpoint = getattr(route, "endpoint", None)
        methods = getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
        if not path or not endpoint or not methods:
            continue
        try:
            signature = inspect.signature(endpoint)
        except (TypeError, ValueError):
            continue
        if "user_id" not in signature.parameters:
            continue
        out.append((sorted(methods)[0], path, endpoint, signature))
    return out


def test_the_audit_actually_finds_routes():
    """A guard on the guard: if route discovery silently broke, every test
    below would pass vacuously."""
    routes = _user_scoped_routes()
    assert len(routes) > 20, f"only found {len(routes)} user-scoped routes; discovery is broken"


@pytest.mark.parametrize("method,path,endpoint,signature", [
    pytest.param(m, p, e, s, id=f"{m} {p}") for m, p, e, s in _user_scoped_routes()
])
def test_every_user_scoped_route_enforces_auth(method, path, endpoint, signature):
    if (method, path) in EXEMPT:
        pytest.skip("explicitly exempt")

    try:
        source = inspect.getsource(endpoint)
    except (OSError, TypeError):  # dynamically constructed handler
        pytest.fail(
            f"{method} {path} takes user_id but its source cannot be read, so "
            f"enforcement cannot be verified. Define it in a module."
        )
    defaults = " ".join(str(p.default) for p in signature.parameters.values())

    assert any(e in source or e in defaults for e in ENFORCERS), (
        f"{method} {path} accepts user_id but never validates it against the "
        f"caller's token. Use Depends(resolve_user_id) for reads, or "
        f"enforce_write_match for writes."
    )


def test_no_handler_validates_user_id_then_ignores_it():
    """The subtle failure: `resolved = await resolve_user_id(...)` followed by
    using the raw `user_id` anyway. The enforcement call is visibly present, so
    this survives review and any text-based audit."""
    leaks = []

    for path in sorted(API_DIR.glob("*.py")):
        tree = ast.parse(io.open(path, encoding="utf-8").read())
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            calls = [
                n for n in ast.walk(fn)
                if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "resolve_user_id"
            ]
            if not calls:
                continue

            inside_call = {id(n) for c in calls for n in ast.walk(c)}
            leaked = [
                n.lineno for n in ast.walk(fn)
                if isinstance(n, ast.Name)
                and n.id == "user_id"
                and id(n) not in inside_call
                and not isinstance(getattr(n, "ctx", None), ast.Store)
            ]
            if leaked:
                leaks.append(f"{path.name}:{fn.name} uses raw user_id at line(s) {leaked}")

    assert not leaks, (
        "These handlers validate user_id and then use the unvalidated value:\n  "
        + "\n  ".join(leaks)
    )


# --- The guard's own sensitivity -------------------------------------------
#
# Both checks above currently pass, which is the point — but a check that has
# quietly stopped being able to fail looks exactly the same from the outside.
# These pin the detector against known-bad and known-good handlers so it cannot
# rot into an assertion that always holds.

_UNGUARDED = """
async def handler(user_id: str = Query(default="default")):
    return await build_report(user_id)
"""

_VALIDATES_THEN_IGNORES = """
async def handler(user_id: str = Query(default="default"), authorization=None):
    resolved = await resolve_user_id(user_id=user_id, authorization=authorization)
    return await build_report(user_id)
"""

_CORRECT = """
async def handler(user_id: str = Query(default="default"), authorization=None):
    resolved = await resolve_user_id(user_id=user_id, authorization=authorization)
    return await build_report(resolved)
"""


def _raw_user_id_lines(snippet):
    """The same analysis test_no_handler_validates_user_id_then_ignores_it runs."""
    fn = ast.parse(snippet).body[0]
    calls = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "resolve_user_id"
    ]
    inside_call = {id(n) for c in calls for n in ast.walk(c)}
    return [
        n.lineno for n in ast.walk(fn)
        if isinstance(n, ast.Name)
        and n.id == "user_id"
        and id(n) not in inside_call
        and not isinstance(getattr(n, "ctx", None), ast.Store)
    ]


def test_it_notices_a_handler_with_no_enforcement():
    assert not any(e in _UNGUARDED for e in ENFORCERS)


def test_it_notices_a_handler_that_validates_then_uses_the_raw_value():
    assert _raw_user_id_lines(_VALIDATES_THEN_IGNORES), (
        "the detector no longer flags the subtle case it was written for"
    )


def test_it_does_not_flag_correct_code():
    """A guard that cries wolf gets an exemption added instead of a fix."""
    assert not _raw_user_id_lines(_CORRECT)
