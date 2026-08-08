from sqlalchemy import inspect

from backend.app.config import get_settings
from backend.app.database import check_database, create_db_engine


def test_postgres_is_reachable_and_has_no_application_tables() -> None:
    engine = create_db_engine(get_settings())
    try:
        check_database(engine)
        assert inspect(engine).get_table_names() == []
    finally:
        engine.dispose()
