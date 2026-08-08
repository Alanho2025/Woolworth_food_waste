"""Global operations dashboard transport route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_api_service
from backend.app.application.api_runtime import FoodFlowApiService
from backend.app.contracts.api import ApiErrorResponse, GlobalDashboardResponse

router = APIRouter()
Service = Annotated[FoodFlowApiService, Depends(get_api_service)]


@router.get(
    "/dashboard",
    response_model=GlobalDashboardResponse,
    responses={503: {"model": ApiErrorResponse, "description": "Typed FoodFlow error"}},
    operation_id="getDashboard",
    tags=["dashboard"],
)
async def get_dashboard(service: Service) -> GlobalDashboardResponse:
    return service.dashboard()
