"""The operations-dashboard read model.

Requirement.md 3 asks the opening screen to read as an active coordination
system rather than a reporting page, and clean_code_spec 8.4 requires the four
ledger components to be *visible* so "no quantity was duplicated" is proven on
screen rather than asserted in a test.

This is a query-only use case: it performs no writes and holds no state.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.contracts.core import (
    CommunityOrganisation,
    DeliveryOrder,
    DeliveryStatus,
    DonationInventory,
    DonationRequest,
    Driver,
)
from backend.app.domain.acceptance import AcceptanceRecord
from backend.app.domain.errors import EligibilityError, ErrorCode
from backend.app.domain.ports import UnitOfWork

_IN_TRANSIT_STATUSES = frozenset(
    {DeliveryStatus.DRIVER_ASSIGNED, DeliveryStatus.IN_TRANSIT, DeliveryStatus.ARRIVED}
)


class CapacityAlert(BaseModel):
    """One community whose declared capacity was corrected mid-journey (C-3a)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    community_id: str
    community_name: str
    corrected_capacity_kg: int
    planned_kg: int
    accepted_kg: int
    message: str


class DashboardSnapshot(BaseModel):
    """Everything Screen 1 renders, scoped to one donation.

    Scoped deliberately: the integrity bar must sum to exactly this donation's
    total, and folding in unrelated in-flight deliveries would make the 60 kg
    proof ambiguous. See docs/phase_review_findings.md R-26.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    donation: DonationRequest
    inventory: DonationInventory
    deliveries: list[DeliveryOrder]
    communities: list[CommunityOrganisation]
    drivers: list[Driver]
    capacity_alerts: list[CapacityAlert]

    @property
    def in_transit_deliveries(self) -> list[DeliveryOrder]:
        return [d for d in self.deliveries if d.status in _IN_TRANSIT_STATUSES]


class DashboardView:
    """Assemble the dashboard snapshot for one donation."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def snapshot(self, donation_id: str) -> DashboardSnapshot:
        with self._uow as uow:
            donation = uow.donations.get(donation_id)
            inventory = uow.donations.get_inventory(donation_id)
            if donation is None or inventory is None:
                raise EligibilityError(ErrorCode.NOT_FOUND, f"Unknown donation {donation_id}")

            communities = uow.communities.list_all()
            deliveries = uow.deliveries.list_for_donation(donation_id)
            by_id = {c.community_id: c for c in communities}
            acceptances = {
                order.order_id: uow.acceptances.get(order.order_id) for order in deliveries
            }

            return DashboardSnapshot(
                donation=donation,
                inventory=inventory,
                deliveries=deliveries,
                communities=communities,
                drivers=uow.drivers.list_all(),
                capacity_alerts=[
                    _alert(
                        order,
                        by_id[order.destination_community_id],
                        acceptances[order.order_id],
                    )
                    for order in deliveries
                    if order.status is DeliveryStatus.PARTIALLY_ACCEPTED
                    and order.destination_community_id in by_id
                    and acceptances[order.order_id] is not None
                ],
            )


def _alert(
    order: DeliveryOrder,
    community: CommunityOrganisation,
    acceptance: AcceptanceRecord | None,
) -> CapacityAlert:
    if acceptance is None:
        raise EligibilityError(
            ErrorCode.NOT_FOUND,
            f"Partial delivery {order.order_id} has no acceptance record",
        )
    accepted = acceptance.accepted_kg
    return CapacityAlert(
        community_id=community.community_id,
        community_name=community.name,
        corrected_capacity_kg=accepted,
        planned_kg=order.quantity_kg,
        accepted_kg=accepted,
        message=(
            f"{community.name} corrected its declared capacity to {accepted} kg "
            f"after accepting {accepted} of {order.quantity_kg} kg"
        ),
    )
