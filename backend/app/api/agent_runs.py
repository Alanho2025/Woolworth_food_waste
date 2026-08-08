"""Incrementally pollable Agent run transport route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_api_service
from backend.app.application.api_runtime import FoodFlowApiService
from backend.app.contracts.api import AgentRunResponse, ApiErrorResponse

router = APIRouter()
Service = Annotated[FoodFlowApiService, Depends(get_api_service)]


@router.get(
    "/agent-runs/{run_id}",
    response_model=AgentRunResponse,
    responses={
        404: {"model": ApiErrorResponse, "description": "Typed FoodFlow error"},
        422: {"model": ApiErrorResponse, "description": "Typed FoodFlow error"},
    },
    operation_id="getAgentRun",
    tags=["agent-runs"],
)
async def get_agent_run(run_id: str, service: Service) -> AgentRunResponse:
    return service.get_agent_run(run_id)
