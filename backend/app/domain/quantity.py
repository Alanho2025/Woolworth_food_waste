"""Quantity handling for FoodFlow.

Quantities are **integer kilograms**, everywhere, without exception.

The entire product rests on one invariant:

    available + reserved + in_transit + delivered == donation_total

With IEEE-754 floats that invariant is not reliably decidable. The natural
implementation of "return the remainder to inventory" is subtraction, and the
reserve / release / re-reserve cycle can leave a residue that makes an
exactly-correct system report a violation, or an incorrect one pass silently.
AGENTS_FoodFlow.md 8.4 calls quantity integrity blocker-level, so its numeric
type is not an implementation detail.

See docs/phase_review_findings.md R-17.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, StrictInt

# Kilograms. Non-negative integers only.
Kilograms = Annotated[StrictInt, Field(ge=0, description="Whole kilograms")]

# Kilograms that must be strictly positive (a donated item, an allocation).
PositiveKilograms = Annotated[
    StrictInt,
    Field(gt=0, description="Whole kilograms, greater than zero"),
]


def require_kilograms(value: object, *, name: str, positive: bool = False) -> int:
    """Validate whole kilograms at non-Pydantic domain entry points.

    Python's ``bool`` subclasses ``int`` and arithmetic functions otherwise accept
    values such as ``True`` or ``60.0``. Contracts reject those through
    ``StrictInt``; pure policy functions use this guard to preserve the same
    boundary when called directly.
    """
    if type(value) is not int:
        raise TypeError(f"{name} must be a whole-number integer kilogram value")
    if value < 0 or (positive and value == 0):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{name} must be {qualifier}")
    return value
