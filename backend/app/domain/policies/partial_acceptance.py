"""The declining-recipient rule.

Community A is reserved 60 kg, accepts 35 kg, and 25 kg returns to active
inventory. If the capacity reservation is released naively, A now shows free
capacity -- and A is the nearest candidate by definition, because the driver is
standing in its car park with zero travel time. A route-aware Agent may
re-select it, be declined again, and burn its step budget live on stage.

Two rules, both here:

  (a) Correct the recipient's declared maximum to the accepted quantity and
      leave zero remaining capacity. A becomes declared=35, remaining=0, not
      "declared=60 with 25 kg freed". The report was wrong, so correct it rather
      than merely unreserving.
  (b) Exclude the recipient from THIS donation's rematch, as a typed exclusion
      the UI can display -- which strengthens the pitch rather than hiding a
      workaround.

See docs/assumption_audit.md C-3.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.contracts.core import CommunityOrganisation, ExclusionReason
from backend.app.domain.errors import EligibilityError, ErrorCode
from backend.app.domain.policies.eligibility import DECLINED_THIS_DONATION_TEXT
from backend.app.domain.quantity import require_kilograms


@dataclass(frozen=True)
class PartialAcceptanceOutcome:
    """The arithmetic of one recipient's decision on arrival. Integer kilograms."""

    order_id: str
    community_id: str
    planned_kg: int
    accepted_kg: int
    remaining_kg: int
    # The recipient's corrected declared maximum and the capacity still free
    # after accepting the delivery. The user locked these as 35 and 0 for A.
    corrected_declared_capacity_kg: int
    corrected_remaining_capacity_kg: int

    @property
    def corrected_capacity_kg(self) -> int:
        """Compatibility name for P2 callers; means corrected declared capacity."""
        return self.corrected_declared_capacity_kg

    @property
    def requires_rematch(self) -> bool:
        return self.remaining_kg > 0

    @property
    def is_full_acceptance(self) -> bool:
        return self.remaining_kg == 0

    @property
    def is_rejection(self) -> bool:
        return self.accepted_kg == 0


def evaluate_acceptance(
    *,
    order_id: str,
    community_id: str,
    planned_kg: int,
    accepted_kg: int,
) -> PartialAcceptanceOutcome:
    """Compute accepted / remaining for one delivery. No I/O, no rounding."""
    planned_kg = require_kilograms(planned_kg, name="planned_kg", positive=True)
    try:
        accepted_kg = require_kilograms(accepted_kg, name="accepted_kg")
    except ValueError as error:
        raise EligibilityError(
            ErrorCode.RECIPIENT_CAPACITY_EXCEEDED,
            "Accepted quantity cannot be negative",
        ) from error
    if accepted_kg > planned_kg:
        raise EligibilityError(
            ErrorCode.RECIPIENT_CAPACITY_EXCEEDED,
            f"Accepted {accepted_kg} kg exceeds the planned {planned_kg} kg",
        )
    return PartialAcceptanceOutcome(
        order_id=order_id,
        community_id=community_id,
        planned_kg=planned_kg,
        accepted_kg=accepted_kg,
        remaining_kg=planned_kg - accepted_kg,
        corrected_declared_capacity_kg=accepted_kg,
        corrected_remaining_capacity_kg=0,
    )


def correct_declared_capacity(
    community: CommunityOrganisation,
    outcome: PartialAcceptanceOutcome,
) -> CommunityOrganisation:
    """Rule (a): the declared capacity becomes what the recipient actually took.

    This is a correction, not an unreservation. Returning the rejected 25 kg to
    A's capacity would leave A showing free capacity at zero travel distance --
    the exact condition that makes the Agent re-select it.
    """
    return community.model_copy(
        update={
            "declared_capacity_kg": outcome.corrected_declared_capacity_kg,
            "remaining_capacity_kg": outcome.corrected_remaining_capacity_kg,
        }
    )


def declined_exclusion() -> ExclusionReason:
    """Rule (b): the typed exclusion carried into this donation's rematch."""
    return ExclusionReason(
        code=ErrorCode.RECIPIENT_DECLINED_THIS_DONATION,
        display_text=DECLINED_THIS_DONATION_TEXT,
    )
