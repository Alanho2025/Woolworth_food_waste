"""Persisted operational fact for one settled delivery confirmation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AcceptanceRecord:
    """The immutable quantities originally confirmed for one delivery order."""

    order_id: str
    donation_id: str
    community_id: str
    planned_kg: int
    accepted_kg: int
    remaining_kg: int
    reason: str
    recorded_at: datetime
