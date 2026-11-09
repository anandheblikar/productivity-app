"""The web app: FastAPI routes that render the screens.

FastAPI is the web framework. Each function below with an ``@app`` decorator
is a *route* — it answers one URL. We render plain HTML with Jinja2
templates (the files in ``templates/``), so there's no JavaScript build step
and every page is a normal server-rendered page.

The flow mirrors the wireframe:
    /                -> Tonight (one nudge + "also today")
    /something-else  -> alternatives
    /everything      -> all items grouped by category
    /week            -> sessions per category, last 7 days
    /add             -> add an item (GET shows the form, POST saves it)
    /item/{id}       -> item detail + history
    /item/{id}/log   -> log a session (GET form, POST saves it)
    /item/{id}/complete -> mark a todo done
"""

from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlmodel import Session, select

from app import categorize
from app.database import get_session, init_db
from app.models import (
    RHYTHM_ANYTIME,
    RHYTHM_DAILY,
    RHYTHM_MONTHLY,
    RHYTHM_ONCE,
    RHYTHM_ORDER,
    RHYTHM_WEEKLY,
    STATUS_ACTIVE,
    STATUS_DONE,
    Idea,
    Item,
    Log,
)
from app.nudge import advance_item, build_tonight, tiny_version

# Where this file lives, so we can find templates/, static/ and media/.
BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR.parent / "media"

app = FastAPI(title="Tonight — a personal productivity app")

# Create the database tables and the media folder before anything runs.
init_db()
MEDIA_DIR.mkdir(exist_ok=True)

# Jinja2 renders our HTML templates.
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Serve the CSS under /static and uploaded recordings under /media.
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


def css_version() -> int:
    """The stylesheet's last-modified time, used to bust the browser cache.

    We append this to the stylesheet URL (style.css?v=...). Whenever the CSS
    file changes the number changes, so the browser fetches the new version
    instead of showing a stale cached copy.
    """
    return int((BASE_DIR / "static" / "style.css").stat().st_mtime)


def render(request: Request, template_name: str, **context):
    """Render a template, always including the current time for the top bar."""
    context["request"] = request
    context["now"] = datetime.now()
    context["css_version"] = css_version()
    return templates.TemplateResponse(request, template_name, context)


# Smart hints for each item's free-form "canvas". We guess from keywords in
# the title what the user might keep there, and show it as a faint prompt in
# the empty box. If we can't guess, we return "" and leave the canvas blank.
CANVAS_HINTS: list[tuple[list[str], str]] = [
    (["sitar", "raga", "music", "guitar", "sing"], "Ragas or pieces to work on, tunings, notes per practice…"),
    (["cook", "recipe", "meal"], "Recipes and meals to try, ingredients, who liked what…"),
    (["read", "book"], "Reading list — titles, where you're up to, quotes…"),
    (["fittak", "weight", "kg", "gym", "run", "exercise"], "Targets, workouts, and how each weigh-in went…"),
    (["godly", "pray", "mantra", "meditate"], "Topics, readings, reflections…"),
    (["python", "git", "code", "build"], "Project ideas, links, things to learn next…"),
]


def canvas_prompt(item: Item) -> str:
    """A gentle suggestion of what to put in an item's canvas (or "")."""
    text = item.title.lower()
    for keywords, hint in CANVAS_HINTS:
        if any(keyword in text for keyword in keywords):
            return hint
    return ""  # nothing sensible to suggest — leave the canvas blank


# --- Tonight ----------------------------------------------------------------
@app.get("/")
def tonight(request: Request, session: Session = Depends(get_session)):
    items = session.exec(select(Item)).all()
    logs = session.exec(select(Log)).all()

    view = build_tonight(items, logs, date.today())

    return render(
        request,
        "tonight.html",
        title="Tonight",
        active="tonight",
        suggestion=view.suggestion,
        also_today=view.also_today,
        tiny=tiny_version(view.suggestion) if view.suggestion else "",
    )


# --- Something else (alternatives) ------------------------------------------
@app.get("/something-else")
def something_else(request: Request, session: Session = Depends(get_session)):
    items = session.exec(select(Item)).all()
    logs = session.exec(select(Log)).all()

    view = build_tonight(items, logs, date.today())

    return render(
        request,
        "something_else.html",
        title="Something else",
        back_url="/",
        alternatives=view.alternatives,
    )


# The order the Everything screen groups things in, with a friendly heading
# for each rhythm. Category is deliberately NOT shown here — it's a hidden
# field that only powers the weekly review.
EVERYTHING_GROUPS = [
    (RHYTHM_DAILY, "Daily"),
    (RHYTHM_WEEKLY, "Weekly"),
    (RHYTHM_MONTHLY, "Monthly"),
    (RHYTHM_ONCE, "To-do"),
    (RHYTHM_ANYTIME, "Anytime"),
]


# How the To-do section is shown: "checklist" (tick-boxes) or "list" (plain).
# Remembered in a cookie so the choice sticks between visits.
TODO_VIEW_COOKIE = "todo_view"


@app.get("/view/todos/{mode}")
def set_todo_view(mode: str):
    """Switch the To-do section between checklist and plain list, and remember it."""
    mode = "list" if mode == "list" else "checklist"
    response = RedirectResponse(url="/everything", status_code=303)
    response.set_cookie(TODO_VIEW_COOKIE, mode, max_age=60 * 60 * 24 * 365)
    return response


# --- Everything (grouped by rhythm) -----------------------------------------
@app.get("/everything")
def everything(request: Request, session: Session = Depends(get_session)):
    all_items = session.exec(select(Item)).all()
    todo_view = request.cookies.get(TODO_VIEW_COOKIE, "checklist")

    # Group items by rhythm, in the order above.
    #  - To-dos (once): in checklist mode we also keep *done* ones visible
    #    (ticked), so a tick is reversible; in plain-list mode we show only
    #    active ones, since there's no box to tick.
    #  - Every other group: only active items (those never "finish").
    # Within a group, use the manual drag order (position).
    groups = []
    for rhythm, label in EVERYTHING_GROUPS:
        if rhythm == RHYTHM_ONCE and todo_view == "checklist":
            in_group = [i for i in all_items if i.rhythm == RHYTHM_ONCE]
        else:
            in_group = [
                i for i in all_items
                if i.rhythm == rhythm and i.status == STATUS_ACTIVE
            ]
        in_group.sort(key=lambda i: i.position)
        if in_group:
            groups.append({"label": label, "rhythm": rhythm, "members": in_group})

    return render(
        request,
        "everything.html",
        title="Everything",
        active="everything",
        groups=groups,
        todo_view=todo_view,
    )


# --- This week (sessions per category, last 7 days) -------------------------
@app.get("/week")
def week(request: Request, session: Session = Depends(get_session)):
    since = datetime.now() - timedelta(days=7)
    recent_logs = session.exec(select(Log).where(Log.done_at >= since)).all()

    # Look up each item's category so we can tally logs per category.
    category_by_item = {
        item.id: item.category for item in session.exec(select(Item)).all()
    }

    counts: dict[str, int] = {}
    for log in recent_logs:
        name = category_by_item.get(log.item_id, categorize.CATEGORY_OTHER)
        counts[name] = counts.get(name, 0) + 1

    # Build the bar rows. Show the five named areas always, plus Other if it
    # has any sessions — so the "what did my life get (and not get)" picture
    # includes the zeroes.
    rows = []
    if recent_logs:
        max_count = max(counts.values())
        for name in categorize.CATEGORY_ORDER:
            count = counts.get(name, 0)
            if name == categorize.CATEGORY_OTHER and count == 0:
                continue
            # Bar width as a share of the busiest area (a sliver when zero).
            width = int(count / max_count * 100) if count else 3
            rows.append(
                {
                    "name": name,
                    "emoji": categorize.CATEGORY_EMOJI[name],
                    "count": count,
                    "width": width,
                }
            )

    return render(request, "week.html", title="This week", active="week", rows=rows)


# --- Ideas (the app's own backlog) ------------------------------------------
@app.get("/ideas")
def ideas(request: Request, session: Session = Depends(get_session)):
    # Newest ideas first; done ones sink to the bottom.
    all_ideas = session.exec(select(Idea)).all()
    all_ideas.sort(key=lambda i: (i.done, -(i.id or 0)))
    return render(request, "ideas.html", title="Ideas", active="ideas", ideas=all_ideas)


@app.post("/ideas")
def add_idea(text: str = Form(...), session: Session = Depends(get_session)):
    text = text.strip()
    if text:
        session.add(Idea(text=text))
        session.commit()
    return RedirectResponse(url="/ideas", status_code=303)


@app.post("/ideas/{idea_id}/toggle")
def toggle_idea(idea_id: int, session: Session = Depends(get_session)):
    idea = session.get(Idea, idea_id)
    if idea is not None:
        idea.done = not idea.done
        session.add(idea)
        session.commit()
    return RedirectResponse(url="/ideas", status_code=303)


@app.post("/ideas/{idea_id}/delete")
def delete_idea(idea_id: int, session: Session = Depends(get_session)):
    idea = session.get(Idea, idea_id)
    if idea is not None:
        session.delete(idea)
        session.commit()
    return RedirectResponse(url="/ideas", status_code=303)


# --- Add (GET form, POST save) ----------------------------------------------
@app.get("/add")
def add_form(request: Request):
    return render(request, "add.html", title="Add", back_url="/", rhythms=RHYTHM_ORDER)


@app.post("/add")
def add_save(
    title: str = Form(...),
    rhythm: str = Form(...),
    next_step: str | None = Form(None),
    due_date: str | None = Form(None),
    session: Session = Depends(get_session),
):
    # Work out the due date from the rhythm:
    #  - once:            the date the user picked (or none)
    #  - weekly/monthly:  start today so it surfaces right away, then it
    #                     rolls forward each time it's done
    #  - daily/anytime:   no due date
    parsed_due = None
    if rhythm == RHYTHM_ONCE:
        if due_date:  # the date input sends "YYYY-MM-DD" (or empty)
            parsed_due = date.fromisoformat(due_date)
    elif rhythm in {"weekly", "monthly"}:
        parsed_due = date.today()

    # New items go to the end of the list (highest position so far + 1).
    positions = session.exec(select(Item.position)).all()
    next_position = (max(positions) + 1) if positions else 0

    item = Item(
        title=title.strip(),
        rhythm=rhythm,
        due_date=parsed_due,
        next_step=(next_step.strip() if next_step else None),
        category=categorize.categorize(title),  # the app files it for you
        position=next_position,
    )
    session.add(item)
    session.commit()

    # After saving, go to Everything so the user sees where it landed.
    return RedirectResponse(url="/everything", status_code=303)


# --- Item detail ------------------------------------------------------------
@app.get("/item/{item_id}")
def item_detail(
    item_id: int, request: Request, session: Session = Depends(get_session)
):
    item = session.get(Item, item_id)
    if item is None:
        return RedirectResponse(url="/everything", status_code=303)

    # This item's sessions, newest first.
    logs = session.exec(
        select(Log).where(Log.item_id == item_id).order_by(Log.done_at.desc())
    ).all()

    return render(
        request,
        "detail.html",
        title=item.title,
        back_url="/everything",
        item=item,
        logs=logs,
        rhythms=RHYTHM_ORDER,
        canvas_hint=canvas_prompt(item),
    )


# --- Log a session (GET form, POST save) ------------------------------------
@app.get("/item/{item_id}/log")
def log_form(
    item_id: int, request: Request, session: Session = Depends(get_session)
):
    item = session.get(Item, item_id)
    if item is None:
        return RedirectResponse(url="/", status_code=303)

    return render(request, "log.html", title=f"Log — {item.title}", back_url="/", item=item)


@app.post("/item/{item_id}/log")
async def log_save(
    item_id: int,
    note: str = Form(""),
    recording: UploadFile | None = None,
    session: Session = Depends(get_session),
):
    item = session.get(Item, item_id)
    if item is None:
        return RedirectResponse(url="/", status_code=303)

    media_path = None
    media_type = None

    # Save an uploaded recording, if one was provided, to the media/ folder.
    if recording is not None and recording.filename:
        suffix = Path(recording.filename).suffix
        filename = f"{item_id}_{int(datetime.now().timestamp())}{suffix}"
        destination = MEDIA_DIR / filename
        destination.write_bytes(await recording.read())

        media_path = f"media/{filename}"
        content_type = recording.content_type or ""
        media_type = "video" if content_type.startswith("video") else "audio"

    log = Log(
        item_id=item_id,
        note=note.strip(),
        media_path=media_path,
        media_type=media_type,
    )
    session.add(log)

    # Doing it moves the item along its rhythm: a one-off finishes, a
    # weekly/monthly rolls to its next date, a daily/anytime just gets the
    # logged session (which feeds the fair-rotation ordering).
    advance_item(item, date.today())
    session.add(item)

    session.commit()

    # Then back to Tonight — ideally to close the app.
    return RedirectResponse(url="/", status_code=303)


# --- Mark done (without logging a note) --------------------------------------
@app.post("/item/{item_id}/complete")
def complete_item(item_id: int, session: Session = Depends(get_session)):
    """A quick "I did it" that doesn't need a written session.

    Used for one-offs (tick it off) and recurring chores (roll to next time).
    """
    item = session.get(Item, item_id)
    if item is not None:
        advance_item(item, date.today())
        session.add(item)
        session.commit()
    return RedirectResponse(url="/everything", status_code=303)


# --- Tick a to-do on/off (reversible) ----------------------------------------
@app.post("/item/{item_id}/toggle")
def toggle_item(item_id: int, session: Session = Depends(get_session)):
    """Flip a one-off between active and done.

    This powers the checkbox in the Everything list. It's reversible on
    purpose — a mis-tap just un-ticks — and the item stays in the list
    either way, so nothing disappears out from under you.
    """
    item = session.get(Item, item_id)
    if item is not None and item.rhythm == RHYTHM_ONCE:
        item.status = STATUS_ACTIVE if item.status == STATUS_DONE else STATUS_DONE
        session.add(item)
        session.commit()
    return RedirectResponse(url="/everything", status_code=303)


# --- Edit a single field inline (from the item page) ------------------------
class FieldUpdate(BaseModel):
    """One edit made inline on the item page: which field, and its new value."""

    field: str
    value: str | None = None


@app.post("/item/{item_id}/field", status_code=204)
def update_field(
    item_id: int,
    payload: FieldUpdate,
    session: Session = Depends(get_session),
):
    """Save one edited field. Called by the item page as you edit in place.

    Only a known, safe set of fields can be changed this way.
    """
    item = session.get(Item, item_id)
    if item is None:
        return

    value = (payload.value or "").strip()

    if payload.field == "title":
        if value:  # don't let the title be blanked out
            item.title = value
            item.category = categorize.categorize(value)  # re-file on rename
    elif payload.field == "next_step":
        item.next_step = value or None
    elif payload.field == "notes":
        item.notes = value
    elif payload.field == "rhythm" and value in RHYTHM_ORDER:
        item.rhythm = value
        # Keep the due date consistent with the new rhythm.
        if value in {RHYTHM_WEEKLY, RHYTHM_MONTHLY} and item.due_date is None:
            item.due_date = date.today()
        elif value in {RHYTHM_DAILY, RHYTHM_ANYTIME}:
            item.due_date = None
    elif payload.field == "due_date":
        item.due_date = date.fromisoformat(value) if value else None
    else:
        return  # unknown field — ignore

    session.add(item)
    session.commit()


# --- Reorder a group by drag-and-drop ---------------------------------------
class Reorder(BaseModel):
    """The new top-to-bottom order of one group, as a list of item ids."""

    ids: list[int]


@app.post("/reorder", status_code=204)
def reorder(payload: Reorder, session: Session = Depends(get_session)):
    """Save a new manual order for a dragged group.

    We just write each item's new position from its place in the list. Only
    the items in this one group are touched; other groups keep their order
    (positions are only ever compared within a group).
    """
    for index, item_id in enumerate(payload.ids):
        item = session.get(Item, item_id)
        if item is not None:
            item.position = index
            session.add(item)
    session.commit()


# --- Delete an item for good -------------------------------------------------
@app.post("/item/{item_id}/delete")
def delete_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if item is not None:
        # Remove its logged sessions first, then the item itself.
        logs = session.exec(select(Log).where(Log.item_id == item_id)).all()
        for log in logs:
            session.delete(log)
        session.delete(item)
        session.commit()
    return RedirectResponse(url="/everything", status_code=303)


# Allow `uv run python -m app.main` to start the server directly.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
