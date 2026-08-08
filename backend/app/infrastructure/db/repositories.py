"""SQLite repositories.

Every class here implements a Protocol from `backend/app/domain/ports.py`.

Two rules are absolute in this module:

* **No SQLAlchemy row ever leaves it.** Rows are translated into the frozen
  Pydantic contracts of `contracts/core.py` before returning, so persistence
  shape and API shape can diverge freely (clean_code_spec 4, 9).
* **Reads never write.** No `get`/`list` method creates, mutates, or lazily
  backfills anything (clean_code_spec 5.2).

Repositories do not commit. The transaction boundary belongs to the application
layer through the UnitOfWork (clean_code_spec 6.2). The one deliberate exception
is `record_failure`, which commits on its own connection — see its docstring.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.contracts.core import (
    AgentRun,
    AgentState,
    AgentStateEvent,
    AuditEvent,
    CommunityNeed,
    CommunityOrganisation,
    DeliveryOrder,
    DeliveryStatus,
    DonationInventory,
    DonationRequest,
    Driver,
    FoodCategory,
    FoodItem,
    Location,
    NeedLevel,
    RouteLeg,
    StorageType,
    TimeWindow,
)
from backend.app.domain.acceptance import AcceptanceRecord
from backend.app.domain.errors import ErrorCode, FoodFlowError
from backend.app.infrastructure.db.models import (
    AgentRunEventRow,
    AgentRunRow,
    AuditEventRow,
    CommunityCategoryRow,
    CommunityNeedRow,
    CommunityRow,
    CommunityStorageRow,
    DeliveryOrderRow,
    DonationInventoryRow,
    DonationItemRow,
    DonationRow,
    DriverRow,
    PartialAcceptanceRow,
)
from backend.app.infrastructure.db.session import SessionFactory

# --------------------------------------------------------------------------
# Row -> contract translation
# --------------------------------------------------------------------------


def _to_donation(row: DonationRow, item_rows: Sequence[DonationItemRow]) -> DonationRequest:
    kilogram_unit: Literal["kg"] = "kg"
    for item in item_rows:
        if item.unit != kilogram_unit:
            raise FoodFlowError(
                ErrorCode.DONATION_INVALID,
                f"persisted donation {row.donation_id} has unsupported unit {item.unit!r}",
            )
    return DonationRequest(
        donation_id=row.donation_id,
        store_id=row.store_id,
        store_location=Location(
            name=row.store_name,
            latitude=row.store_latitude,
            longitude=row.store_longitude,
        ),
        pickup_window=TimeWindow(start=row.pickup_window_start, end=row.pickup_window_end),
        items=[
            FoodItem(
                item_name=item.item_name,
                category=FoodCategory(item.category),
                quantity=item.quantity_kg,
                unit=kilogram_unit,
                storage_type=StorageType(item.storage_type),
                delivery_deadline=item.delivery_deadline,
            )
            for item in item_rows
        ],
        handling_notes=row.handling_notes,
    )


def _to_community(
    row: CommunityRow,
    category_rows: Sequence[CommunityCategoryRow],
    storage_rows: Sequence[CommunityStorageRow],
    need_rows: Sequence[CommunityNeedRow],
) -> CommunityOrganisation:
    return CommunityOrganisation(
        community_id=row.community_id,
        name=row.name,
        location=Location(
            name=row.location_name,
            latitude=row.latitude,
            longitude=row.longitude,
        ),
        accepted_categories=[FoodCategory(c.category) for c in category_rows],
        supported_storage=[StorageType(s.storage_type) for s in storage_rows],
        needs=[
            CommunityNeed(category=FoodCategory(n.category), level=NeedLevel(n.level))
            for n in need_rows
        ],
        declared_capacity_kg=row.declared_capacity_kg,
        remaining_capacity_kg=row.remaining_capacity_kg,
        receiving_window=TimeWindow(start=row.receiving_window_start, end=row.receiving_window_end),
        is_open=row.is_open,
    )


def _to_driver(row: DriverRow) -> Driver:
    return Driver(
        driver_id=row.driver_id,
        name=row.name,
        start_location=Location(
            name=row.start_location_name,
            latitude=row.start_latitude,
            longitude=row.start_longitude,
        ),
        vehicle_capacity_kg=row.vehicle_capacity_kg,
        is_available=row.is_available,
    )


def _to_delivery_order(row: DeliveryOrderRow) -> DeliveryOrder:
    origin = Location(
        name=row.origin_name,
        latitude=row.origin_latitude,
        longitude=row.origin_longitude,
    )
    route = RouteLeg(
        origin=origin,
        destination=Location(
            name=row.route_destination_name,
            latitude=row.route_destination_latitude,
            longitude=row.route_destination_longitude,
        ),
        polyline=[(point[0], point[1]) for point in row.route_polyline],
        distance_km=row.route_distance_km,
        duration_minutes=row.route_duration_minutes,
        eta=row.route_eta,
        simulated=row.route_simulated,
    )
    return DeliveryOrder(
        order_id=row.order_id,
        donation_id=row.donation_id,
        origin=origin,
        destination_community_id=row.destination_community_id,
        quantity_kg=row.quantity_kg,
        driver_id=row.driver_id,
        route=route,
        status=DeliveryStatus(row.status),
        deadline=row.deadline,
        is_rematch=row.is_rematch,
    )


def _delivery_order_values(order: DeliveryOrder) -> dict[str, object]:
    """Flatten a DeliveryOrder into the denormalised row columns."""
    return {
        "order_id": order.order_id,
        "donation_id": order.donation_id,
        "origin_name": order.origin.name,
        "origin_latitude": order.origin.latitude,
        "origin_longitude": order.origin.longitude,
        "destination_community_id": order.destination_community_id,
        "quantity_kg": order.quantity_kg,
        "driver_id": order.driver_id,
        "status": order.status.value,
        "deadline": order.deadline,
        "is_rematch": order.is_rematch,
        "route_destination_name": order.route.destination.name,
        "route_destination_latitude": order.route.destination.latitude,
        "route_destination_longitude": order.route.destination.longitude,
        "route_polyline": [[lat, lon] for lat, lon in order.route.polyline],
        "route_distance_km": order.route.distance_km,
        "route_duration_minutes": order.route.duration_minutes,
        "route_eta": order.route.eta,
        "route_simulated": order.route.simulated,
    }


# --------------------------------------------------------------------------
# Repositories
# --------------------------------------------------------------------------


class SqlAlchemyDonationRepository:
    """Donations and their quantity ledger."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, donation_id: str) -> DonationRequest | None:
        row = self._session.get(DonationRow, donation_id)
        if row is None:
            return None
        item_rows = list(
            self._session.scalars(
                select(DonationItemRow)
                .where(DonationItemRow.donation_id == donation_id)
                .order_by(DonationItemRow.ordinal)
            )
        )
        return _to_donation(row, item_rows)

    def add(self, donation: DonationRequest) -> None:
        self._session.merge(
            DonationRow(
                donation_id=donation.donation_id,
                store_id=donation.store_id,
                store_name=donation.store_location.name,
                store_latitude=donation.store_location.latitude,
                store_longitude=donation.store_location.longitude,
                pickup_window_start=donation.pickup_window.start,
                pickup_window_end=donation.pickup_window.end,
                handling_notes=donation.handling_notes,
            )
        )
        self._session.execute(
            delete(DonationItemRow).where(DonationItemRow.donation_id == donation.donation_id)
        )
        self._session.flush()
        for ordinal, item in enumerate(donation.items):
            self._session.add(
                DonationItemRow(
                    donation_id=donation.donation_id,
                    ordinal=ordinal,
                    item_name=item.item_name,
                    category=item.category.value,
                    quantity_kg=item.quantity,
                    unit=item.unit,
                    storage_type=item.storage_type.value,
                    delivery_deadline=item.delivery_deadline,
                )
            )

    def get_inventory(self, donation_id: str) -> DonationInventory | None:
        row = self._session.get(DonationInventoryRow, donation_id)
        if row is None:
            return None
        return DonationInventory(
            donation_id=row.donation_id,
            total_kg=row.total_kg,
            available_kg=row.available_kg,
            reserved_kg=row.reserved_kg,
            in_transit_kg=row.in_transit_kg,
            delivered_kg=row.delivered_kg,
        )

    def save_inventory(self, inventory: DonationInventory) -> None:
        """Persist the ledger.

        The balance check is re-asserted here as a last line of defence. The
        invariant is a domain rule, but AGENTS_FoodFlow.md 8.4 calls quantity
        integrity blocker-level, and a repository that will happily write an
        unbalanced ledger is one unnoticed caller away from a demo that reports
        more food delivered than was donated.
        """
        if not inventory.is_balanced:
            raise FoodFlowError(
                ErrorCode.QUANTITY_INTEGRITY_VIOLATION,
                f"inventory for {inventory.donation_id} does not sum to {inventory.total_kg} kg",
            )
        self._session.merge(
            DonationInventoryRow(
                donation_id=inventory.donation_id,
                total_kg=inventory.total_kg,
                available_kg=inventory.available_kg,
                reserved_kg=inventory.reserved_kg,
                in_transit_kg=inventory.in_transit_kg,
                delivered_kg=inventory.delivered_kg,
            )
        )


class SqlAlchemyCommunityRepository:
    """Community organisations, their capacity, and their needs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[CommunityOrganisation]:
        rows = list(self._session.scalars(select(CommunityRow).order_by(CommunityRow.community_id)))
        return [self._hydrate(row) for row in rows]

    def get(self, community_id: str) -> CommunityOrganisation | None:
        row = self._session.get(CommunityRow, community_id)
        if row is None:
            return None
        return self._hydrate(row)

    def save(self, community: CommunityOrganisation) -> None:
        self._session.merge(
            CommunityRow(
                community_id=community.community_id,
                name=community.name,
                location_name=community.location.name,
                latitude=community.location.latitude,
                longitude=community.location.longitude,
                declared_capacity_kg=community.declared_capacity_kg,
                remaining_capacity_kg=community.remaining_capacity_kg,
                receiving_window_start=community.receiving_window.start,
                receiving_window_end=community.receiving_window.end,
                is_open=community.is_open,
            )
        )
        community_id = community.community_id
        self._session.execute(
            delete(CommunityCategoryRow).where(CommunityCategoryRow.community_id == community_id)
        )
        self._session.execute(
            delete(CommunityStorageRow).where(CommunityStorageRow.community_id == community_id)
        )
        self._session.execute(
            delete(CommunityNeedRow).where(CommunityNeedRow.community_id == community_id)
        )
        self._session.flush()
        for ordinal, category in enumerate(community.accepted_categories):
            self._session.add(
                CommunityCategoryRow(
                    community_id=community_id, ordinal=ordinal, category=category.value
                )
            )
        for ordinal, storage in enumerate(community.supported_storage):
            self._session.add(
                CommunityStorageRow(
                    community_id=community_id, ordinal=ordinal, storage_type=storage.value
                )
            )
        for ordinal, need in enumerate(community.needs):
            self._session.add(
                CommunityNeedRow(
                    community_id=community_id,
                    ordinal=ordinal,
                    category=need.category.value,
                    level=need.level.value,
                )
            )

    def _hydrate(self, row: CommunityRow) -> CommunityOrganisation:
        community_id = row.community_id
        categories = list(
            self._session.scalars(
                select(CommunityCategoryRow)
                .where(CommunityCategoryRow.community_id == community_id)
                .order_by(CommunityCategoryRow.ordinal)
            )
        )
        storage = list(
            self._session.scalars(
                select(CommunityStorageRow)
                .where(CommunityStorageRow.community_id == community_id)
                .order_by(CommunityStorageRow.ordinal)
            )
        )
        needs = list(
            self._session.scalars(
                select(CommunityNeedRow)
                .where(CommunityNeedRow.community_id == community_id)
                .order_by(CommunityNeedRow.ordinal)
            )
        )
        return _to_community(row, categories, storage, needs)


class SqlAlchemyDriverRepository:
    """Delivery drivers and their vehicle capacity."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_available(self) -> list[Driver]:
        rows = self._session.scalars(
            select(DriverRow).where(DriverRow.is_available.is_(True)).order_by(DriverRow.driver_id)
        )
        return [_to_driver(row) for row in rows]

    def get(self, driver_id: str) -> Driver | None:
        row = self._session.get(DriverRow, driver_id)
        if row is None:
            return None
        return _to_driver(row)

    def save(self, driver: Driver) -> None:
        self._session.merge(
            DriverRow(
                driver_id=driver.driver_id,
                name=driver.name,
                start_location_name=driver.start_location.name,
                start_latitude=driver.start_location.latitude,
                start_longitude=driver.start_location.longitude,
                vehicle_capacity_kg=driver.vehicle_capacity_kg,
                is_available=driver.is_available,
            )
        )


class SqlAlchemyDeliveryRepository:
    """Delivery orders, including rematched legs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, order: DeliveryOrder) -> None:
        self._session.add(DeliveryOrderRow(**_delivery_order_values(order)))

    def get(self, order_id: str) -> DeliveryOrder | None:
        row = self._session.get(DeliveryOrderRow, order_id)
        if row is None:
            return None
        return _to_delivery_order(row)

    def list_for_donation(self, donation_id: str) -> list[DeliveryOrder]:
        rows = self._session.scalars(
            select(DeliveryOrderRow)
            .where(DeliveryOrderRow.donation_id == donation_id)
            .order_by(DeliveryOrderRow.order_id)
        )
        return [_to_delivery_order(row) for row in rows]

    def save(self, order: DeliveryOrder) -> None:
        self._session.merge(DeliveryOrderRow(**_delivery_order_values(order)))


class SqlAlchemyAcceptanceRepository:
    """Original recipient confirmations, keyed one-to-one by delivery order."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, order_id: str) -> AcceptanceRecord | None:
        row = self._session.get(PartialAcceptanceRow, order_id)
        if row is None:
            return None
        return AcceptanceRecord(
            order_id=row.order_id,
            donation_id=row.donation_id,
            community_id=row.community_id,
            planned_kg=row.planned_kg,
            accepted_kg=row.accepted_kg,
            remaining_kg=row.remaining_kg,
            reason=row.reason,
            recorded_at=row.recorded_at,
        )

    def add(self, record: AcceptanceRecord) -> None:
        self._session.add(
            PartialAcceptanceRow(
                order_id=record.order_id,
                donation_id=record.donation_id,
                community_id=record.community_id,
                planned_kg=record.planned_kg,
                accepted_kg=record.accepted_kg,
                remaining_kg=record.remaining_kg,
                reason=record.reason,
                recorded_at=record.recorded_at,
            )
        )


class SqlAlchemyAgentRunRepository:
    """Agent runs and their incrementally appended visible states."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, run_id: str, donation_id: str) -> None:
        self._session.add(
            AgentRunRow(run_id=run_id, donation_id=donation_id, is_complete=False, error_code=None)
        )

    def append_event(self, run_id: str, event: AgentStateEvent) -> None:
        self._session.add(
            AgentRunEventRow(
                run_id=run_id,
                sequence=event.sequence,
                state=event.state.value,
                label=event.label,
                detail=event.detail,
                occurred_at=event.occurred_at,
            )
        )

    def get(self, run_id: str) -> AgentRun | None:
        row = self._session.get(AgentRunRow, run_id)
        if row is None:
            return None
        event_rows = self._session.scalars(
            select(AgentRunEventRow)
            .where(AgentRunEventRow.run_id == run_id)
            .order_by(AgentRunEventRow.sequence)
        )
        return AgentRun(
            run_id=row.run_id,
            donation_id=row.donation_id,
            events=[
                AgentStateEvent(
                    sequence=event.sequence,
                    state=AgentState(event.state),
                    label=event.label,
                    detail=event.detail,
                    occurred_at=event.occurred_at,
                )
                for event in event_rows
            ],
            is_complete=row.is_complete,
            error_code=ErrorCode(row.error_code) if row.error_code is not None else None,
        )

    def complete(self, run_id: str, error_code: str | None = None) -> None:
        row = self._session.get(AgentRunRow, run_id)
        if row is None:
            raise FoodFlowError(ErrorCode.NOT_FOUND, f"agent run {run_id} does not exist")
        row.is_complete = True
        row.error_code = error_code


class SqlAlchemyAuditRepository:
    """Audit trail.

    Successes are written inside the caller's transaction; failures are not.
    See `record_failure`.
    """

    def __init__(self, session: Session, session_factory: SessionFactory) -> None:
        self._session = session
        self._session_factory = session_factory

    def record(self, event: AuditEvent) -> None:
        self._session.add(_audit_row(event))

    def record_failure(self, event: AuditEvent) -> None:
        """Write a failure audit on its own connection, and commit it there.

        clean_code_spec 6.2 lists "create audit event" as step 6 of the
        allocation transaction and requires the whole transaction to roll back
        on failure. Taken literally that rolls back the audit record of the
        failed attempt, destroying exactly the evidence AGENTS_FoodFlow.md 14
        requires for diagnosis. A separate session survives the caller's
        rollback. See docs/phase_review_findings.md R-10 and Q6.
        """
        with self._session_factory() as session:
            session.add(_audit_row(event))
            session.commit()


def _audit_row(event: AuditEvent) -> AuditEventRow:
    return AuditEventRow(
        event_id=event.event_id,
        donation_id=event.donation_id,
        action=event.action,
        detail=event.detail,
        occurred_at=event.occurred_at,
        succeeded=event.succeeded,
    )
