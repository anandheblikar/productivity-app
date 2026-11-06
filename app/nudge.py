"""The nudge engine: decide the one thing to suggest tonight.

This is the heart of the app. Given the user's active items and their log
history, it ranks everything into the order we'd want to surface it, then
the Tonight screen shows the top one as *the* suggestion.

The priority rule (from the spec) is:

    Due  →  Everyday  →  Optional  →  (undated todos last)

Within the Optional group we use **fair rotation**: the item done *least
recently* comes first, so favourites don't crowd out the rest and neglected
things resurface on their own. "Just rest" is always a valid choice, so it
is fine for this to return nothing when there's nothing active.

The functions here are deliberately "pure": they take plain lists of items
and logs and return results, touching no database and no clock of their
own (the caller passes in ``today``). That makes them easy to unit-test.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.models import (
    COMMITMENT_EVERYDAY,
    COMMITMENT_OPTIONAL,
    KIND_TODO,
    STATUS_ACTIVE,
    Item,
    Log,
)

# A todo counts as "due" if its date is today, in the past, or within this
# many days ahead. ("due Fri" should surface a couple of evenings early.)
DUE_SOON_DAYS = 2

# Sorting key for "never done". datetime.min is the earliest possible time,
# so an item with no logs sorts as the *most* neglected and surfaces first.
NEVER = datetime.min


def last_done_times(logs: list[Log]) -> dict[int, datetime]:
    """Map each item id to the most recent time it was logged.

    Items that never appear in the logs simply won't be in the map; callers
    treat a missing item as "never done".
    """
    latest: dict[int, datetime] = {}
    for log in logs:
        # Keep the newest done_at we've seen for this item.
        if log.item_id not in latest or log.done_at > latest[log.item_id]:
            latest[log.item_id] = log.done_at
    return latest


def is_due(item: Item, today: date, window_days: int = DUE_SOON_DAYS) -> bool:
    """True if this item is a todo whose due date is near or past."""
    if item.kind != KIND_TODO or item.due_date is None:
        return False
    return item.due_date <= today + timedelta(days=window_days)


def rank_items(items: list[Item], logs: list[Log], today: date) -> list[Item]:
    """Return active items in the order we'd suggest them.

    The four buckets, highest priority first:

    1. **Due** todos        — sorted by due date (most urgent first).
    2. **Everyday** anchors  — sorted least-recently-done first.
    3. **Optional** items    — fair rotation: least-recently-done first.
    4. **Undated todos**     — oldest capture first, so they don't get lost.

    Done items are ignored entirely.
    """
    active = [item for item in items if item.status == STATUS_ACTIVE]
    last_done = last_done_times(logs)

    def recency_key(item: Item) -> datetime:
        # Smaller (older) means "done less recently" -> higher priority.
        return last_done.get(item.id, NEVER)

    due: list[Item] = []
    everyday: list[Item] = []
    optional: list[Item] = []
    undated_todos: list[Item] = []

    for item in active:
        if is_due(item, today):
            due.append(item)
        elif item.commitment == COMMITMENT_EVERYDAY:
            everyday.append(item)
        elif item.commitment == COMMITMENT_OPTIONAL:
            optional.append(item)
        elif item.kind == KIND_TODO:
            # A todo with no (near) due date — still worth resurfacing.
            undated_todos.append(item)
        # Anything else (shouldn't happen) is left out of the nudge.

    # Sort each bucket by its own rule.
    due.sort(key=lambda i: (i.due_date or today))
    everyday.sort(key=recency_key)
    optional.sort(key=recency_key)
    undated_todos.sort(key=lambda i: i.created_at)

    return due + everyday + optional + undated_todos


def everyday_items(items: list[Item]) -> list[Item]:
    """Active everyday anchors — the "also today" checklist on Tonight."""
    return [
        item
        for item in items
        if item.status == STATUS_ACTIVE and item.commitment == COMMITMENT_EVERYDAY
    ]


def tiny_version(item: Item) -> str:
    """A gentle 'smaller' version of an item, to lower the bar to starting.

    Kept simple for v1: the same tiny nudge for everything. Later this
    could be tailored per item (e.g. read a real duration off the item).
    """
    return "short on time? → just 10 minutes"


@dataclass
class TonightView:
    """Everything the Tonight screen needs, bundled together."""

    suggestion: Item | None = None          # the one nudge (may be None)
    also_today: list[Item] = field(default_factory=list)  # everyday checklist
    alternatives: list[Item] = field(default_factory=list)  # "something else"


def build_tonight(items: list[Item], logs: list[Log], today: date) -> TonightView:
    """Compose the Tonight screen from ranked items.

    - ``suggestion``   is the top-ranked item (or None -> "just rest").
    - ``also_today``   lists the everyday anchors (minus the suggestion).
    - ``alternatives`` is the next handful for the "Something else" screen.
    """
    ranked = rank_items(items, logs, today)
    suggestion = ranked[0] if ranked else None

    anchors = everyday_items(items)
    also_today = [item for item in anchors if item is not suggestion]

    # The alternatives are the ranked items after the top one, a few at most.
    alternatives = [item for item in ranked if item is not suggestion][:3]

    return TonightView(
        suggestion=suggestion,
        also_today=also_today,
        alternatives=alternatives,
    )
