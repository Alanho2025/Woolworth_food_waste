from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from backend.app.models import Base


def test_migration_upgrade_has_current_tables_and_constraints(
    migrated_connection: Connection,
    alembic_config: Config,
) -> None:
    inspector = inspect(migrated_connection)
    expected_tables = set(Base.metadata.tables) | {"alembic_version"}

    assert set(inspector.get_table_names()) == expected_tables

    allocation_indexes = {index["name"] for index in inspector.get_indexes("allocations")}
    assert "uq_allocations_active_item" in allocation_indexes

    delivery_stop_foreign_keys = {
        foreign_key["name"] for foreign_key in inspector.get_foreign_keys("delivery_stops")
    }
    assert "fk_delivery_stops_location_site" in delivery_stop_foreign_keys

    donation_item_checks = {
        check["name"] for check in inspector.get_check_constraints("donation_items")
    }
    assert "ck_donation_items_quantity_positive" in donation_item_checks

    migration_heads = ScriptDirectory.from_config(alembic_config).get_heads()
    stored_revision = migrated_connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert len(migration_heads) == 1
    assert stored_revision == migration_heads[0]


def test_migration_has_no_model_drift(
    migrated_connection: Connection,
    alembic_config: Config,
) -> None:
    command.check(alembic_config)


def test_migration_can_downgrade_and_upgrade_again(
    migrated_connection: Connection,
    alembic_config: Config,
) -> None:
    command.downgrade(alembic_config, "base")
    migrated_connection.commit()

    inspector = inspect(migrated_connection)
    assert set(inspector.get_table_names()) == {"alembic_version"}
    assert migrated_connection.scalar(text("SELECT version_num FROM alembic_version")) is None

    command.upgrade(alembic_config, "head")
    migrated_connection.commit()

    assert set(inspect(migrated_connection).get_table_names()) == (
        set(Base.metadata.tables) | {"alembic_version"}
    )
