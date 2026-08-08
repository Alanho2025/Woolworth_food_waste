"""The seam between the test suite and the domain policies under test.

WHY THIS EXISTS
---------------
The domain policies, the persistence layer, the agent layer and this test suite
are being built concurrently. A test may therefore reference a module that does
not exist yet. The rule (AGENTS_FoodFlow.md 13, foodflow_clean_code_spec.md
10.2) is that a test is never deleted and never weakened to go green — so a test
whose subject has not landed yet SKIPS with an exact reason naming what it
looked for, and the assertions below it stay untouched.

This module is the ONE place that names the expected domain API. If an
implementer chooses different names, only this file changes.

WHAT THIS MODULE MUST NEVER DO
------------------------------
It must never supply a fallback implementation of a rule. Mocks may isolate
DeepSeek, the clock, and routing; they must not replace the allocation,
capacity, or eligibility policy being tested (10.2). Everything here either
resolves the real callable or skips.
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from types import ModuleType
from typing import Any

import pytest

# Expected module paths, from docs/implementation_phases.md P1 "Files added".
ELIGIBILITY = "backend.app.domain.policies.eligibility"
ALLOCATION = "backend.app.domain.policies.allocation"
PARTIAL_ACCEPTANCE = "backend.app.domain.policies.partial_acceptance"
QUANTITY_INTEGRITY = "backend.app.domain.policies.quantity_integrity"
ROUTING = "backend.app.domain.routing"
DELIVERY_STATE = "backend.app.domain.delivery_state"


def require_module(dotted: str) -> ModuleType:
    """Import a module, or skip with a reason naming the missing module."""
    try:
        return importlib.import_module(dotted)
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on build order
        if exc.name is not None and not dotted.startswith(exc.name):
            raise
        pytest.skip(f"not implemented yet: module {dotted} (docs/implementation_phases.md P1)")


def require_callable(dotted: str, *names: str) -> Any:
    """Return the first attribute of `dotted` named in `names`, or skip.

    Skipping — rather than substituting a stub — keeps the assertion in the test
    body honest: the day the policy lands, the test runs against the real rule.
    """
    module = require_module(dotted)
    for name in names:
        candidate = getattr(module, name, None)
        if callable(candidate):
            return candidate
    pytest.skip(
        f"not implemented yet: {dotted} defines none of {list(names)} "
        f"(present: {sorted(n for n in vars(module) if not n.startswith('_'))})"
    )


def _call(func: Any, kwargs: dict[str, Any], positional: Sequence[Any]) -> Any:
    """Call `func` by keyword, falling back to positional order.

    A signature that matches neither shape FAILS the test loudly. It does not
    skip: the module exists, so a mismatch is a real integration defect between
    the policy and its contract, and hiding it behind a skip would be exactly
    the kind of silently-green suite clean_code_spec 10.2 forbids.
    """
    try:
        return func(**kwargs)
    except TypeError as keyword_error:
        try:
            return func(*positional)
        except TypeError as positional_error:
            pytest.fail(
                f"{getattr(func, '__module__', '?')}.{getattr(func, '__name__', func)!r} "
                f"accepts neither the keyword form {sorted(kwargs)} "
                f"({keyword_error}) nor the positional form of length "
                f"{len(positional)} ({positional_error})"
            )


# --------------------------------------------------------------------------
# Policy adapters
#
# Each adapter names the ONE expected entry point plus the aliases an
# implementer might plausibly have chosen. The output types are NOT guessed:
# they are fixed by `backend/app/contracts/core.py`, which is authority. So a
# test asserts on `CandidateAssessment.capacity_sufficient` rather than on some
# invented return shape, and only the function name and argument order are soft.
# --------------------------------------------------------------------------


def assess_candidates(
    *,
    donation: Any,
    communities: Any,
    clock: Any,
    quantity_kg: int | None = None,
) -> list[Any]:
    """Fact-gathering pass -> one `CandidateAssessment` per community.

    R-18: every displayable fact is computed for EVERY candidate, including ones
    that already failed a hard constraint. Eligibility is a label over a
    complete fact set, never an early return.
    """
    eligibility = require_module(ELIGIBILITY)
    request_type = eligibility.AssessmentRequest
    func = eligibility.assess_candidates
    routing = require_module(ROUTING)
    simulator_type = routing.DeterministicRouteSimulator
    item = donation.items[0]
    request = request_type(
        origin=donation.store_location,
        category=item.category,
        storage_type=item.storage_type,
        required_kg=item.quantity if quantity_kg is None else quantity_kg,
        delivery_deadline=item.delivery_deadline,
        now=clock.now(),
    )
    return list(func(request, list(communities), simulator_type(clock)))


def assess_one(*, donation: Any, community: Any, clock: Any, quantity_kg: int | None = None) -> Any:
    """The single `CandidateAssessment` for one community."""
    assessments = assess_candidates(
        donation=donation, communities=[community], clock=clock, quantity_kg=quantity_kg
    )
    assert len(assessments) == 1, (
        f"the fact-gathering pass returned {len(assessments)} assessments for one community; "
        "R-18 requires exactly one complete fact set per candidate, including excluded ones"
    )
    return assessments[0]


def select_allocation(
    *,
    donation: Any,
    quantity_kg: int,
    communities: Any,
    drivers: Any,
    clock: Any,
    excluded_community_ids: Sequence[str] = (),
) -> Any:
    """Single-destination allocation -> an `AllocationDecision`.

    docs/assumption_audit.md C-2: prefer one destination for the full remaining
    quantity; split only when no single feasible recipient can accept the whole
    remainder. Python-enforced, never a prompt hint (clean_code_spec 2.3).
    """
    func = require_callable(
        ALLOCATION,
        "select_allocation",
        "allocate",
        "allocate_donation",
        "choose_allocation",
        "select_destination",
    )
    return _call(
        func,
        {
            "donation": donation,
            "quantity_kg": quantity_kg,
            "communities": communities,
            "drivers": drivers,
            "clock": clock,
            "excluded_community_ids": list(excluded_community_ids),
        },
        (donation, quantity_kg, communities, drivers, clock, list(excluded_community_ids)),
    )


def apply_partial_acceptance(*, inventory: Any, accepted_kg: int, planned_kg: int) -> Any:
    """Partial acceptance -> the updated `DonationInventory` (or a result carrying it)."""
    func = require_callable(
        PARTIAL_ACCEPTANCE,
        "apply_partial_acceptance",
        "record_partial_acceptance",
        "partial_acceptance",
        "accept_partial",
    )
    return _call(
        func,
        {"inventory": inventory, "accepted_kg": accepted_kg, "planned_kg": planned_kg},
        (inventory, accepted_kg, planned_kg),
    )


def assert_quantity_integrity(inventory: Any) -> Any:
    """The blocker-level invariant -> raises `QuantityIntegrityError` when violated.

    AGENTS_FoodFlow.md 8.4 / docs/assumption_audit.md C-7: asserted at every
    transition, not merely tested on one path.
    """
    func = require_callable(
        QUANTITY_INTEGRITY,
        "assert_quantity_integrity",
        "assert_balanced",
        "check_quantity_integrity",
        "verify_integrity",
        "assert_integrity",
    )
    return _call(func, {"inventory": inventory}, (inventory,))


def reserve(*, inventory: Any, quantity_kg: int) -> Any:
    """Move `quantity_kg` from available to reserved, refusing a duplicate allocation."""
    func = require_callable(
        QUANTITY_INTEGRITY,
        "reserve",
        "reserve_quantity",
        "reserve_inventory",
    )
    return _call(
        func, {"inventory": inventory, "quantity_kg": quantity_kg}, (inventory, quantity_kg)
    )


def simulate_route(*, origin: Any, destination: Any, departure: Any) -> Any:
    """Deterministic simulated route -> a `RouteLeg` carrying `simulated=True`."""
    func = require_callable(
        ROUTING,
        "simulate_route",
        "calculate_route",
        "route",
        "build_route",
    )
    return _call(
        func,
        {"origin": origin, "destination": destination, "departure": departure},
        (origin, destination, departure),
    )
