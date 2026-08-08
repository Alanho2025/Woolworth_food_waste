"""Real SQLite/application/tool wiring for replay-only P3 evaluations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import Engine

from backend.app.agents.bounds import AgentBounds
from backend.app.agents.tools.registry import ToolDependencies
from backend.app.application.allocate_donation import AllocateDonation
from backend.app.application.record_acceptance import RecordAcceptance
from backend.app.application.rematch import RematchRemaining
from backend.app.domain.clock import DEMO_NOW, PinnedClock
from backend.app.infrastructure.db.session import (
    SessionFactory,
    create_db_engine,
    create_session_factory,
)
from backend.app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from backend.app.infrastructure.route_simulator import SimulatedRouteSimulator
from backend.app.seed.data import ROUTE_POLYLINES
from backend.app.seed.seed import seed


@dataclass(frozen=True)
class AgentHarness:
    """Production P1/P2 dependencies plus a deterministic replay model boundary."""

    database_url: str
    engine: Engine
    sessions: SessionFactory
    clock: PinnedClock
    tools: ToolDependencies

    def uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.sessions)


@pytest.fixture
def agent_harness(tmp_path: Path) -> AgentHarness:
    path = tmp_path / "agent-eval.db"
    database_url = f"sqlite:///{path}"
    seed(database_url)
    engine = create_db_engine(database_url)
    sessions = create_session_factory(engine)
    clock = PinnedClock(DEMO_NOW)
    routes = SimulatedRouteSimulator(clock, ROUTE_POLYLINES)
    uow = SqlAlchemyUnitOfWork(sessions)
    allocator = AllocateDonation(uow, routes, clock)
    tools = ToolDependencies(
        uow=uow,
        allocator=allocator,
        acceptance=RecordAcceptance(SqlAlchemyUnitOfWork(sessions), clock),
        rematcher=RematchRemaining(SqlAlchemyUnitOfWork(sessions), allocator),
        routes=routes,
        bounds=AgentBounds(
            max_llm_calls=24,
            run_timeout_seconds=5,
            tool_timeout_seconds=2,
        ),
    )
    harness = AgentHarness(
        database_url=database_url,
        engine=engine,
        sessions=sessions,
        clock=clock,
        tools=tools,
    )
    yield harness
    engine.dispose()
