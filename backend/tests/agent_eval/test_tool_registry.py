"""The reconciled P3 tool contract shared by both source-of-truth documents."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.app.agents.schemas import DonationView, GetDonationInput
from backend.app.agents.tools.registry import CANONICAL_TOOL_NAMES, build_tool_functions
from backend.app.seed.data import DONATION_ID
from backend.tests.agent_eval.conftest import AgentHarness

PROJECT_ROOT = Path(__file__).resolve().parents[3]

EXPECTED_TOOL_NAMES = (
    "get_donation",
    "list_candidate_communities",
    "get_community_capacity",
    "get_available_drivers",
    "calculate_route",
    "validate_category_acceptance",
    "validate_storage_compatibility",
    "validate_recipient_capacity",
    "validate_receiving_window",
    "validate_driver_capacity",
    "reserve_inventory",
    "reserve_recipient_capacity",
    "create_delivery_order",
    "assign_driver",
    "record_partial_acceptance",
    "release_remaining_inventory",
    "create_rematched_delivery",
    "update_driver_route",
)


def test_registry_exposes_exactly_the_eighteen_canonical_tools_in_contract_order() -> None:
    """P3 TOOL REGISTRY -> inspect names -> exact reconciled set, no aliases or extras."""
    assert CANONICAL_TOOL_NAMES == EXPECTED_TOOL_NAMES
    assert len(CANONICAL_TOOL_NAMES) == 18
    assert len(set(CANONICAL_TOOL_NAMES)) == 18


def test_requirement_and_clean_code_spec_publish_the_same_exact_eighteen_tool_names() -> None:
    """BOTH AUTHORITIES -> parse their required-tool sections -> same canonical tuple."""
    requirement = (PROJECT_ROOT / "Requirement.md").read_text(encoding="utf-8")
    requirement_section = requirement.split("11. MINIMUM REQUIRED TOOLS", maxsplit=1)[1].split(
        "12. VISIBLE AGENT STATES", maxsplit=1
    )[0]
    requirement_names = tuple(re.findall(r"^- ([a-z][a-z0-9_]*)$", requirement_section, re.M))

    clean_spec = (PROJECT_ROOT / "docs" / "clean_code_spec.md").read_text(encoding="utf-8")
    clean_section = clean_spec.split("Required MVP tools", maxsplit=1)[1].split("```", maxsplit=2)[
        1
    ]
    clean_names = tuple(
        line.strip()
        for line in clean_section.splitlines()
        if line.strip() and line.strip() != "text"
    )

    assert requirement_names == EXPECTED_TOOL_NAMES
    assert clean_names == EXPECTED_TOOL_NAMES


@pytest.mark.asyncio
async def test_built_registry_invokes_real_get_donation_tool_against_seeded_sqlite(
    agent_harness: AgentHarness,
) -> None:
    """REAL REGISTRY + SEEDED SQLITE -> get_donation -> typed 60 kg fact result."""
    functions = build_tool_functions(agent_harness.tools)
    assert tuple(function.__name__ for function in functions) == EXPECTED_TOOL_NAMES

    result = await functions[0](GetDonationInput(donation_id=DONATION_ID))

    assert isinstance(result, DonationView)
    assert result.donation.donation_id == DONATION_ID
    assert result.inventory.total_kg == 60
    assert result.inventory.available_kg == 60
