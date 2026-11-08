"""Tests for the nudge engine — the priority rule, fair rotation, and
advancing an item along its rhythm.

The nudge functions are pure (they take plain lists of items and logs and a
`today` date), so we can build small fixtures by hand and check the ordering
directly, with no database involved.

Run them with:  uv run pytest
"""

from datetime import date, datetime, timedelta

from app.models import (
    RHYTHM_ANYTIME,
    RHYTHM_DAILY,
    RHYTHM_MONTHLY,
    RHYTHM_ONCE,
    RHYTHM_WEEKLY,
    STATUS_ACTIVE,
    STATUS_DONE,
    Item,
    Log,
)
from app.nudge import (
    add_months,
    advance_item,
    build_tonight,
    is_due,
    rank_items,
)

TODAY = date(2026, 11, 6)


def make_item(item_id, title="Thing", rhythm=RHYTHM_DAILY,
              due_date=None, status=STATUS_ACTIVE):
    """Build an Item with just the fields a test cares about."""
    return Item(
        id=item_id,
        title=title,
        rhythm=rhythm,
        due_date=due_date,
        status=status,
    )


def make_log(item_id, days_ago):
    """A log for `item_id`, recorded `days_ago` days before TODAY."""
    done_at = datetime(TODAY.year, TODAY.month, TODAY.day) - timedelta(days=days_ago)
    return Log(item_id=item_id, done_at=done_at)


# --- The priority rule: Due -> Daily -> Anytime -----------------------------
def test_priority_order_due_then_daily_then_anytime():
    due_once = make_item(1, "Book dentist", RHYTHM_ONCE, due_date=TODAY)
    anchor = make_item(2, "Sitar", RHYTHM_DAILY)
    optional = make_item(3, "Read", RHYTHM_ANYTIME)

    # Pass them jumbled to prove the ranking does the work.
    ranked = rank_items([optional, anchor, due_once], logs=[], today=TODAY)

    assert [item.id for item in ranked] == [1, 2, 3]


def test_recurring_item_counts_as_due_when_its_date_arrives():
    weekly = make_item(1, "Water plants", RHYTHM_WEEKLY, due_date=TODAY)
    anchor = make_item(2, "Sitar", RHYTHM_DAILY)

    ranked = rank_items([anchor, weekly], logs=[], today=TODAY)

    # The weekly chore has come around, so it outranks the daily anchor.
    assert [item.id for item in ranked] == [1, 2]


def test_recurring_item_not_yet_due_is_not_suggested():
    future_weekly = make_item(1, "Water plants", RHYTHM_WEEKLY,
                              due_date=TODAY + timedelta(days=5))
    anchor = make_item(2, "Sitar", RHYTHM_DAILY)

    ranked = rank_items([future_weekly, anchor], logs=[], today=TODAY)

    # It sits quietly out of the list until its date is near.
    assert [item.id for item in ranked] == [2]


def test_done_items_are_not_suggested():
    active = make_item(1, "Sitar", RHYTHM_DAILY)
    finished = make_item(2, "Old todo", RHYTHM_ONCE, due_date=TODAY, status=STATUS_DONE)

    ranked = rank_items([active, finished], logs=[], today=TODAY)

    assert [item.id for item in ranked] == [1]


# --- Anytime fair rotation: least-recently-done comes first -----------------
def test_anytime_rotation_prefers_least_recently_done():
    recent = make_item(1, "Read", RHYTHM_ANYTIME)
    stale = make_item(2, "Stretch", RHYTHM_ANYTIME)

    logs = [make_log(1, days_ago=1), make_log(2, days_ago=10)]

    ranked = rank_items([recent, stale], logs, TODAY)

    # The one done longest ago (stale, id 2) should be suggested first.
    assert [item.id for item in ranked] == [2, 1]


def test_never_done_anytime_surfaces_first():
    done_recently = make_item(1, "Read", RHYTHM_ANYTIME)
    never_done = make_item(2, "Stretch", RHYTHM_ANYTIME)

    logs = [make_log(1, days_ago=2)]  # only item 1 has ever been done

    ranked = rank_items([done_recently, never_done], logs, TODAY)

    # A never-done item is treated as the most neglected, so it comes first.
    assert [item.id for item in ranked] == [2, 1]


# --- is_due window ----------------------------------------------------------
def test_is_due_true_for_near_and_past_dates():
    overdue = make_item(1, "Bill", RHYTHM_ONCE, due_date=TODAY - timedelta(days=1))
    soon = make_item(2, "Call", RHYTHM_ONCE, due_date=TODAY + timedelta(days=1))
    assert is_due(overdue, TODAY) is True
    assert is_due(soon, TODAY) is True


def test_is_due_false_for_far_off_or_undated():
    far = make_item(1, "Later", RHYTHM_ONCE, due_date=TODAY + timedelta(days=30))
    undated = make_item(2, "Someday", RHYTHM_ONCE, due_date=None)
    assert is_due(far, TODAY) is False
    assert is_due(undated, TODAY) is False


# --- Advancing an item after it's done --------------------------------------
def test_advance_once_marks_it_done():
    todo = make_item(1, "Book dentist", RHYTHM_ONCE, due_date=TODAY)
    advance_item(todo, TODAY)
    assert todo.status == STATUS_DONE


def test_advance_weekly_rolls_date_forward_and_stays_active():
    chore = make_item(1, "Water plants", RHYTHM_WEEKLY, due_date=TODAY)
    advance_item(chore, TODAY)
    assert chore.status == STATUS_ACTIVE
    assert chore.due_date == TODAY + timedelta(days=7)


def test_advance_monthly_rolls_one_month():
    rent = make_item(1, "Pay rent", RHYTHM_MONTHLY, due_date=TODAY)
    advance_item(rent, TODAY)
    assert rent.due_date == date(2026, 12, 6)


def test_advance_daily_changes_nothing():
    anchor = make_item(1, "Sitar", RHYTHM_DAILY)
    advance_item(anchor, TODAY)
    assert anchor.status == STATUS_ACTIVE
    assert anchor.due_date is None


def test_add_months_clamps_to_last_day():
    # Jan 31 + 1 month -> Feb 28 (2026 is not a leap year).
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


# --- build_tonight ties it together -----------------------------------------
def test_build_tonight_picks_top_and_lists_other_anchors():
    due_once = make_item(1, "Book dentist", RHYTHM_ONCE, due_date=TODAY)
    anchor_a = make_item(2, "Sitar", RHYTHM_DAILY)
    anchor_b = make_item(3, "Mantra", RHYTHM_DAILY)

    view = build_tonight([due_once, anchor_a, anchor_b], logs=[], today=TODAY)

    # The due one-off wins the single suggestion slot.
    assert view.suggestion.id == 1
    # Both daily anchors show under "also today".
    assert {item.id for item in view.also_today} == {2, 3}


def test_build_tonight_returns_none_when_nothing_active():
    view = build_tonight([], logs=[], today=TODAY)
    assert view.suggestion is None
