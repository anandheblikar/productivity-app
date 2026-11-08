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
from sqlmodel import Session, select

from app import categorize
from app.database import get_session, init_db
from app.models import (
    RHYTHM_ONCE,
    RHYTHM_ORDER,
    STATUS_ACTIVE,
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


def render(request: Request, template_name: str, **context):
    """Render a template, always including the current time for the top bar."""
    context["request"] = request
    context["now"] = datetime.now()
    return templates.TemplateResponse(request, template_name, context)


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


# --- Everything (grouped by category) ---------------------------------------
@app.get("/everything")
def everything(request: Request, session: Session = Depends(get_session)):
    # Only active items show here (done todos leave the list).
    items = session.exec(
        select(Item).where(Item.status == STATUS_ACTIVE)
    ).all()

    # Group items by category, in the fixed category order.
    groups = []
    for name in categorize.CATEGORY_ORDER:
        in_group = [item for item in items if item.category == name]
        if in_group:
            groups.append(
                {
                    "name": name,
                    "emoji": categorize.CATEGORY_EMOJI[name],
                    # Not "items": that name clashes with dict.items() in templates.
                    "members": in_group,
                }
            )

    return render(
        request,
        "everything.html",
        title="Everything",
        active="everything",
        groups=groups,
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

    item = Item(
        title=title.strip(),
        rhythm=rhythm,
        due_date=parsed_due,
        next_step=(next_step.strip() if next_step else None),
        category=categorize.categorize(title),  # the app files it for you
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


# Allow `uv run python -m app.main` to start the server directly.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
