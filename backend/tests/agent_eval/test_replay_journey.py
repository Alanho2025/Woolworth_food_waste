"""P3 replay evaluations through real tools, applications, and SQLite."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from backend.app.agents.agent import (
    AgentEventStore,
    AgentExecutionResult,
    AgentInvocation,
    ReplayAgentExecutor,
)
from backend.app.agents.schemas import (
    AcceptanceResultView,
    RecordPartialAcceptanceInput,
)
from backend.app.agents.tools.registry import FoodFlowTools
from backend.app.contracts.api import (
    AgentRunKind,
    InitialAgentRunResult,
    RematchAgentRunResult,
)
from backend.app.contracts.core import CandidateStatus
from backend.app.infrastructure.db.models import AgentRunEventRow, AgentRunRow
from backend.app.seed.data import COMMUNITY_A, COMMUNITY_B, COMMUNITY_C, COMMUNITY_D, DONATION_ID
from backend.tests.agent_eval.conftest import AgentHarness

INITIAL_RUN_ID = "RUN-EVAL-INITIAL"
REMATCH_RUN_ID = "RUN-EVAL-REMATCH"


def executor(harness: AgentHarness, *, event_delay_seconds: float = 0.0) -> ReplayAgentExecutor:
    return ReplayAgentExecutor(
        harness.tools,
        AgentEventStore(harness.uow()),
        harness.clock,
        event_delay_seconds=event_delay_seconds,
    )


def initial_invocation(run_id: str = INITIAL_RUN_ID) -> AgentInvocation:
    return AgentInvocation(run_id=run_id, donation_id=DONATION_ID, kind=AgentRunKind.INITIAL)


async def run_initial(harness: AgentHarness) -> AgentExecutionResult:
    return await executor(harness).run(initial_invocation())


@pytest.mark.asyncio
async def test_feasible_replay_selects_a_and_persists_the_real_sixty_kg_order(
    agent_harness: AgentHarness,
) -> None:
    """FEASIBLE replay facts -> real application transaction -> A receives all 60 kg."""
    execution = await run_initial(agent_harness)

    assert isinstance(execution.result, InitialAgentRunResult)
    assert execution.result.decision.selected_community_id == COMMUNITY_A.community_id
    assert execution.result.decision.allocated_kg == 60
    assert execution.result.inventory.total_kg == 60
    assert execution.result.inventory.reserved_kg == 60
    assert execution.result.inventory.in_transit_kg == 0
    with agent_harness.uow() as uow:
        orders = uow.deliveries.list_for_donation(DONATION_ID)
        run = uow.agent_runs.get(INITIAL_RUN_ID)
        assert len(orders) == 1
        assert orders[0].destination_community_id == COMMUNITY_A.community_id
        assert orders[0].quantity_kg == 60
        assert run is not None and run.is_complete is True


@pytest.mark.asyncio
async def test_invalid_candidates_remain_visible_but_are_never_selected(
    agent_harness: AgentHarness,
) -> None:
    """B category invalid + C capacity invalid -> visible exclusions, never recommendation."""
    execution = await run_initial(agent_harness)
    assert isinstance(execution.result, InitialAgentRunResult)

    candidates = {
        candidate.community.community_id: candidate
        for candidate in execution.result.decision.candidates
    }
    assert candidates[COMMUNITY_B.community_id].status is CandidateStatus.EXCLUDED
    assert candidates[COMMUNITY_B.community_id].exclusions
    assert candidates[COMMUNITY_C.community_id].status is CandidateStatus.EXCLUDED
    assert candidates[COMMUNITY_C.community_id].exclusions
    assert candidates[COMMUNITY_A.community_id].status is CandidateStatus.RECOMMENDED
    assert execution.result.decision.selected_community_id not in {
        COMMUNITY_B.community_id,
        COMMUNITY_C.community_id,
    }


@pytest.mark.asyncio
async def test_replay_uses_the_expected_real_tool_sequence(
    agent_harness: AgentHarness,
) -> None:
    """Recorded model choices replace planning only; every business action is a real tool."""
    execution = await run_initial(agent_harness)

    assert execution.tool_trace == (
        "get_donation",
        "list_candidate_communities",
        "get_available_drivers",
        "reserve_inventory",
        "reserve_recipient_capacity",
        "create_delivery_order",
        "assign_driver",
    )
    assert execution.recovered_failures == 1


@pytest.mark.asyncio
async def test_partial_acceptance_rematches_only_the_twenty_five_kg_remainder(
    agent_harness: AgentHarness,
) -> None:
    """Replay initial + real 35 kg acceptance + replay rematch -> one new 25 kg order to D."""
    initial = await run_initial(agent_harness)
    assert isinstance(initial.result, InitialAgentRunResult)
    original_order_id = initial.result.order_refs[0]

    accepted = await FoodFlowTools(agent_harness.tools).record_partial_acceptance(
        RecordPartialAcceptanceInput(
            order_id=original_order_id,
            accepted_kg=35,
            reason="Capacity corrected on arrival",
        )
    )
    assert isinstance(accepted, AcceptanceResultView)
    assert (accepted.accepted_kg, accepted.remaining_kg) == (35, 25)

    rematch = await executor(agent_harness).run(
        AgentInvocation(
            run_id=REMATCH_RUN_ID,
            donation_id=DONATION_ID,
            kind=AgentRunKind.REMATCH,
            declined_order_id=original_order_id,
            original_community_id=COMMUNITY_A.community_id,
            accepted_kg=accepted.accepted_kg,
            remaining_kg=accepted.remaining_kg,
        )
    )

    assert isinstance(rematch.result, RematchAgentRunResult)
    assert rematch.result.decision.accepted_kg == 35
    assert rematch.result.decision.remaining_kg == 25
    assert rematch.result.decision.new_community_id == COMMUNITY_D.community_id
    assert rematch.result.inventory.delivered_kg == 35
    assert rematch.result.inventory.reserved_kg == 25
    replacement_order_id = rematch.result.order_refs[0]
    delivered = await FoodFlowTools(agent_harness.tools).record_partial_acceptance(
        RecordPartialAcceptanceInput(
            order_id=replacement_order_id,
            accepted_kg=25,
            reason="Remainder accepted in full",
        )
    )
    assert isinstance(delivered, AcceptanceResultView)
    assert (delivered.accepted_kg, delivered.remaining_kg) == (25, 0)
    assert (
        delivered.inventory.available_kg,
        delivered.inventory.reserved_kg,
        delivered.inventory.in_transit_kg,
        delivered.inventory.delivered_kg,
    ) == (0, 0, 0, 60)
    with agent_harness.uow() as uow:
        orders = uow.deliveries.list_for_donation(DONATION_ID)
        original = uow.deliveries.get(original_order_id)
        replacement = uow.deliveries.get(replacement_order_id)
        initial_run = uow.agent_runs.get(INITIAL_RUN_ID)
        rematch_run = uow.agent_runs.get(REMATCH_RUN_ID)
        assert len(orders) == 2
        assert original is not None and replacement is not None
        assert replacement.quantity_kg == 25
        assert replacement.origin == COMMUNITY_A.location
        assert replacement.driver_id == original.driver_id
        assert replacement.is_rematch is True
        assert initial_run is not None and rematch_run is not None
        assert len(initial_run.events) + len(rematch_run.events) == 11


@pytest.mark.asyncio
async def test_explanation_is_grounded_in_returned_candidate_and_route_facts(
    agent_harness: AgentHarness,
) -> None:
    """Explanation names only the selected candidate and facts returned by real tools."""
    execution = await run_initial(agent_harness)
    assert isinstance(execution.result, InitialAgentRunResult)
    decision = execution.result.decision
    selected = next(
        candidate
        for candidate in decision.candidates
        if candidate.community.community_id == decision.selected_community_id
    )
    explanation = decision.explanation.casefold()

    assert "community a" in explanation
    assert "urgent vegetable demand" in explanation
    assert "sufficient capacity" in explanation
    assert "compatible receiving hours" in explanation
    assert "simulated route" in explanation
    assert selected.route is not None
    assert selected.route.simulated is True
    assert selected.community.remaining_capacity_kg >= decision.allocated_kg


@pytest.mark.asyncio
async def test_replay_full_journey_needs_no_provider_key(
    agent_harness: AgentHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No DeepSeek key -> replay still completes using real SQLite/application tools."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    execution = await run_initial(agent_harness)

    assert isinstance(execution.result, InitialAgentRunResult)
    assert execution.result.decision.selected_community_id == COMMUNITY_A.community_id
    assert execution.events
    assert execution.result.order_refs


@pytest.mark.asyncio
async def test_agent_events_are_queryable_while_the_replay_is_still_running(
    agent_harness: AgentHarness,
) -> None:
    """Delayed replay -> a second real UOW observes a growing non-terminal event list."""
    delayed = executor(agent_harness, event_delay_seconds=0.02)
    task = asyncio.create_task(delayed.run(initial_invocation("RUN-EVAL-POLL")))

    observed_count = 0
    for _ in range(100):
        with agent_harness.uow() as uow:
            run = uow.agent_runs.get("RUN-EVAL-POLL")
            if run is not None and run.events and not run.is_complete:
                observed_count = len(run.events)
                break
        await asyncio.sleep(0.005)

    assert observed_count > 0
    execution = await task
    assert observed_count < len(execution.events)
    with agent_harness.uow() as uow:
        completed = uow.agent_runs.get("RUN-EVAL-POLL")
        assert completed is not None
        assert completed.is_complete is True
        assert len(completed.events) == len(execution.events)


@pytest.mark.asyncio
async def test_only_visible_state_is_persisted_never_model_reasoning(
    agent_harness: AgentHarness,
) -> None:
    """Completed replay -> agent tables contain public states, with no reasoning field/value."""
    await run_initial(agent_harness)

    assert "reasoning" not in AgentRunRow.__table__.columns
    assert "reasoning" not in AgentRunEventRow.__table__.columns
    with agent_harness.sessions() as session:
        rows = session.scalars(
            select(AgentRunEventRow).where(AgentRunEventRow.run_id == INITIAL_RUN_ID)
        ).all()
    persisted_text = " ".join(f"{row.state} {row.label} {row.detail}" for row in rows).casefold()
    assert rows
    assert "reasoning_content" not in persisted_text
    assert "chain of thought" not in persisted_text
