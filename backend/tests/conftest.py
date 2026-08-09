from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import create_db_engine

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config(connection: Connection) -> Config:
    config = Config(str(REPOSITORY_ROOT / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


@pytest.fixture
def migrated_connection() -> Iterator[Connection]:
    """Provide a temporary PostgreSQL schema built by Alembic migrations."""

    engine = create_db_engine(get_settings())
    schema_name = f"test_foodflow_{uuid4().hex}"
    schema_created = False
    connection: Connection | None = None

    try:
        # The identifier is generated locally and never contains user input.
        connection = engine.connect()
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
        connection.commit()
        schema_created = True
        connection.execute(text(f'SET search_path TO "{schema_name}"'))
        command.upgrade(_alembic_config(connection), "head")
        connection.commit()
        yield connection
    finally:
        if connection is not None:
            connection.rollback()
            if schema_created:
                connection.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
                connection.commit()
            connection.close()
        engine.dispose()


@pytest.fixture
def alembic_config(migrated_connection: Connection) -> Config:
    return _alembic_config(migrated_connection)


@pytest.fixture
def postgres_session(migrated_connection: Connection) -> Iterator[Session]:
    """Provide an isolated temporary PostgreSQL schema built by migrations."""

    with Session(bind=migrated_connection) as session:
        yield session
        session.rollback()
