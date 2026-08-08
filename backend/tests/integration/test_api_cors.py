"""P4 browser boundary permits only the two local frontend development origins."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_local_frontend_cors_preflight_and_response_headers_are_explicit() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)
    preflight = client.options(
        "/donations",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    response = client.get(
        "/health",
        headers={"Origin": "http://127.0.0.1:3000"},
    )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in preflight.headers["access-control-allow-methods"]
    assert "Content-Type" in preflight.headers["access-control-allow-headers"]
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_unlisted_origin_receives_no_cors_permission() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.get(
        "/health",
        headers={"Origin": "https://example.invalid"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
