from backend.app.config import get_settings
from backend.app.database import check_database, create_db_engine


def test_postgres_is_reachable() -> None:
    engine = create_db_engine(get_settings())
    try:
        check_database(engine)
    finally:
        engine.dispose()
