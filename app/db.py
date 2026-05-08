"""SQLAlchemy engine / session setup.

Uses SQLite at ``data/app.db`` by default. Override via ``DATABASE_URL``
environment variable (e.g. ``postgresql+psycopg://...`` in production).
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import BASE_DIR

_DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(_DATA_DIR, exist_ok=True)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(_DATA_DIR, 'app.db')}",
).strip()

_is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    future=True,
    echo=False,
    # SQLite + multi-threaded Flask dev server needs this.
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


# Enable WAL + foreign keys on SQLite for safer concurrent reads/writes.
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session context."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables. Safe to call multiple times."""
    from . import models  # noqa: F401 — register mappers
    Base.metadata.create_all(engine)
    _apply_lightweight_migrations()


# ---------------------------------------------------------------------------
# lightweight ALTER TABLE migrations (SQLite, no Alembic)
# ---------------------------------------------------------------------------

# Columns that were added after v1. Each entry: (table, column, ddl_type_default).
_COLUMN_ADDITIONS = [
    ("hitem3d_tasks", "oss_key", "TEXT"),
    ("hitem3d_tasks", "file_size", "INTEGER"),
    ("hitem3d_tasks", "upload_state", "VARCHAR(16) DEFAULT 'pending'"),
    ("hitem3d_tasks", "upload_error", "TEXT"),
    ("hitem3d_tasks", "asset_type", "VARCHAR(32) DEFAULT 'model_3d'"),
]


def _apply_lightweight_migrations() -> None:
    # SQLite-only: for Postgres/MySQL, use Alembic instead.
    if not _is_sqlite:
        return
    from sqlalchemy import text
    with engine.begin() as conn:
        for table, column, ddl in _COLUMN_ADDITIONS:
            existing = {
                row[1]
                for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            }
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
