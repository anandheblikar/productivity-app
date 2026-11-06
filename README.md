# Tonight — a personal productivity app (v1)

A tiny, single-user evening app. At the moment the evening would otherwise
dissolve into the phone, it suggests **one good thing to do** — then gets
out of the way. Success is doing the thing and *closing the app*: less time
in the app is a win.

It's deliberately light: grayscale, system font, a bottom tab bar — function
over looks. See [`SPEC.md`](SPEC.md) for the full design and the wireframes
it's built to match in [`reference/`](reference/).

## What it does

- **Tonight** — one suggestion (with a "tiny version" to lower the bar),
  plus an "also today" list of your everyday anchors.
- **Something else** — 2–3 alternatives; "just rest" is always valid.
- **Everything** — all your items, grouped automatically by category.
- **This week** — how many sessions each area got in the last 7 days.
- **Add** — title → kind → commitment *or* due date. No category picker;
  the app files each item itself from keywords in the title.
- **Logging** — after doing a thing, jot a note and (optionally) attach an
  audio/video recording, saved to a local `media/` folder.

### How the one suggestion is chosen

Items are surfaced in priority order: **Due → Everyday → Optional**. Among
Optional items it uses *fair rotation* — the one done least recently comes
first — so favourites don't crowd out the rest and neglected things
resurface on their own. (See [`app/nudge.py`](app/nudge.py).)

## Tech

- **Python** with [`uv`](https://docs.astral.sh/uv/) for environment and
  packages
- **FastAPI** serving server-rendered **Jinja2** templates (no JavaScript
  build step)
- **SQLite** + **SQLModel** for storage (a single `productivity.db` file)
- **pytest** for tests

## Project layout

```
app/
  main.py         FastAPI routes (one per screen)
  models.py       the Item and Log database tables
  database.py     SQLite engine + session setup
  categorize.py   keyword rules: title -> category  (the one obvious place)
  nudge.py        the priority + fair-rotation engine
  templates/      one HTML template per screen
  static/style.css
tests/            pytest tests for categorize + nudge
```

## Setup & run

You need [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
installed. Everything else (the right Python, all packages) is handled for
you.

Install dependencies into a local virtual environment:

```bash
uv sync
```

Start the app (with auto-reload while you edit):

```bash
uv run uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000> in a browser. On first run it creates the
`productivity.db` database and a `media/` folder automatically.

## Run the tests

```bash
uv run pytest
```

## Notes

- `productivity.db` (your data) and `media/` (your recordings) are created
  at runtime and are git-ignored — they stay on your machine only.
- This is v1. Out of scope for now: streaks/points, multi-user/sharing,
  notifications, calendar integrations.
