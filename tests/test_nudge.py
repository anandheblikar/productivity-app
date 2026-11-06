"""Tests for the nudge engine — the priority rule and fair rotation.

The nudge functions are pure (they take plain lists of items and logs and
a `today` date), so we can build small fixtures by hand and check the
ordering directly, with no database involved.

Run them with:  uv run pytest
"""

from datetime import date, datetime, timedelta

from app.models import (
    COMMITMENT_EVERYDAY,
    COMMITMENT_OPTIONAL,
    KIND_LEARN,
    KIND_PRACTICE,
    KIND_TODO,
    STATUS_ACTIVE,
    STATUS_DONE,
    Item,
    Log,
)
from app.nudge import build_tonight, is_due, rank_items

TODAY = date(2026, 11, 6)


def make_item(item_id, title="Thing", kind=KIND_PRACTICE, commitment=None,
              due_date=None, status=STATUS_ACTIVE):
    """Build an Item with just the fields a test cares about."""
    return Item(
        id=item_id,
        title=title,
        kind=kind,
        commitment=commitment,
        due_date=due_date,
        status=status,
    )


def make_log(item_id, days_ago):
    """A log for `item_id`, recorded `days_ago` days before TODAY."""
    done_at = datetime(TODAY.year, TODAY.month, TODAY.day) - timedelta(days=days_ago)
    return Log(item_id=item_id, done_at=done_at)


# --- The priority rule: Due -> Everyday -> Optional -------------------------
def test_priority_order_due_then_everyday_then_optional():
    due_todo = make_item(1, "Book dentist", KIND_TODO, due_date=TODAY)
    everyday = make_item(2, "Sitar", KIND_PRACTICE, COMMITMENT_EVERYDAY)
    optional = make_item(3, "Read", KIND_LEARN, COMMITMENT_OPTIONAL)

    # Pass them in a jumbled order to prove the ranking does the work.
    ranked = rank_items([optional, everyday, due_todo], logs=[], today=TODAY)

    assert [item.id for item in ranked] == [1, 2, 3]


def test_done_items_are_not_suggested():
    active = make_item(1, "Sitar", KIND_PRACTICE, COMMITMENT_EVERYDAY)
    finished = make_item(2, "Old todo", KIND_TODO, due_date=TODAY, status=STATUS_DONE)

    ranked = rank_items([active, finished], logs=[], today=TODAY)

    assert [item.id for item in ranked] == [1]


# --- Optional fair rotation: least-recently-done comes first ----------------
def test_optional_rotation_prefers_least_recently_done():
    recent = make_item(1, "Read", KIND_LEARN, COMMITMENT_OPTIONAL)
    stale = make_item(2, "Stretch", KIND_LEARN, COMMITMENT_OPTIONAL)

    logs = [
        make_log(1, days_ago=1),   # read yesterday
        make_log(2, days_ago=10),  # stretched 10 days ago
    ]

    ranked = rank_items([recent, stale], logs, TODAY)

    # The one done longest ago (stale, id 2) should be suggested first.
    assert [item.id for item in ranked] == [2, 1]


def test_never_done_optional_surfaces_first():
    done_recently = make_item(1, "Read", KIND_LEARN, COMMITMENT_OPTIONAL)
    never_done = make_item(2, "Stretch", KIND_LEARN, COMMITMENT_OPTIONAL)

    logs = [make_log(1, days_ago=2)]  # only item 1 has ever been done

    ranked = rank_items([done_recently, never_done], logs, TODAY)

    # A never-done item is treated as the most neglected, so it comes first.
    assert [item.id for item in ranked] == [2, 1]


# --- is_due window ----------------------------------------------------------
def test_is_due_true_for_near_and_past_dates():
    overdue = make_item(1, "Bill", KIND_TODO, due_date=TODAY - timedelta(days=1))
    soon = make_item(2, "Call", KIND_TODO, due_date=TODAY + timedelta(days=1))
    assert is_due(overdue, TODAY) is True
    assert is_due(soon, TODAY) is True


def test_is_due_false_for_far_off_or_undated_todos():
    far = make_item(1, "Later", KIND_TODO, due_date=TODAY + timedelta(days=30))
    undated = make_item(2, "Someday", KIND_TODO, due_date=None)
    assert is_due(far, TODAY) is False
    assert is_due(undated, TODAY) is False


# --- build_tonight ties it together -----------------------------------------
def test_build_tonight_picks_top_and_lists_other_anchors():
    due_todo = make_item(1, "Book dentist", KIND_TODO, due_date=TODAY)
    anchor_a = make_item(2, "Sitar", KIND_PRACTICE, COMMITMENT_EVERYDAY)
    anchor_b = make_item(3, "Mantra", KIND_PRACTICE, COMMITMENT_EVERYDAY)

    view = build_tonight([due_todo, anchor_a, anchor_b], logs=[], today=TODAY)

    # The due todo wins the single suggestion slot.
    assert view.suggestion.id == 1
    # Both everyday anchors show under "also today" (neither is the suggestion).
    assert {item.id for item in view.also_today} == {2, 3}


def test_build_tonight_returns_none_when_nothing_active():
    view = build_tonight([], logs=[], today=TODAY)
    assert view.suggestion is None
