from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import Settings

POSTGRES_DATABASE_URL_PREFIX = "postgresql+psycopg://"


def create_db_engine(settings: Settings) -> Engine:
    """Create a PostgreSQL engine without creating tables or running migrations."""

    if not settings.database_url.startswith(POSTGRES_DATABASE_URL_PREFIX):
        raise ValueError(
            "DATABASE_URL must use the postgresql+psycopg:// scheme for the platform foundation"
        )

    return create_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a future-ready session factory; no schema is declared here."""

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def check_database(engine: Engine) -> None:
    """Verify that PostgreSQL accepts a connection without mutating state."""

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
