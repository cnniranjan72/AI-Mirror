"""Whether an account has anything to be answered about, and what to say if not.

Reads come from a frozen identity snapshot, so an account without one cannot be
answered about at all - the pipeline stops with "No identity snapshot
available" before it plans anything. That is correct. What was wrong is what
happened next: the request fell through to the simple retrieval path, which
found nothing and rendered the default template around it:

    Here's what I found relevant to your query:

    No behavioral data found yet.

    This is based on 0 behavioral data points.

It claims to have looked and reports nothing, in one breath, and says nothing
about why or what would change it. It is also the first thing a new account
sees, since asking a question is the first thing anyone does.

Worse, that same fallback answered two situations that are not alike: an
account with nothing in it, and an account whose pipeline broke. Both produced
the same sentence, so neither the person asking nor anyone reading the logs
could tell which had happened.

Measured on the deployed instance when this was written: 2 accounts had nothing
ingested, 13 held events with nothing derived from them, and 21 could actually
be answered about. Seven queries in the trace table were asked by accounts with
no snapshot, and every one produced a zero-length response.
"""
import logging
from typing import Optional

from app.db.postgres import fetchrow

logger = logging.getLogger(__name__)

# An account is answerable when a snapshot exists. The counts below only
# explain *why* one does not, so the answer can say something specific.
STATE_READY = "ready"
STATE_NO_EVENTS = "no_events"
STATE_NOT_CONSOLIDATED = "not_consolidated"
STATE_NO_IDENTITY = "no_identity"

# Consolidation forms a behaviour object once three events share a topic or a
# creator, so this is the honest floor to quote to someone asking why nothing
# has appeared. It mirrors KnowledgeConsolidationEngine.min_cluster_size; the
# number is quoted rather than imported because this is prose for a person, not
# a threshold anything branches on.
_CLUSTER_FLOOR = 3

# Above this many events with nothing consolidated, "not enough history yet" is
# no longer true and saying it would be blaming the user for our own gap.
#
# Measured by finding the smallest prefix of each real account's history that
# produces a first cluster:
#
#     demo_tx4m2pae   800 events   first cluster at 10
#     demo_vf35lyxj   159 events   first cluster at  4
#     demo_qwd0eav1   109 events   first cluster at  7
#     demo_ddz4smtf   800 events   first cluster at  5
#     test_user_001    95 events   first cluster at 12
#
# So a first pattern arrives inside a dozen events on every account measured.
# Twice the worst case leaves room for a narrower interest mix than any of
# these had.
_EXPECT_A_PATTERN_BY = 25


async def account_state(user_id: str) -> dict:
    """One query: what the account holds, and how far the pipeline got.

    Called only when the pipeline has already failed, so an extra round trip
    costs nothing anybody is waiting on in the normal case.
    """
    try:
        row = await fetchrow(
            """
            SELECT
              (SELECT COUNT(*) FROM events             WHERE user_id = $1) AS events,
              (SELECT COUNT(*) FROM behavior_objects   WHERE user_id = $1) AS behaviours,
              (SELECT COUNT(*) FROM identity_snapshots WHERE user_id = $1) AS snapshots
            """,
            user_id,
        )
    except Exception:
        logger.warning("Could not read account state for %s", user_id, exc_info=True)
        return {"state": STATE_READY, "events": 0, "behaviours": 0, "snapshots": 0}

    events = row["events"] or 0
    behaviours = row["behaviours"] or 0
    snapshots = row["snapshots"] or 0

    if snapshots:
        # A snapshot exists, so the failure was not an empty account. Saying
        # "ready" here is what keeps a real breakage from being explained away
        # as missing data.
        state = STATE_READY
    elif not events:
        state = STATE_NO_EVENTS
    elif not behaviours:
        state = STATE_NOT_CONSOLIDATED
    else:
        state = STATE_NO_IDENTITY

    return {"state": state, "events": events,
            "behaviours": behaviours, "snapshots": snapshots}


def explain(state: dict) -> Optional[str]:
    """What to tell someone whose question cannot be answered yet.

    None when the account is answerable, because then the failure was
    something else and inventing a reassuring explanation for it would be the
    same lie in a different place.

    Each message says what is there, what is missing, and the one thing that
    changes it. No message claims to have searched.
    """
    name = state.get("state")
    events = state.get("events", 0)
    behaviours = state.get("behaviours", 0)

    if name == STATE_READY:
        return None

    if name == STATE_NO_EVENTS:
        return (
            "I don't have anything to go on yet - no activity has reached me "
            "for this account.\n\n"
            "Install the Chrome extension and browse normally, and I'll start "
            "building a picture from what you actually watch. If you'd rather "
            "see what that looks like first, \"Load Demo Data\" on the landing "
            "page fills an account with synthetic history."
        )

    if name == STATE_NOT_CONSOLIDATED and events < _EXPECT_A_PATTERN_BY:
        return (
            "I've recorded %d %s, but nothing has come together into a pattern "
            "yet.\n\n"
            "A topic or creator has to show up %d times before I'll treat it as "
            "a pattern rather than a one-off, so this usually just means there "
            "isn't enough history yet. Keep browsing and ask me again."
            % (events, "event" if events == 1 else "events", _CLUSTER_FLOOR)
        )

    if name == STATE_NOT_CONSOLIDATED:
        # Enough events that a pattern should have formed. Telling this person
        # to keep browsing would be blaming them for our gap.
        return (
            "I've recorded %d events for this account but haven't turned any of "
            "them into patterns, and by this point I should have.\n\n"
            "That's a processing gap on my side, not a shortage of history. The "
            "events are safely stored, so nothing is lost - they need to be run "
            "through again." % events
        )

    # Behaviours exist but no snapshot: the pipeline got partway and stopped.
    # Not the user's problem to solve, so it does not get advice, only the
    # truth.
    return (
        "I've found %d %s in your %d recorded events, but I haven't formed an "
        "identity from them yet, so there's nothing I can answer from.\n\n"
        "This one is on my side rather than yours - the processing stopped "
        "partway. Asking again after your next batch of activity should "
        "rebuild it."
        % (behaviours, "pattern" if behaviours == 1 else "patterns", events)
    )
