"""P2 deterministic OpenAPI freeze and public-schema boundary assertions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.check_openapi_compat import compatibility_violations
from scripts.generate_openapi import build_openapi, render_openapi

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OPENAPI_PATH = PROJECT_ROOT / "backend" / "contracts" / "openapi.json"

REQUIRED_OPERATIONS = {
    "/health": "get",
    "/donations": "post",
    "/donations/{donation_id}/match": "post",
    "/agent-runs/{run_id}": "get",
    "/deliveries/{delivery_id}": "get",
    "/deliveries/{delivery_id}/confirm": "post",
    "/dashboard": "get",
}


def frozen_openapi() -> dict[str, Any]:
    document = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def schema(document: dict[str, Any], name: str) -> dict[str, Any]:
    value = document["components"]["schemas"][name]
    assert isinstance(value, dict)
    return value


def test_frozen_openapi_is_byte_for_byte_the_deterministically_rendered_contract() -> None:
    """FROZEN ARTIFACT + TWO GENERATIONS -> exact same sorted UTF-8 JSON."""
    frozen = OPENAPI_PATH.read_text(encoding="utf-8")
    first = render_openapi()
    second = render_openapi()

    assert first == second
    assert frozen == first
    assert compatibility_violations(json.loads(frozen), build_openapi()) == []


def test_frozen_openapi_contains_exactly_the_seven_required_p2_paths_and_methods() -> None:
    """P2 CONTRACT -> inspect paths -> all frontend-unblocking operations are frozen."""
    document = frozen_openapi()

    assert set(document["paths"]) == set(REQUIRED_OPERATIONS)
    for path, method in REQUIRED_OPERATIONS.items():
        assert method in document["paths"][path]
    operation_ids = [
        document["paths"][path][method]["operationId"]
        for path, method in REQUIRED_OPERATIONS.items()
    ]
    assert len(operation_ids) == len(set(operation_ids))


def test_create_match_and_confirmation_operations_freeze_required_body_and_response_models() -> (
    None
):
    """WRITE OPERATIONS -> inspect refs/statuses -> stable typed request/response surfaces."""
    paths = frozen_openapi()["paths"]
    create = paths["/donations"]["post"]
    match = paths["/donations/{donation_id}/match"]["post"]
    confirm = paths["/deliveries/{delivery_id}/confirm"]["post"]

    assert create["requestBody"]["required"] is True
    assert create["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CreateDonationRequest"
    }
    assert create["responses"]["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CreateDonationResponse"
    }
    assert match["responses"]["202"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/StartMatchResponse"
    }
    assert confirm["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ConfirmDeliveryRequest"
    }
    assert confirm["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ConfirmDeliveryResponse"
    }


def test_quantity_capacity_route_and_origin_fields_are_required_and_typed_in_openapi() -> None:
    """BLOCKER FIELDS -> inspect schemas -> integer kg, separate capacity, explicit route/origin."""
    document = frozen_openapi()
    food_item = schema(document, "FoodItem")
    inventory = schema(document, "DonationInventory")
    community = schema(document, "CommunityOrganisation")
    order = schema(document, "DeliveryOrder")
    candidate = schema(document, "CandidateAssessment")
    confirmation = schema(document, "ConfirmDeliveryResponse")

    assert food_item["properties"]["quantity"]["type"] == "integer"
    assert food_item["properties"]["quantity"]["exclusiveMinimum"] == 0
    assert {
        "total_kg",
        "available_kg",
        "reserved_kg",
        "in_transit_kg",
        "delivered_kg",
    } <= set(inventory["required"])
    assert all(
        inventory["properties"][field]["type"] == "integer"
        for field in (
            "total_kg",
            "available_kg",
            "reserved_kg",
            "in_transit_kg",
            "delivered_kg",
        )
    )
    assert {"declared_capacity_kg", "remaining_capacity_kg"} <= set(community["required"])
    assert community["properties"]["declared_capacity_kg"]["type"] == "integer"
    assert community["properties"]["remaining_capacity_kg"]["type"] == "integer"
    assert {"origin", "route", "quantity_kg"} <= set(order["required"])
    assert order["properties"]["quantity_kg"]["type"] == "integer"
    assert "route" in candidate["required"], "excluded candidates must still carry ETA/route"
    assert {"planned_kg", "accepted_kg", "remaining_kg", "inventory"} <= set(
        confirmation["required"]
    )
    assert all(
        confirmation["properties"][field]["type"] == "integer"
        for field in ("planned_kg", "accepted_kg", "remaining_kg")
    )


def test_openapi_schema_registry_contains_no_sqlalchemy_or_orm_row_surface() -> None:
    """FROZEN PUBLIC DOCUMENT -> inspect registry/refs -> no persistence model leaks."""
    document = frozen_openapi()
    schemas = document["components"]["schemas"]
    serialized = json.dumps(document, sort_keys=True).lower()

    assert all(not name.endswith("Row") for name in schemas)
    assert all("orm" not in name.lower() for name in schemas)
    assert "sqlalchemy" not in serialized
    assert "infrastructure.db" not in serialized
    assert "__table__" not in serialized
