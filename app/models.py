"""The data model: the two database tables this app stores.

We use SQLModel, which lets us describe a database table as a normal
Python class. Each attribute on the class becomes a column in the table.

There are only two tables, exactly as the spec describes:

- ``Item``  — a thing the user tracks (a practice, something they're
  learning, or a one-off todo).
- ``Log``   — one record of the user *doing* an item (a "session"),
  with an optional note and an optional recording.

The small ``str`` constants near the top (``KIND_PRACTICE`` etc.) exist so
the rest of the code never has to type a bare string like ``"practice"``
and risk a typo. They are plain strings so they're easy to read in the
database and in templates.
"""

from datetime import date, datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel

# We store plain local timestamps (no timezone) — this is a personal,
# single-machine app, so "local time" is the natural mental model. Newer
# SQLModel refuses to store a timezone-less datetime unless we mark the
# field as `NaiveDatetime`, which is exactly what we want here.


# --- Allowed values for the "rhythm" field ----------------------------------
# A rhythm is the one axis that describes an item: *how often does it want
# your attention?* The old "kind" (practice/learn/todo) and "commitment"
# (everyday/optional) collapse into this single choice.
RHYTHM_ONCE = "once"        # a one-off; optional due date; finishes & leaves
RHYTHM_DAILY = "daily"      # an everyday anchor
RHYTHM_WEEKLY = "weekly"    # repeats every week; comes back when done
RHYTHM_MONTHLY = "monthly"  # repeats every month; comes back when done
RHYTHM_ANYTIME = "anytime"  # no schedule; fills leftover time, open-ended

# The rhythms that "come back" on a schedule: doing one rolls its due date
# forward instead of finishing it.
RECURRING_RHYTHMS = {RHYTHM_WEEKLY, RHYTHM_MONTHLY}

# The order rhythms appear in the Add form.
RHYTHM_ORDER = [
    RHYTHM_ONCE,
    RHYTHM_DAILY,
    RHYTHM_WEEKLY,
    RHYTHM_MONTHLY,
    RHYTHM_ANYTIME,
]

# --- Allowed values for the "status" field ----------------------------------
STATUS_ACTIVE = "active"    # shows up in the app
STATUS_DONE = "done"        # a finished one-off; leaves the active list


class Item(SQLModel, table=True):
    """One thing the user tracks.

    ``table=True`` tells SQLModel to create a real database table for this
    class (called ``item``).
    """

    # The primary key. `Optional[int]` + default None means "the database
    # fills this in automatically when the row is saved".
    id: int | None = Field(default=None, primary_key=True)

    title: str

    # once / daily / weekly / monthly / anytime (see the RHYTHM_* constants).
    rhythm: str

    # For `once`: when it's due (None = no date). For `weekly`/`monthly`:
    # the *next* time it comes around — we roll this forward each time it's
    # done. For `daily`/`anytime` it stays None.
    due_date: date | None = None

    # The optional "next bit" to do — this is the old "learn" flavour. Any
    # item can have one; if it does, the nudge shows it (e.g. "slow section
    # of Raga Yaman"). None means the item is just a habit/task, not a goal.
    next_step: str | None = None

    # A free-form "canvas" for whatever this item needs — recipes for a
    # cooking item, ragas for sitar, a reading list, links... Shown on the
    # item's page and freely editable. Empty by default.
    notes: str = ""

    # Auto-assigned by the keyword rules in categorize.py. The user never
    # picks this. It only exists to power the weekly review.
    category: str = "Other"

    # active / done
    status: str = Field(default=STATUS_ACTIVE)

    # When the item was created. `default_factory` runs datetime.now() at the
    # moment a row is created, giving each item its own timestamp.
    created_at: NaiveDatetime = Field(default_factory=datetime.now)


class Log(SQLModel, table=True):
    """One logged session: a record that the user did an item."""

    id: int | None = Field(default=None, primary_key=True)

    # Which item this session belongs to. `foreign_key` links this column
    # to the `id` column of the item table, so a Log always points at a
    # real Item.
    item_id: int = Field(foreign_key="item.id")

    # When the session happened.
    done_at: NaiveDatetime = Field(default_factory=datetime.now)

    # A short reflection. Always present (may be an empty string).
    note: str = ""

    # Optional recording saved to the local media/ folder.
    media_path: str | None = None    # e.g. "media/3_1699300000.webm"
    media_type: str | None = None    # "audio" or "video"
