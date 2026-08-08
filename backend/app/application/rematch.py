"""Rematch the quantity a recipient declined.

Two rules from docs/assumption_audit.md make this more than "run the allocation
again":

  C-3(b) the declining recipient is excluded from THIS donation's rematch, with
         a typed reason the UI displays;
  C-4    the new leg's origin is the DRIVER'S CURRENT LOCATION -- the declining
         community, where the driver is standing holding the food. The same
         driver is retained and there is no second store pickup. A store-origin
         default draws a phantom return trip to Mount Eden on the map.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.application.allocate_donation import (
    AllocateDonation,
    AllocationCommand,
    CandidateQuery,
)
from backend.app.contracts.core import (
    CandidateAssessment,
    DeliveryOrder,
    Location,
)
from backend.app.domain.errors import EligibilityError, ErrorCode
from backend.app.domain.policies.allocation import AllocationPlan, plan_allocation
from backend.app.domain.ports import UnitOfWork


@dataclass(frozen=True)
class RematchContext:
    """Everything the rematch needs that the declined order supplies."""

    donation_id: str
    declined_order_id: str
    declined_community_id: str
    driver_id: str
    # The driver's current location, which is the declined community's address.
    origin: Location
    remaining_kg: int


@dataclass(frozen=True)
class RematchProposal:
    context: RematchContext
    candidates: list[CandidateAssessment]
    plan: AllocationPlan


class RematchRemaining:
    """Re-assess alternatives for the remainder and commit the replacement leg."""

    def __init__(self, uow: UnitOfWork, allocator: AllocateDonation) -> None:
        self._uow = uow
        self._allocator = allocator

    def context_for(self, declined_order_id: str, remaining_kg: int) -> RematchContext:
        with self._uow as uow:
            order = uow.deliveries.get(declined_order_id)
            if order is None:
                raise EligibilityError(
                    ErrorCode.NOT_FOUND, f"Unknown delivery order {declined_order_id}"
                )
            community = uow.communities.get(order.destination_community_id)
            if community is None:
                raise EligibilityError(
                    ErrorCode.NOT_FOUND,
                    f"Unknown community {order.destination_community_id}",
                )
            acceptance = uow.acceptances.get(declined_order_id)
            if acceptance is None:
                raise EligibilityError(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    f"Delivery {declined_order_id} has no persisted acceptance to rematch",
                )
            if remaining_kg != acceptance.remaining_kg:
                raise EligibilityError(
                    ErrorCode.DUPLICATE_ALLOCATION,
                    f"Rematch requested {remaining_kg} kg but the persisted remainder is "
                    f"{acceptance.remaining_kg} kg",
                )
            return RematchContext(
                donation_id=order.donation_id,
                declined_order_id=order.order_id,
                declined_community_id=order.destination_community_id,
                driver_id=order.driver_id,
                origin=community.location,
                remaining_kg=acceptance.remaining_kg,
            )

    def propose(self, context: RematchContext) -> RematchProposal:
        """Assess every community from the driver's current position, then plan.

        The declining recipient keeps a full fact set -- its card still renders
        with an ETA -- but carries RECIPIENT_DECLINED_THIS_DONATION.
        """
        candidates = self._allocator.assess_candidates(
            CandidateQuery(
                donation_id=context.donation_id,
                required_kg=context.remaining_kg,
                origin=context.origin,
                declined_community_ids=(context.declined_community_id,),
            )
        )
        return RematchProposal(
            context=context,
            candidates=candidates,
            plan=plan_allocation(candidates, context.remaining_kg),
        )

    def execute(self, context: RematchContext, community_id: str) -> DeliveryOrder:
        """Create the replacement leg: same driver, origin at the declining recipient."""
        return self._allocator.execute(
            AllocationCommand(
                donation_id=context.donation_id,
                community_id=community_id,
                quantity_kg=context.remaining_kg,
                driver_id=context.driver_id,
                origin=context.origin,
                is_rematch=True,
                supersedes_order_id=context.declined_order_id,
            )
        )
