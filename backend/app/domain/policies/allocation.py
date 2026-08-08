"""Single-destination allocation policy.

Prefer ONE destination for the full remaining quantity. Split only when NO
single feasible recipient can accept the entire remainder.

This is enforced in Python and is never a prompt hint. AGENTS_FoodFlow.md 7
explicitly says DeepSeek "decides whether to split or rematch", and a
well-reasoning model given 25 kg to place, with Community C offering 10 kg and
Community D offering 30 kg, may allocate 10 kg to C and 15 kg to D. That
delivers all 60 kg, satisfies every hard constraint, and is arguably a better
answer -- and it destroys the scripted "Community C excluded" beat that
Requirement.md 8 and 16.3 depend on. clean_code_spec 2.3 forbids the Agent
making final product policy, so the rule lives here.

See docs/assumption_audit.md C-2.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.contracts.core import (
    CandidateAssessment,
    CandidateStatus,
    NeedLevel,
)
from backend.app.domain.errors import ErrorCode
from backend.app.domain.quantity import require_kilograms

# Urgency ranking used to break ties between feasible recipients. Higher wins.
_NEED_RANK: dict[NeedLevel, int] = {
    NeedLevel.NONE: 0,
    NeedLevel.LOW: 1,
    NeedLevel.MEDIUM: 2,
    NeedLevel.HIGH: 3,
    NeedLevel.URGENT: 4,
}


@dataclass(frozen=True)
class AllocationLeg:
    community_id: str
    quantity_kg: int


@dataclass(frozen=True)
class AllocationPlan:
    """The placement of one quantity across one -- or, reluctantly, more -- recipients."""

    legs: tuple[AllocationLeg, ...]
    required_kg: int
    is_split: bool

    @property
    def is_feasible(self) -> bool:
        return self.is_complete

    @property
    def covered_kg(self) -> int:
        return sum(leg.quantity_kg for leg in self.legs)

    @property
    def is_complete(self) -> bool:
        return self.covered_kg == self.required_kg

    @property
    def primary_community_id(self) -> str:
        if not self.legs:
            raise ValueError("AllocationPlan has no legs; check is_feasible first")
        return self.legs[0].community_id


def plan_allocation(
    assessments: list[CandidateAssessment],
    required_kg: int,
) -> AllocationPlan:
    """Choose recipients for `required_kg`, preferring a single destination.

    A candidate is eligible for a single-destination allocation only if it
    passed every hard constraint, which includes holding capacity for the whole
    quantity -- `capacity_sufficient` is computed against `required_kg`, so an
    under-capacity candidate is already labelled EXCLUDED by the eligibility
    policy. The split branch is therefore reached only when the feasible set is
    empty, which is exactly the rule C-2 requires.
    """
    required_kg = require_kilograms(required_kg, name="required_kg", positive=True)

    feasible = [a for a in assessments if a.status is not CandidateStatus.EXCLUDED]
    if feasible:
        best = min(feasible, key=_ranking_key)
        return AllocationPlan(
            legs=(AllocationLeg(best.community.community_id, required_kg),),
            required_kg=required_kg,
            is_split=False,
        )

    return _plan_split(assessments, required_kg)


def _plan_split(assessments: list[CandidateAssessment], required_kg: int) -> AllocationPlan:
    """Fallback only. Reached when no single recipient can take the whole quantity.

    Only candidates whose *sole* failing constraint is capacity may take part:
    a candidate excluded on category or a closed receiving window is not made
    eligible by shrinking the quantity.
    """
    pool = sorted(
        (a for a in assessments if _capacity_is_the_only_failure(a)),
        key=_ranking_key,
    )

    legs: list[AllocationLeg] = []
    outstanding = required_kg
    for candidate in pool:
        if outstanding <= 0:
            break
        take = min(candidate.community.remaining_capacity_kg, outstanding)
        if take > 0:
            legs.append(AllocationLeg(candidate.community.community_id, take))
            outstanding -= take

    return AllocationPlan(legs=tuple(legs), required_kg=required_kg, is_split=True)


def mark_recommended(
    assessments: list[CandidateAssessment],
    community_id: str,
) -> list[CandidateAssessment]:
    """Promote the selected candidate's label to RECOMMENDED, leaving facts intact."""
    return [
        a.model_copy(update={"status": CandidateStatus.RECOMMENDED})
        if a.community.community_id == community_id and a.status is not CandidateStatus.EXCLUDED
        else a
        for a in assessments
    ]


def _capacity_is_the_only_failure(assessment: CandidateAssessment) -> bool:
    codes = {reason.code for reason in assessment.exclusions}
    return codes == {ErrorCode.RECIPIENT_CAPACITY_EXCEEDED}


def _ranking_key(assessment: CandidateAssessment) -> tuple[int, int, str]:
    """Most urgent need first, then shortest simulated drive, then id for determinism."""
    need = assessment.matched_need
    urgency = _NEED_RANK[need.level] if need is not None else -1
    return (-urgency, assessment.route.duration_minutes, assessment.community.community_id)
