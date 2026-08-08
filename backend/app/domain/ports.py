"""Ports.

Protocols the domain and application layers depend on, implemented by
infrastructure adapters. This is what keeps the dependency arrow pointing
inward (clean_code_spec 2.2) and lets persistence and policy be built in
parallel against one agreed shape.

Domain code must not import FastAPI, SQLAlchemy, Google ADK, DeepSeek SDKs,
React, or browser APIs. `backend/tests/test_architecture.py` enforces it.
"""

from __future__ import annotations

from typing import Protocol

from backend.app.contracts.core import (
    AgentRun,
    AgentStateEvent,
    AuditEvent,
    CommunityOrganisation,
    DeliveryOrder,
    DonationInventory,
    DonationRequest,
    Driver,
    Location,
    RouteLeg,
)
from backend.app.domain.acceptance import AcceptanceRecord


class DonationRepository(Protocol):
    def get(self, donation_id: str) -> DonationRequest | None: ...
    def list_all(self) -> list[DonationRequest]: ...
    def add(self, donation: DonationRequest) -> None: ...
    def get_inventory(self, donation_id: str) -> DonationInventory | None: ...
    def list_inventories(self) -> list[DonationInventory]: ...
    def save_inventory(self, inventory: DonationInventory) -> None: ...


class CommunityRepository(Protocol):
    def list_all(self) -> list[CommunityOrganisation]: ...
    def get(self, community_id: str) -> CommunityOrganisation | None: ...
    def save(self, community: CommunityOrganisation) -> None: ...


class DriverRepository(Protocol):
    def list_all(self) -> list[Driver]: ...
    def list_available(self) -> list[Driver]: ...
    def get(self, driver_id: str) -> Driver | None: ...
    def save(self, driver: Driver) -> None: ...


class DeliveryRepository(Protocol):
    def add(self, order: DeliveryOrder) -> None: ...
    def get(self, order_id: str) -> DeliveryOrder | None: ...
    def list_for_donation(self, donation_id: str) -> list[DeliveryOrder]: ...
    def list_all(self) -> list[DeliveryOrder]: ...
    def save(self, order: DeliveryOrder) -> None: ...


class AcceptanceRepository(Protocol):
    def get(self, order_id: str) -> AcceptanceRecord | None: ...
    def add(self, record: AcceptanceRecord) -> None: ...


class AgentRunRepository(Protocol):
    def create(self, run_id: str, donation_id: str) -> None: ...
    def append_event(self, run_id: str, event: AgentStateEvent) -> None: ...
    def get(self, run_id: str) -> AgentRun | None: ...
    def complete(self, run_id: str, error_code: str | None = None) -> None: ...


class AuditRepository(Protocol):
    def record(self, event: AuditEvent) -> None: ...

    def record_failure(self, event: AuditEvent) -> None:
        """Write a failure audit OUTSIDE the caller's transaction.

        clean_code_spec 6.2 lists "create audit event" as step 6 of the
        allocation transaction, and requires the whole transaction to roll back
        on failure. Taken literally that rolls back the audit record of the
        failed attempt, destroying exactly the evidence AGENTS_FoodFlow.md 14
        requires for diagnosis. Failures are therefore recorded on a separate
        connection. See docs/phase_review_findings.md R-10.
        """
        ...


class RouteSimulator(Protocol):
    def route(self, origin: Location, destination: Location) -> RouteLeg:
        """Deterministic simulated route. Never presented as real routing."""
        ...


class UnitOfWork(Protocol):
    """Transaction boundary. Owned by the application layer (clean_code_spec 6.2)."""

    donations: DonationRepository
    communities: CommunityRepository
    drivers: DriverRepository
    deliveries: DeliveryRepository
    acceptances: AcceptanceRepository
    agent_runs: AgentRunRepository
    audit: AuditRepository

    def __enter__(self) -> UnitOfWork: ...
    def __exit__(self, *args: object) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
