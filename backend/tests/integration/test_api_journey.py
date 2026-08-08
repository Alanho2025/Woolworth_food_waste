"""P4 HTTP journey through FastAPI, replay planning, and real isolated SQLite."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.config import AgentTransport, Settings
from backend.app.main import create_app
from backend.app.seed.data import COMMUNITY_A, COMMUNITY_D, STORE_ID, STORE_LOCATIONS
from backend.app.seed.seed import seed


@pytest.fixture
def api_client(tmp_path: Path) -> Iterator[TestClient]:
    database_url = f"sqlite:///{tmp_path / 'api-journey.db'}"
    seed(database_url)
    settings = Settings(
        deepseek_api_key="",
        deepseek_base_url="https://provider.invalid/v1",
        deepseek_model="deepseek-v4-flash",
        database_url=database_url,
        demo_mode=True,
        agent_transport=AgentTransport.REPLAY,
        agent_max_llm_calls=24,
        agent_run_timeout_seconds=5,
        agent_tool_timeout_seconds=2,
    )
    with TestClient(create_app(settings, replay_event_delay_seconds=0.025)) as client:
        yield client


def donation_payload() -> dict[str, Any]:
    return {
        "donation_id": "DON-PREVIEW-001",
        "store_id": STORE_ID,
        "pickup_window": {
            "start": "2026-08-08T16:00:00+12:00",
            "end": "2026-08-08T17:00:00+12:00",
        },
        "items": [
            {
                "item_name": "Fresh vegetables",
                "category": "vegetables",
                "quantity": 60,
                "unit": "kg",
                "storage_type": "ambient",
                "delivery_deadline": "2026-08-08T19:00:00+12:00",
            }
        ],
        "handling_notes": "Keep shaded and deliver in stackable produce crates.",
    }


def await_succeeded(client: TestClient, run_id: str) -> tuple[dict[str, Any], list[int]]:
    deadline = time.monotonic() + 5
    observed_event_counts: list[int] = []
    while time.monotonic() < deadline:
        response = client.get(f"/agent-runs/{run_id}")
        assert response.status_code == 200, response.text
        body = response.json()
        observed_event_counts.append(len(body["events"]))
        if body["status"] == "succeeded":
            return body, observed_event_counts
        assert body["status"] in {"queued", "running"}, body
        time.sleep(0.01)
    raise AssertionError(f"Agent run {run_id} did not succeed; counts={observed_event_counts}")


@pytest.mark.parametrize("store_id", tuple(STORE_LOCATIONS))
def test_create_donation_resolves_each_cbd_store_to_its_authoritative_location(
    api_client: TestClient,
    store_id: str,
) -> None:
    payload = donation_payload()
    payload["store_id"] = store_id

    response = api_client.post("/donations", json=payload)

    assert response.status_code == 201, response.text
    donation = response.json()["donation"]
    expected = STORE_LOCATIONS[store_id]
    assert donation["store_id"] == store_id
    assert donation["store_location"] == expected.model_dump()


def test_complete_http_journey_auto_rematches_and_balances_all_sixty_kg(
    api_client: TestClient,
) -> None:
    """POST donation -> replay A -> accept 35 -> auto-rematch D -> accept 25 -> delivered 60."""
    health = api_client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "foodflow-backend"}

    created_response = api_client.post("/donations", json=donation_payload())
    assert created_response.status_code == 201, created_response.text
    created = created_response.json()
    donation_id = created["donation"]["donation_id"]
    assert donation_id.startswith("DON-")
    assert donation_id != "DON-PREVIEW-001", "the backend must mint the authoritative ID"
    assert created["donation"]["items"][0]["quantity"] == 60
    assert created["inventory"] == {
        "donation_id": donation_id,
        "total_kg": 60,
        "available_kg": 60,
        "reserved_kg": 0,
        "in_transit_kg": 0,
        "delivered_kg": 0,
    }

    started_response = api_client.post(f"/donations/{donation_id}/match")
    assert started_response.status_code == 202, started_response.text
    started = started_response.json()
    assert started["donation_id"] == donation_id
    assert started["status"] == "queued"
    assert started["kind"] == "initial"
    assert started["transport"] == "replay"

    initial, initial_counts = await_succeeded(api_client, started["run_id"])
    assert len(initial["events"]) == 7
    assert any(0 < count < 7 for count in initial_counts), initial_counts
    assert initial["result"]["decision"]["selected_community_id"] == COMMUNITY_A.community_id
    assert initial["result"]["decision"]["allocated_kg"] == 60
    original_order_id = initial["result"]["order_refs"][0]

    delivery_response = api_client.get(f"/deliveries/{original_order_id}")
    assert delivery_response.status_code == 200, delivery_response.text
    delivery = delivery_response.json()
    assert delivery["order"]["donation_id"] == donation_id
    assert delivery["order"]["destination_community_id"] == COMMUNITY_A.community_id
    assert delivery["order"]["quantity_kg"] == 60
    assert delivery["order"]["route"]["simulated"] is True
    original_driver_id = delivery["driver"]["driver_id"]

    partial_response = api_client.post(
        f"/deliveries/{original_order_id}/confirm",
        json={
            "outcome": "partial",
            "accepted_kg": 35,
            "reason": "Capacity corrected on arrival",
        },
    )
    assert partial_response.status_code == 200, partial_response.text
    partial = partial_response.json()
    assert (partial["planned_kg"], partial["accepted_kg"], partial["remaining_kg"]) == (
        60,
        35,
        25,
    )
    assert partial["corrected_community"]["community_id"] == COMMUNITY_A.community_id
    assert partial["corrected_community"]["declared_capacity_kg"] == 35
    assert partial["corrected_community"]["remaining_capacity_kg"] == 0
    assert partial["rematch_run_id"]

    rematch, rematch_counts = await_succeeded(api_client, partial["rematch_run_id"])
    assert len(rematch["events"]) == 4
    assert any(0 < count < 4 for count in rematch_counts), rematch_counts
    assert rematch["result"]["decision"]["remaining_kg"] == 25
    assert rematch["result"]["decision"]["new_community_id"] == COMMUNITY_D.community_id
    replacement_order_id = rematch["result"]["order_refs"][0]

    replacement_response = api_client.get(f"/deliveries/{replacement_order_id}")
    assert replacement_response.status_code == 200, replacement_response.text
    replacement = replacement_response.json()
    assert replacement["order"]["quantity_kg"] == 25
    assert replacement["order"]["origin"] == COMMUNITY_A.location.model_dump(mode="json")
    assert replacement["driver"]["driver_id"] == original_driver_id

    final_response = api_client.post(
        f"/deliveries/{replacement_order_id}/confirm",
        json={"outcome": "full", "accepted_kg": 25, "reason": ""},
    )
    assert final_response.status_code == 200, final_response.text
    final = final_response.json()
    assert (final["accepted_kg"], final["remaining_kg"], final["rematch_run_id"]) == (
        25,
        0,
        None,
    )
    assert (
        final["inventory"]["available_kg"],
        final["inventory"]["reserved_kg"],
        final["inventory"]["in_transit_kg"],
        final["inventory"]["delivered_kg"],
    ) == (0, 0, 0, 60)

    dashboard_response = api_client.get("/dashboard")
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()
    ledger = next(item for item in dashboard["inventories"] if item["donation_id"] == donation_id)
    assert ledger["delivered_kg"] == 60
    alert = dashboard["capacity_change_highlight"]
    assert alert["community_id"] == COMMUNITY_A.community_id
    assert alert["declared_capacity_kg"] == 35
    assert alert["accepted_kg"] == 35
    assert "35 of 60 kg" in alert["message"]


def test_invalid_http_inputs_return_typed_errors_and_never_an_internal_500(
    api_client: TestClient,
) -> None:
    """Invalid strict kg and unknown donation -> typed 422/404 payloads, never stack traces."""
    invalid = donation_payload()
    invalid["items"][0]["quantity"] = 60.5

    validation_response = api_client.post("/donations", json=invalid)
    assert validation_response.status_code == 422
    validation = validation_response.json()
    assert validation["code"] == "AGENT_OUTPUT_INVALID"
    assert validation["detail"] == "Request validation failed"
    assert validation["field_errors"]
    assert "traceback" not in validation_response.text.casefold()

    missing_response = api_client.post("/donations/DON-DOES-NOT-EXIST/match")
    assert missing_response.status_code == 404
    missing = missing_response.json()
    assert missing["code"] == "NOT_FOUND"
    assert missing["retryable"] is False
    assert "traceback" not in missing_response.text.casefold()
