from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.config import get_settings
from backend.app.database import check_database, create_db_engine


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ready"]


def create_app() -> FastAPI:
    settings = get_settings()
    engine = create_db_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        check_database(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="FoodFlow Platform Foundation",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()
        ],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", database="ready")

    return app


app = create_app()
