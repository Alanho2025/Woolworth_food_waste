"""Engine and session factory.

The single place that knows the database exists. `DATABASE_URL` is read through
the configuration boundary (clean_code_spec 6.4), never from `os.environ` here.

Schema is created from the models rather than from migrations: Requirement.md 15
defers PostgreSQL and Alembic out of the project entirely, so a migration tool
would be infrastructure for a future that this MVP has explicitly declined.
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry

from backend.app.config import get_settings
from backend.app.infrastructure.db.models import Base

SessionFactory = sessionmaker[Session]

# How long a connection waits for a lock held by another connection before
# giving up. The durable failure audit (repositories.record_failure) writes on a
# second connection, so a brief overlap must queue rather than raise.
SQLITE_BUSY_TIMEOUT_MS = 5000


def _apply_sqlite_pragmas(
    dbapi_connection: DBAPIConnection,
    connection_record: ConnectionPoolEntry,  # noqa: ARG001 - required by the SQLAlchemy event API
) -> None:
    """Set the three pragmas SQLite does not default to but this design needs.

    * `journal_mode=WAL` — readers no longer block on a writer. The API polls
      `GET /agent-runs/{id}` every ~500 ms while the Agent is writing state
      events; in the default rollback journal those reads contend with the run.
    * `busy_timeout` — a second writer waits instead of failing instantly.
    * `foreign_keys=ON` — SQLite ignores foreign keys unless asked. Without it
      the child tables behind `accepted_categories` and `needs` could be orphaned
      by a partial delete and nothing would complain until the UI rendered a
      community with no categories.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def create_db_engine(database_url: str | None = None) -> Engine:
    """Build an engine for `database_url`, defaulting to the configured one.

    `check_same_thread=False` is required because FastAPI serves requests from a
    thread pool while SQLite defaults to refusing cross-thread use of a
    connection. It is safe here only because the pool hands one connection to
    one thread at a time.
    """
    url = database_url if database_url is not None else get_settings().database_url
    connect_args: dict[str, bool] = {}
    is_sqlite = url.startswith("sqlite")
    if is_sqlite:
        connect_args["check_same_thread"] = False
    engine = create_engine(url, connect_args=connect_args, future=True)
    if is_sqlite:
        event.listen(engine, "connect", _apply_sqlite_pragmas)
    return engine


def create_session_factory(engine: Engine) -> SessionFactory:
    """Session factory bound to `engine`.

    `expire_on_commit=False` because repositories convert rows into frozen
    Pydantic contracts and the application layer keeps reading those after the
    transaction commits; expiring would trigger a refresh against a closed
    transaction.
    """
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def create_all(engine: Engine) -> None:
    """Create every table that does not already exist. Never drops."""
    Base.metadata.create_all(engine)


def reset_all(engine: Engine) -> None:
    """Recreate the demo schema exactly for the explicit seed/reset workflow."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
