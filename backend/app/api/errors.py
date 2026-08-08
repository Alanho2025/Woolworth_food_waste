"""Map typed domain/application failures to typed HTTP errors."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.contracts.api import ApiErrorResponse, ApiFieldError
from backend.app.domain.errors import ErrorCode, FoodFlowError

_STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.INVALID_STATE_TRANSITION: 409,
    ErrorCode.QUANTITY_INTEGRITY_VIOLATION: 409,
    ErrorCode.AGENT_TIMEOUT: 503,
    ErrorCode.TOOL_TIMEOUT: 503,
    ErrorCode.TOOL_INTERNAL_FAILURE: 503,
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(FoodFlowError)
    async def foodflow_error(_request: Request, error: FoodFlowError) -> JSONResponse:
        payload = ApiErrorResponse(
            code=error.code,
            detail=error.detail,
            retryable=error.code
            in {ErrorCode.AGENT_TIMEOUT, ErrorCode.TOOL_TIMEOUT, ErrorCode.TOOL_INTERNAL_FAILURE},
        )
        return JSONResponse(
            status_code=_STATUS_BY_CODE.get(error.code, 400),
            content=payload.model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        fields = [
            ApiFieldError(
                field=".".join(str(part) for part in item["loc"] if part != "body"),
                message=item["msg"],
            )
            for item in error.errors()
        ]
        payload = ApiErrorResponse(
            code=ErrorCode.AGENT_OUTPUT_INVALID,
            detail="Request validation failed",
            field_errors=fields,
        )
        return JSONResponse(status_code=422, content=payload.model_dump(mode="json"))

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
        payload = ApiErrorResponse(
            code=ErrorCode.TOOL_INTERNAL_FAILURE,
            detail="Unexpected backend failure",
            retryable=True,
        )
        return JSONResponse(status_code=500, content=payload.model_dump(mode="json"))
