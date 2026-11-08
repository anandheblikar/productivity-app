"""The nudge engine: decide the one thing to suggest tonight.

This is the heart of the app. Given the user's active items and their log
history, it ranks everything into the order we'd want to surface it, then
the Tonight screen shows the top one as *the* suggestion.

Everything hangs off one axis — an item's **rhythm** (how often it wants
your attention). The priority rule is:

    Due  →  Daily  →  Anytime  →  (undated one-offs last)

- **Due**    — a `once` item whose date is near/past, OR a `weekly`/`monthly`
  item that has come back around (its next date has arrived).
- **Daily**  — your everyday anchors.
- **Anytime** — open-ended, no schedule; chosen by *fair rotation* (least
  recently done first) so favourites don't crowd out the rest.

"Just rest" is always valid, so this happily returns nothing when there's
nothing active.

The selection functions are deliberately "pure": they take plain lists of
items and logs and a ``today`` date, touching no database and no clock of
their own. That makes them easy to unit-test. ``advance_item`` is the one
function that *changes* an item (when you've done it).
"""

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.models import (
    RECURRING_RHYTHMS,
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

# A scheduled item counts as "due" if its date is today, past, or within
# this many days ahead (so "due Fri" surfaces a couple of evenings early).
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
        if log.item_id not in latest or log.done_at > latest[log.item_id]:
            latest[log.item_id] = log.done_at
    return latest


def is_due(item: Item, today: date, window_days: int = DUE_SOON_DAYS) -> bool:
    """True if this item has a due date that is near or past.

    This covers both a one-off todo with a date and a recurring item whose
    next occurrence has arrived — both store that date in ``due_date``.
    """
    if item.due_date is None:
        return False
    return item.due_date <= today + timedelta(days=window_days)


def rank_items(items: list[Item], logs: list[Log], today: date) -> list[Item]:
    """Return active items in the order we'd suggest them.

    The buckets, highest priority first:

    1. **Due**     — anything with a due date that's near/past (one-offs and
       recurring items that have come back around), soonest first.
    2. **Daily**   — everyday anchors, least-recently-done first.
    3. **Anytime** — fair rotation: least-recently-done first.
    4. **Undated one-offs** — `once` items with no date, oldest capture first.

    Recurring items whose next date is still in the future sit quietly out
    of the list until their day comes. Done items are ignored entirely.
    """
    active = [item for item in items if item.status == STATUS_ACTIVE]
    last_done = last_done_times(logs)

    def recency_key(item: Item) -> datetime:
        # Smaller (older) means "done less recently" -> higher priority.
        return last_done.get(item.id, NEVER)

    due: list[Item] = []
    daily: list[Item] = []
    anytime: list[Item] = []
    undated_once: list[Item] = []

    for item in active:
        if is_due(item, today):
            due.append(item)
        elif item.rhythm == RHYTHM_DAILY:
            daily.append(item)
        elif item.rhythm == RHYTHM_ANYTIME:
            anytime.append(item)
        elif item.rhythm == RHYTHM_ONCE and item.due_date is None:
            undated_once.append(item)
        # Recurring items that aren't due yet are intentionally skipped.

    due.sort(key=lambda i: (i.due_date or today))
    daily.sort(key=recency_key)
    anytime.sort(key=recency_key)
    undated_once.sort(key=lambda i: i.created_at)

    return due + daily + anytime + undated_once


def daily_items(items: list[Item]) -> list[Item]:
    """Active everyday anchors — the "also today" checklist on Tonight."""
    return [
        item
        for item in items
        if item.status == STATUS_ACTIVE and item.rhythm == RHYTHM_DAILY
    ]


def tiny_version(item: Item) -> str:
    """A gentle 'smaller' version of an item, to lower the bar to starting."""
    return "short on time? → just 10 minutes"


# --- Advancing an item after you've done it ---------------------------------
def add_months(start: date, months: int) -> date:
    """Return the date `months` after `start`, clamping the day if needed.

    (e.g. Jan 31 + 1 month -> Feb 28, since February has no 31st.)
    """
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


def next_due_date(rhythm: str, today: date) -> date | None:
    """When a recurring item should next come around, measured from today."""
    if rhythm == RHYTHM_WEEKLY:
        return today + timedelta(days=7)
    if rhythm == RHYTHM_MONTHLY:
        return add_months(today, 1)
    return None


def advance_item(item: Item, today: date) -> None:
    """Record that an item was just done, by moving it along its rhythm.

    - ``once``            -> mark it done; it leaves the active list.
    - ``weekly``/``monthly`` -> roll the due date forward; it comes back later.
    - ``daily``/``anytime``  -> nothing to change (logging a session is enough).

    This mutates the item in place; the caller saves it.
    """
    if item.rhythm == RHYTHM_ONCE:
        item.status = STATUS_DONE
    elif item.rhythm in RECURRING_RHYTHMS:
        item.due_date = next_due_date(item.rhythm, today)


@dataclass
class TonightView:
    """Everything the Tonight screen needs, bundled together."""

    suggestion: Item | None = None
    also_today: list[Item] = field(default_factory=list)
    alternatives: list[Item] = field(default_factory=list)


def build_tonight(items: list[Item], logs: list[Log], today: date) -> TonightView:
    """Compose the Tonight screen from ranked items."""
    ranked = rank_items(items, logs, today)
    suggestion = ranked[0] if ranked else None

    anchors = daily_items(items)
    also_today = [item for item in anchors if item is not suggestion]

    alternatives = [item for item in ranked if item is not suggestion][:3]

    return TonightView(
        suggestion=suggestion,
        also_today=also_today,
        alternatives=alternatives,
    )
