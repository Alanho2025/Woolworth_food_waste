"""SQLAlchemy models for the FoodFlow domain."""

from backend.app.models.base import Base
from backend.app.models.matching import (
    Allocation,
    AllocationStatusEvent,
    MatchCandidate,
    MatchDecision,
    MatchRun,
    confirmed_allocation_statement,
)
from backend.app.models.organisation import Organisation, OrganisationRole
from backend.app.models.recipient import (
    RecipientAvailabilitySnapshot,
    RecipientCapability,
    RecipientNeed,
    current_recipient_availability_statement,
    public_recipient_availability_statement,
)
from backend.app.models.route import (
    Delivery,
    DeliveryAllocation,
    DeliveryStatusEvent,
    DeliveryStop,
    RouteDecision,
    RouteInputSnapshot,
    RoutePlanningRun,
    RouteProposal,
    confirmed_delivery_statement,
)
from backend.app.models.site import Site, SiteLocation, navigation_location_statement
from backend.app.models.source import (
    FoodProduct,
    ImportBatch,
    SourceRecord,
    source_record_identity_statement,
)
from backend.app.models.supply import (
    Donation,
    DonationItem,
    DonationStatusEvent,
    FoodConditionObservation,
)
from backend.app.models.user import OrganisationMembership, User, active_membership_statement

__all__ = [
    "Allocation",
    "AllocationStatusEvent",
    "Base",
    "Delivery",
    "DeliveryAllocation",
    "DeliveryStatusEvent",
    "DeliveryStop",
    "Donation",
    "DonationItem",
    "DonationStatusEvent",
    "FoodConditionObservation",
    "FoodProduct",
    "ImportBatch",
    "MatchCandidate",
    "MatchDecision",
    "MatchRun",
    "Organisation",
    "OrganisationMembership",
    "OrganisationRole",
    "RecipientAvailabilitySnapshot",
    "RecipientCapability",
    "RecipientNeed",
    "RouteDecision",
    "RouteInputSnapshot",
    "RoutePlanningRun",
    "RouteProposal",
    "Site",
    "SiteLocation",
    "SourceRecord",
    "User",
    "active_membership_statement",
    "confirmed_allocation_statement",
    "confirmed_delivery_statement",
    "current_recipient_availability_statement",
    "navigation_location_statement",
    "public_recipient_availability_statement",
    "source_record_identity_statement",
]
