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


# --- Allowed values for the "kind" field ------------------------------------
# A kind describes what sort of thing an item is.
KIND_PRACTICE = "practice"  # repeats forever, never "done" (e.g. sitar)
KIND_LEARN = "learn"        # has steps, grows over time (e.g. learn a raga)
KIND_TODO = "todo"          # a one-off that gets checked off and leaves

# --- Allowed values for the "commitment" field ------------------------------
# How much the user is committing to a practice/learn item.
COMMITMENT_EVERYDAY = "everyday"    # a daily anchor
COMMITMENT_OPTIONAL = "optional"    # nice-to-do, fills leftover time

# --- Allowed values for the "status" field ----------------------------------
STATUS_ACTIVE = "active"    # shows up in the app
STATUS_DONE = "done"        # a finished todo; leaves the active list


class Item(SQLModel, table=True):
    """One thing the user tracks.

    ``table=True`` tells SQLModel to create a real database table for this
    class (called ``item``).
    """

    # The primary key. `Optional[int]` + default None means "the database
    # fills this in automatically when the row is saved".
    id: int | None = Field(default=None, primary_key=True)

    title: str

    # practice / learn / todo  (see the KIND_* constants above)
    kind: str

    # everyday / optional — only meaningful for practice & learn items.
    # Todos leave this as None and use a due date instead.
    commitment: str | None = None

    # Mainly for todos: when it's due. None means "no date".
    due_date: date | None = None

    # Mainly for learn items: the concrete next bit to do, so the nudge
    # can suggest it (e.g. "slow section of Raga Yaman").
    next_step: str | None = None

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
