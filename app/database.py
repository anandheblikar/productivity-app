"""Database setup: where the data lives and how we open a connection.

We use SQLite — a tiny database that is just a single file on disk
(``productivity.db``). SQLModel talks to it through an "engine", which is
the object that knows how to connect to that file.

Two helpers are exported:

- ``init_db()``      — create the tables if they don't exist yet. Called
  once when the app starts.
- ``get_session()``  — hand out a short-lived database session. FastAPI
  calls this for each request; the ``yield`` style makes sure the session
  is always closed afterwards, even if something goes wrong.
"""

from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# Importing models here (even though we don't use the names directly) makes
# sure SQLModel knows about the Item and Log tables before we create them.
from app import models  # noqa: F401

# The database file sits in the project root, next to pyproject.toml.
DB_FILE = Path(__file__).resolve().parent.parent / "productivity.db"

# The connection string SQLite understands. The engine is created once and
# reused for the whole app.
engine = create_engine(f"sqlite:///{DB_FILE}", echo=False)


def init_db() -> None:
    """Create the database tables if they don't already exist."""
    SQLModel.metadata.create_all(engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """Add columns that exist on the model but not yet in an older database.

    SQLite's ``create_all`` only creates whole tables; it won't add a new
    column to a table that already exists. So when we add a field to a model
    (like Item.notes), we patch older databases here with a one-line
    ``ALTER TABLE`` — this keeps existing data instead of wiping the file.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    item_columns = {col["name"] for col in inspector.get_columns("item")}

    if "notes" not in item_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE item ADD COLUMN notes TEXT DEFAULT ''"))


def get_session() -> Iterator[Session]:
    """Yield a database session, closing it when the request is done.

    Used as a FastAPI dependency (see main.py). Each web request gets its
    own fresh session.
    """
    with Session(engine) as session:
        yield session
