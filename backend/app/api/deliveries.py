"""Delivery detail and recipient confirmation transport routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_api_service
from backend.app.application.api_runtime import FoodFlowApiService
from backend.app.contracts.api import (
    ApiErrorResponse,
    ConfirmDeliveryRequest,
    ConfirmDeliveryResponse,
    DeliveryDetailResponse,
)

router = APIRouter()
Service = Annotated[FoodFlowApiService, Depends(get_api_service)]


def _errors(*codes: int) -> dict[int | str, dict[str, object]]:
    return {
        code: {"model": ApiErrorResponse, "description": "Typed FoodFlow error"} for code in codes
    }


@router.get(
    "/deliveries/{delivery_id}",
    response_model=DeliveryDetailResponse,
    responses=_errors(404, 422),
    operation_id="getDelivery",
    tags=["deliveries"],
)
async def get_delivery(delivery_id: str, service: Service) -> DeliveryDetailResponse:
    return service.get_delivery(delivery_id)


@router.post(
    "/deliveries/{delivery_id}/confirm",
    response_model=ConfirmDeliveryResponse,
    responses=_errors(400, 404, 409, 422),
    operation_id="confirmDelivery",
    tags=["deliveries"],
)
async def confirm_delivery(
    delivery_id: str,
    request: ConfirmDeliveryRequest,
    service: Service,
) -> ConfirmDeliveryResponse:
    return service.confirm_delivery(delivery_id, request)
