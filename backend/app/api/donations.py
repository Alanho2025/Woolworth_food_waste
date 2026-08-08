"""Donation and initial-match transport routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from backend.app.api.dependencies import get_api_service
from backend.app.application.api_runtime import FoodFlowApiService
from backend.app.contracts.api import (
    ApiErrorResponse,
    CreateDonationRequest,
    CreateDonationResponse,
    StartMatchResponse,
)

router = APIRouter()
Service = Annotated[FoodFlowApiService, Depends(get_api_service)]


def _errors(*codes: int) -> dict[int | str, dict[str, object]]:
    return {
        code: {"model": ApiErrorResponse, "description": "Typed FoodFlow error"} for code in codes
    }


@router.post(
    "/donations",
    response_model=CreateDonationResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_errors(400, 409, 422),
    operation_id="createDonation",
    tags=["donations"],
)
async def create_donation(
    request: CreateDonationRequest, service: Service
) -> CreateDonationResponse:
    return service.create_donation(request)


@router.post(
    "/donations/{donation_id}/match",
    response_model=StartMatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_errors(404, 409, 422),
    operation_id="startDonationMatch",
    tags=["agent-runs"],
)
async def start_match(donation_id: str, service: Service) -> StartMatchResponse:
    return service.start_match(donation_id)
