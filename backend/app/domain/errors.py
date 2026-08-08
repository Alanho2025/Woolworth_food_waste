"""Typed failure codes.

Business outcomes are never determined by parsing exception message strings,
and a broad exception is never caught and turned into a success.
See clean_code_spec.md 6.3.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    """Expected, typed failures. Every one is a business outcome, not a crash."""

    # Eligibility — clean_code_spec 6.3
    RECIPIENT_CATEGORY_UNSUPPORTED = "RECIPIENT_CATEGORY_UNSUPPORTED"
    RECIPIENT_CAPACITY_EXCEEDED = "RECIPIENT_CAPACITY_EXCEEDED"
    STORAGE_INCOMPATIBLE = "STORAGE_INCOMPATIBLE"
    RECEIVING_WINDOW_CLOSED = "RECEIVING_WINDOW_CLOSED"
    DELIVERY_DEADLINE_MISSED = "DELIVERY_DEADLINE_MISSED"
    DRIVER_CAPACITY_EXCEEDED = "DRIVER_CAPACITY_EXCEEDED"
    DRIVER_UNAVAILABLE = "DRIVER_UNAVAILABLE"

    # A recipient that partially accepted is out of the running for the rest of
    # THIS donation. Without it the Agent may re-select the recipient it is
    # already standing at (zero travel distance, freshly freed capacity), be
    # declined again, and burn its step budget live on stage.
    # See docs/assumption_audit.md C-3.
    RECIPIENT_DECLINED_THIS_DONATION = "RECIPIENT_DECLINED_THIS_DONATION"

    # Quantity integrity — AGENTS_FoodFlow.md 8.4, blocker-level
    INSUFFICIENT_INVENTORY = "INSUFFICIENT_INVENTORY"
    DUPLICATE_ALLOCATION = "DUPLICATE_ALLOCATION"
    QUANTITY_INTEGRITY_VIOLATION = "QUANTITY_INTEGRITY_VIOLATION"

    # State machine
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"

    # Agent — clean_code_spec 6.3
    AGENT_OUTPUT_INVALID = "AGENT_OUTPUT_INVALID"
    AGENT_STEP_LIMIT_REACHED = "AGENT_STEP_LIMIT_REACHED"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"

    # Tool failure classes — AGENTS_FoodFlow.md 9 requires these be distinguishable
    TOOL_VALIDATION_FAILED = "TOOL_VALIDATION_FAILED"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_RATE_LIMITED = "TOOL_RATE_LIMITED"
    TOOL_INVALID_RESULT = "TOOL_INVALID_RESULT"
    TOOL_INTERNAL_FAILURE = "TOOL_INTERNAL_FAILURE"

    # Input
    DONATION_INVALID = "DONATION_INVALID"
    NOT_FOUND = "NOT_FOUND"


class FoodFlowError(Exception):
    """Base for every expected failure. Carries a code, never just a message."""

    def __init__(self, code: ErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class EligibilityError(FoodFlowError):
    """A recipient, driver, or route failed a hard constraint."""


class QuantityIntegrityError(FoodFlowError):
    """The quantity invariant was violated. Blocker-level; never suppressed."""


class StateTransitionError(FoodFlowError):
    """An illegal delivery-state transition was attempted."""


class AgentError(FoodFlowError):
    """The Agent loop failed, timed out, or produced unusable output."""
