"""Recipient capacity reservation.

Declared capacity is the organisation's latest stated maximum. Remaining
capacity is the unreserved portion of that declaration. Reserving A's initial
60 kg therefore changes only ``remaining_capacity_kg`` from 60 to 0.
"""

from __future__ import annotations

from backend.app.contracts.core import CommunityOrganisation
from backend.app.domain.policies.eligibility import validate_recipient_capacity


def reserve_recipient_capacity(
    community: CommunityOrganisation,
    quantity_kg: int,
) -> CommunityOrganisation:
    """Return a copy with the validated quantity removed from remaining capacity."""
    validate_recipient_capacity(community, quantity_kg)
    return community.model_copy(
        update={"remaining_capacity_kg": community.remaining_capacity_kg - quantity_kg}
    )
