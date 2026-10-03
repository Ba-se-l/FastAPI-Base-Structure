import pytest
from httpx import AsyncClient

from src.settings import settings


@pytest.mark.asyncio
async def test_404_not_found_envelope(client: AsyncClient):
    """Verifies that non-existent routes return unified ErrorResponse envelope with 404."""
    response = await client.get("/api/v1/non-existent-route-xyz")
    assert response.status_code == 404

    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Not Found"
    assert "request_id" in data
    assert data["request_id"] is not None
    assert response.headers.get("X-Request-ID") == data["request_id"]


@pytest.mark.asyncio
async def test_405_method_not_allowed_envelope(client: AsyncClient):
    """Verifies that disallowed HTTP methods return unified ErrorResponse envelope with 405."""
    # POST to /health which only supports GET
    response = await client.post("/health")
    assert response.status_code == 405

    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert data["error"]["message"] == "Method Not Allowed"
    assert "request_id" in data
    assert data["request_id"] is not None
    assert response.headers.get("X-Request-ID") == data["request_id"]


@pytest.mark.asyncio
async def test_401_unauthorized_envelope_and_rfc6750_headers(client: AsyncClient):
    """Verifies that unauthenticated access returns ErrorResponse and preserves WWW-Authenticate header."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401

    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "request_id" in data
    assert data["request_id"] is not None
    assert response.headers.get("X-Request-ID") == data["request_id"]

    # Critical RFC 6750 invariant: WWW-Authenticate header must be preserved
    assert "WWW-Authenticate" in response.headers
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_health_probes_contract_exemption(client: AsyncClient):
    """Verifies that health probes return raw un-enveloped JSON per Kubernetes contract exemption."""
    # Liveness probe
    liveness_resp = await client.get("/health")
    assert liveness_resp.status_code == 200
    liveness_data = liveness_resp.json()

    assert liveness_data["status"] == "ok"
    assert liveness_data["version"] == settings.app_version
    assert liveness_data["environment"] == settings.environment.value
    assert "success" not in liveness_data
    assert "error" not in liveness_data

    # Readiness probe
    readiness_resp = await client.get("/health/ready")
    assert readiness_resp.status_code == 200
    readiness_data = readiness_resp.json()

    assert readiness_data["status"] == "ok"
    assert readiness_data["checks"] == {"database": "ok"}
    assert "success" not in readiness_data
    assert "error" not in readiness_data
