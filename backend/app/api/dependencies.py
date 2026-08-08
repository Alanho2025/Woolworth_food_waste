"""FastAPI dependency accessors for the application facade."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from backend.app.application.api_runtime import FoodFlowApiService


def get_api_service(request: Request) -> FoodFlowApiService:
    return cast(FoodFlowApiService, request.app.state.foodflow)
