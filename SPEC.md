# Productivity App — v1 Spec

A personal, single-user tool that, at the moment the evening would otherwise dissolve into
phone/reels, suggests **one good thing to do** — then gets out of the way. Success = you do
the thing and *close the app* (less time in the app is a win).

Working name: TBD. Runs in a browser (laptop + phone), local-only for v1.

## Tech (already decided — see CLAUDE.md)
- Python, `uv` for env/packages
- FastAPI (web), SQLite + SQLModel (data), pytest (tests), Git/GitHub

## The core: the "What now?" nudge
- Shows **one** suggestion at a time, never a wall of tasks.
- "Something else" reveals 2–3 alternatives. "Just rest" is always a valid choice (no guilt).
- Each suggestion offers a **tiny version** (e.g. "just 10 min") to lower the barrier to starting.

## Items — the one spine
Everything the user tracks is an **Item**. The three old "kinds" (practice/learn/todo)
collapse onto a single axis — **rhythm**, i.e. *how often does this want my attention?*
Each item has:
- `title`
- `rhythm`: one of
  - `once` — a one-off; optional due date; finishes & leaves (the old *todo*)
  - `daily` — an everyday anchor (the old *everyday practice*)
  - `weekly` / `monthly` — repeats on a schedule; each time it's done it rolls forward
    and comes back (covers recurring chores like rent or watering plants)
  - `anytime` — no schedule, open-ended, fills leftover time (the old *optional practice*)
- `due_date`: for `once`, when it's due; for `weekly`/`monthly`, the *next* time it comes
  around (rolled forward on completion); unused for `daily`/`anytime`
- `next_step`: optional short text — the old *learn* flavour. Any item can carry one; if it
  does, the nudge shows the concrete next bit. (So "learn" isn't a separate kind — it's any
  item with a goal attached.)
- `category`: **auto-assigned** (see below) — the user never picks or manages it
- `status`: `active` / `done` (a finished `once` item leaves the active list)

## Nudge priority (the rule)
Surface in this order: **Due → Daily → Anytime.**
- `Due`: a `once` item whose date is near/passed, OR a `weekly`/`monthly` item that has
  come back around (its next date has arrived) — jumps the queue.
- `Daily`: the user's everyday anchors.
- `Anytime`: fills leftover time.

### Anytime fairness (so favorites don't crowd out the rest) — Anytime items only
1. **Fair rotation (silent default):** among Anytime items, bias selection toward the one done
   **least recently** (compute from logs). Neglected ones surface on their own.
2. **Gentle hint (only with enough data):** if one Anytime item dominates recent picks, show a
   pick-able suggestion to try another — never a block. *(Later upgrade.)*
3. **Weekly keep / promote / drop:** things repeatedly skipped surface in the weekly review as a
   decision (keep / promote to Daily / drop). *(Later upgrade.)*

### Daily soft lean
If the Daily list grows long, show a quiet hint — **never a block**. Low priority for the first build.

## Auto-categorization (the user never manages categories)
On add, the app assigns a category itself using **simple built-in keyword rules**, with an
**Other** catch-all. Categories exist only to power the weekly review.
- Starter categories: `Music` · `Spiritual` · `Health` · `Mind` · `Life stuff` · `Other`
- Example rules: "sitar"/"raga" → Music; "mantra"/"pray" → Spiritual; "run"/"gym"/"exercise" → Health;
  "read"/"learn"/"code" → Mind; "bill"/"dentist"/"buy"/"email" → Life stuff; else → Other.
- Keep the rule map in one obvious place in code. Smarter sorting (e.g. AI) is a later upgrade.

## Logging — the backbone
Every time the user does a thing they can log a **session**:
- `note` (text, always)
- optional **recording**: `media_path` + `media_type` (audio/video). For v1, a file upload saved
  to a local folder is fine; keep it simple, and it's OK if media is minimal/stubbed first.
- `done_at` timestamp
Logs power the weekly review and the Optional fair-rotation.

## Screens (match `reference/wireframe-clickable.html` — light, minimal, grayscale, system font)
Four destinations in a bottom tab bar, plus sub-screens:
1. **Tonight** (home) — the one suggestion + "also today" list.
2. **Everything** — all items, grouped by (auto) category.
3. **This week** — sessions per category over the last 7 days ("what did my life get"); also where
   skipped Optionals get keep/promote/drop.
4. **Add** (the `+`) — title, then rhythm (Once / Daily / Weekly / Monthly / Anytime); a due
   date appears only for `once`; an optional next step for any item. No category picker. Quick to add.
Sub-screens: **Something else** (alternatives), **Log a session** (after "Let's go"), **Item detail**
(history/logs, "log a session").

## Keep the UI LIGHT
Match the wireframe exactly in spirit: plain, grayscale, system font, simple borders, no heavy
styling. The user will make it pretty later. Function and clarity over looks.

## Explicitly OUT of v1
Streaks / don't-break-the-chain · points, badges, gamification · multi-user / sharing · pushy
notifications · people / birthdays (parked — returns later as a category) · calendar & integrations.

## Data model summary
- **Item**(id, title, rhythm, due_date?, next_step?, category, status, created_at)
- **Log**(id, item_id → Item, done_at, note, media_path?, media_type?)
(No separate Area/Category table needed — `category` is a string on Item, assigned by the rules.)

## Definition of done
- `uv run` starts the app on localhost.
- Can add items (category auto-assigned), see one nudge on Tonight, log a session, browse Everything
  grouped by category, and see This week.
- A few pytest tests for the real logic (categorization + nudge priority).
- README with run instructions.
