#!/usr/bin/env python3
"""Generate the P2 contract-only OpenAPI freeze without implementing P4 routes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.contracts.api import (  # noqa: E402
    AgentRunResponse,
    ApiErrorResponse,
    ConfirmDeliveryRequest,
    ConfirmDeliveryResponse,
    CreateDonationRequest,
    CreateDonationResponse,
    DeliveryDetailResponse,
    GlobalDashboardResponse,
    HealthResponse,
    StartMatchResponse,
)
from fastapi import FastAPI, status  # noqa: E402

DEFAULT_OUTPUT = PROJECT_ROOT / "backend" / "contracts" / "openapi.json"


def _errors(*codes: int) -> dict[int | str, dict[str, Any]]:
    return {
        code: {
            "model": ApiErrorResponse,
            "description": "Typed FoodFlow error",
        }
        for code in codes
    }


def build_contract_app() -> FastAPI:
    """A schema-only app whose signatures freeze the future P4 transport."""
    app = FastAPI(
        title="FoodFlow Auckland API",
        version="0.1.0",
        description=(
            "P2 frozen transport contract. Runtime route implementation begins in P4; "
            "all routing and ETA values are simulated."
        ),
    )

    @app.get(
        "/health",
        response_model=HealthResponse,
        operation_id="getHealth",
        tags=["system"],
    )
    async def health() -> HealthResponse:
        raise NotImplementedError("contract-only route")

    @app.post(
        "/donations",
        response_model=CreateDonationResponse,
        status_code=status.HTTP_201_CREATED,
        responses=_errors(400, 409, 422),
        operation_id="createDonation",
        tags=["donations"],
    )
    async def create_donation(request: CreateDonationRequest) -> CreateDonationResponse:
        del request
        raise NotImplementedError("contract-only route")

    @app.post(
        "/donations/{donation_id}/match",
        response_model=StartMatchResponse,
        status_code=status.HTTP_202_ACCEPTED,
        responses=_errors(404, 409, 422),
        operation_id="startDonationMatch",
        tags=["agent-runs"],
    )
    async def start_match(donation_id: str) -> StartMatchResponse:
        del donation_id
        raise NotImplementedError("contract-only route")

    @app.get(
        "/agent-runs/{run_id}",
        response_model=AgentRunResponse,
        responses=_errors(404, 422),
        operation_id="getAgentRun",
        tags=["agent-runs"],
    )
    async def get_agent_run(run_id: str) -> AgentRunResponse:
        del run_id
        raise NotImplementedError("contract-only route")

    @app.get(
        "/deliveries/{delivery_id}",
        response_model=DeliveryDetailResponse,
        responses=_errors(404, 422),
        operation_id="getDelivery",
        tags=["deliveries"],
    )
    async def get_delivery(delivery_id: str) -> DeliveryDetailResponse:
        del delivery_id
        raise NotImplementedError("contract-only route")

    @app.post(
        "/deliveries/{delivery_id}/confirm",
        response_model=ConfirmDeliveryResponse,
        responses=_errors(400, 404, 409, 422),
        operation_id="confirmDelivery",
        tags=["deliveries"],
    )
    async def confirm_delivery(
        delivery_id: str, request: ConfirmDeliveryRequest
    ) -> ConfirmDeliveryResponse:
        del delivery_id, request
        raise NotImplementedError("contract-only route")

    @app.get(
        "/dashboard",
        response_model=GlobalDashboardResponse,
        responses=_errors(503),
        operation_id="getDashboard",
        tags=["dashboard"],
    )
    async def get_dashboard() -> GlobalDashboardResponse:
        raise NotImplementedError("contract-only route")

    return app


def build_openapi() -> dict[str, Any]:
    """Build one deterministic in-memory schema from the frozen signatures."""
    return build_contract_app().openapi()


def render_openapi() -> str:
    return json.dumps(build_openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the frozen artifact differs; do not write it.",
    )
    args = parser.parse_args()
    rendered = render_openapi()
    output: Path = args.output
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != rendered:
            print(f"OpenAPI artifact is stale: {output.relative_to(PROJECT_ROOT)}")
            return 1
        print(f"OpenAPI artifact is deterministic: {output.relative_to(PROJECT_ROOT)}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {output.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
