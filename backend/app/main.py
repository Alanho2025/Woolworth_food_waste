"""FoodFlow FastAPI composition root."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.agent_runs import router as agent_runs_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.deliveries import router as deliveries_router
from backend.app.api.donations import router as donations_router
from backend.app.api.errors import install_error_handlers
from backend.app.application.api_runtime import AgentRunCoordinator, FoodFlowApiService
from backend.app.application.record_acceptance import RecordAcceptance
from backend.app.config import Settings, get_settings
from backend.app.contracts.api import HealthResponse
from backend.app.domain.clock import PinnedClock, SystemClock
from backend.app.infrastructure.db.session import (
    create_all,
    create_db_engine,
    create_session_factory,
)
from backend.app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from backend.app.infrastructure.route_simulator import SimulatedRouteSimulator
from backend.app.seed.data import ROUTE_POLYLINES


def create_app(
    settings: Settings | None = None,
    *,
    replay_event_delay_seconds: float = 0.02,
) -> FastAPI:
    """Build an isolated app; tests inject settings pointing at a temporary DB."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        resolved = settings or get_settings()
        engine = create_db_engine(resolved.database_url)
        create_all(engine)
        sessions = create_session_factory(engine)
        clock = PinnedClock() if resolved.demo_mode else SystemClock()
        routes = SimulatedRouteSimulator(clock, ROUTE_POLYLINES)

        def uow_factory() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(sessions)

        coordinator = AgentRunCoordinator(
            uow_factory,
            routes,
            clock,
            resolved,
            replay_event_delay_seconds=replay_event_delay_seconds,
        )
        application.state.foodflow = FoodFlowApiService(
            uow_factory,
            RecordAcceptance(uow_factory(), clock),
            coordinator,
            clock,
        )
        application.state.agent_runs = coordinator
        try:
            yield
        finally:
            await coordinator.shutdown()
            engine.dispose()

    application = FastAPI(
        title="FoodFlow Auckland API",
        version="0.1.0",
        description=("Typed FoodFlow runtime API; all routing and ETA values are simulated."),
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    install_error_handlers(application)

    @application.get(
        "/health",
        response_model=HealthResponse,
        operation_id="getHealth",
        tags=["system"],
    )
    async def health() -> HealthResponse:
        return HealthResponse()

    application.include_router(donations_router)
    application.include_router(agent_runs_router)
    application.include_router(deliveries_router)
    application.include_router(dashboard_router)
    return application


app = create_app()
