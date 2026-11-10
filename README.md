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
- **Add** — title → **rhythm** (Once / Daily / Weekly / Monthly / Anytime);
  a due date appears only for one-offs, and any item can carry an optional
  "next step". No category picker; the app files each item itself from
  keywords in the title.
- **Logging** — after doing a thing, jot a note and (optionally) attach an
  audio/video recording, saved to a local `media/` folder.

### Rhythm — the one axis

Instead of separate "kinds", every item has a **rhythm** — how often it
wants your attention:

| Rhythm | Means |
|---|---|
| **Once** | a one-off; optional due date; finishes & leaves |
| **Daily** | an everyday anchor |
| **Weekly / Monthly** | a recurring chore; doing it rolls the date forward so it comes back |
| **Anytime** | no schedule; fills leftover time |

An optional **next step** on any item is the "learn / working towards a
goal" flavour — if present, the nudge shows the concrete next bit.

### How the one suggestion is chosen

Items are surfaced in priority order: **Due → Daily → Anytime**. "Due"
covers both a one-off due soon *and* a recurring item that's come back
around. Among Anytime items it uses *fair rotation* — the one done least
recently comes first — so favourites don't crowd out the rest and neglected
things resurface on their own. (See [`app/nudge.py`](app/nudge.py).)

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

## Login & hosting

The app is single-user and sits behind one password. Locally it runs with a
default password (`tonight`) so you can get started — you'll see a warning in
the console reminding you to set your own.

Before hosting it anywhere (e.g. to reach it from your phone), set these
environment variables:

- `APP_PASSWORD` — the password you'll type to sign in.
- `APP_SECRET` — a long random string used to sign the login cookie (so it
  can't be forged). Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`.
- `APP_HTTPS_ONLY=1` — once you're serving over HTTPS, so the cookie is only
  sent over a secure connection.

```bash
APP_PASSWORD='your-password' \
APP_SECRET='paste-a-long-random-string' \
APP_HTTPS_ONLY=1 \
uv run uvicorn app.main:app --host 0.0.0.0
```

**Important:** only expose this over **HTTPS** (e.g. behind a host or reverse
proxy that terminates TLS). A password sent over plain `http://` can be read
in transit. The log-out control is the ⏻ in the top-right of every screen.

## Run the tests

```bash
uv run pytest
```

## Notes

- `productivity.db` (your data) and `media/` (your recordings) are created
  at runtime and are git-ignored — they stay on your machine only.
- This is v1. Out of scope for now: streaks/points, multi-user/sharing,
  notifications, calendar integrations.
