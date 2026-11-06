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
Everything the user tracks is an **Item**. Each has:
- `title`
- `kind`: `practice` (repeats, never done) · `learn` (has steps, grows) · `todo` (one-off, checks off & leaves)
- `commitment`: `everyday` or `optional` — asked for practice/learn; **todos use a due date instead**
- `due_date`: optional (mainly todos)
- `next_step`: optional short text (mainly learn — so the nudge can suggest the concrete next bit)
- `category`: **auto-assigned** (see below) — the user never picks or manages it
- `status`: `active` / `done` (done todos leave the active list)

## Nudge priority (the rule)
Surface in this order: **Due → Everyday → Optional.**
- `Due`: a todo whose due date is near/passed jumps the queue.
- `Everyday`: the user's daily anchors.
- `Optional`: fills leftover time.

### Optional fairness (so favorites don't crowd out the rest) — Optional items only
1. **Fair rotation (silent default):** among Optional items, bias selection toward the one done
   **least recently** (compute from logs). Neglected ones surface on their own.
2. **Gentle hint (only with enough data):** if one Optional dominates recent picks, show a
   pick-able suggestion to try another — never a block.
3. **Weekly keep / promote / drop:** things repeatedly skipped surface in the weekly review as a
   decision (keep / promote to Everyday / drop).

### Everyday soft lean
If the Everyday list grows long, show a quiet hint — **never a block**. Low priority for the first build.

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
4. **Add** (the `+`) — title, kind, then commitment OR due date. No category picker. Quick to add.
Sub-screens: **Something else** (alternatives), **Log a session** (after "Let's go"), **Item detail**
(history/logs, "log a session").

## Keep the UI LIGHT
Match the wireframe exactly in spirit: plain, grayscale, system font, simple borders, no heavy
styling. The user will make it pretty later. Function and clarity over looks.

## Explicitly OUT of v1
Streaks / don't-break-the-chain · points, badges, gamification · multi-user / sharing · pushy
notifications · people / birthdays (parked — returns later as a category) · calendar & integrations.

## Data model summary
- **Item**(id, title, kind, commitment, due_date?, next_step?, category, status, created_at)
- **Log**(id, item_id → Item, done_at, note, media_path?, media_type?)
(No separate Area/Category table needed — `category` is a string on Item, assigned by the rules.)

## Definition of done
- `uv run` starts the app on localhost.
- Can add items (category auto-assigned), see one nudge on Tonight, log a session, browse Everything
  grouped by category, and see This week.
- A few pytest tests for the real logic (categorization + nudge priority).
- README with run instructions.
