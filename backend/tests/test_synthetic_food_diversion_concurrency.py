from datetime import timedelta
from threading import Barrier, Thread
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import Allocation
from backend.tests.fixtures.synthetic_food_diversion import (
    build_listed_scenario,
    confirm_barcode_item_allocation,
)


def test_phase10d_two_transactions_allow_only_one_active_allocation(
    migrated_connection,
    postgres_session: Session,
) -> None:
    listed = build_listed_scenario(postgres_session)
    confirmed = confirm_barcode_item_allocation(postgres_session, listed)
    confirmed.allocation.status = "fulfilled"
    confirmed.allocation.fulfilled_at = listed.now + timedelta(minutes=7)
    postgres_session.commit()

    schema_name = migrated_connection.scalar(text("SELECT current_schema()"))
    engine = migrated_connection.engine
    connections = []
    sessions = []
    for _ in range(2):
        connection = engine.connect()
        connection.execute(text(f'SET search_path TO "{schema_name}"'))
        connection.commit()
        connections.append(connection)
        sessions.append(Session(bind=connection))

    barrier = Barrier(2)
    outcomes: list[str] = []

    def reserve(session: Session, recipient_site_id, candidate_id) -> None:
        session.add(
            Allocation(
                id=uuid4(),
                donation_item_id=listed.barcode_item.id,
                recipient_site_id=recipient_site_id,
                match_candidate_id=candidate_id,
                allocated_quantity=listed.barcode_item.quantity,
                quantity_unit=listed.barcode_item.quantity_unit,
                status="reserved",
                reserved_by_user_id=listed.driver.id,
                reserved_at=listed.now + timedelta(minutes=8),
            )
        )
        try:
            barrier.wait(timeout=10)
            session.commit()
        except IntegrityError:
            session.rollback()
            outcomes.append("integrity_error")
        else:
            outcomes.append("committed")

    threads = [
        Thread(
            target=reserve,
            args=(sessions[0], listed.recipient_a_site.id, confirmed.recipient_a_candidate.id),
        ),
        Thread(
            target=reserve,
            args=(sessions[1], listed.recipient_b_site.id, confirmed.recipient_b_candidate.id),
        ),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    try:
        assert all(not thread.is_alive() for thread in threads)
        assert sorted(outcomes) == ["committed", "integrity_error"]
    finally:
        for session in sessions:
            session.close()
        for connection in connections:
            connection.close()
