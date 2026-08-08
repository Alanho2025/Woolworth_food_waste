"""Real P2 integration wiring over one isolated on-disk SQLite database per test."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import Engine

from backend.app.application.allocate_donation import AllocateDonation
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
class DatabaseHarness:
    """The production adapters pointed at a disposable database, never fakes."""

    url: str
    path: Path
    engine: Engine
    sessions: SessionFactory

    def uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.sessions)

    def allocator(self, clock: PinnedClock | None = None) -> AllocateDonation:
        selected_clock = clock or PinnedClock(DEMO_NOW)
        return AllocateDonation(
            self.uow(),
            SimulatedRouteSimulator(selected_clock, ROUTE_POLYLINES),
            selected_clock,
        )


@pytest.fixture
def database(tmp_path: Path) -> DatabaseHarness:
    """Seed and expose a fresh real SQLite database, then release its engine."""
    path = tmp_path / "foodflow-integration.db"
    url = f"sqlite:///{path}"
    seed(url)
    engine = create_db_engine(url)
    harness = DatabaseHarness(
        url=url,
        path=path,
        engine=engine,
        sessions=create_session_factory(engine),
    )
    yield harness
    engine.dispose()
