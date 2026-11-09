import pytest
from httpx import AsyncClient, ASGITransport

from app.api import auth as auth_module
from app.main import app


@pytest.mark.asyncio
async def test_health_is_liveness_only():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_checks_the_database():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_valid_request_id_is_echoed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health", headers={"X-Request-ID": "trace-123_ABC"})

    assert response.headers["X-Request-ID"] == "trace-123_ABC"


@pytest.mark.asyncio
async def test_unsafe_request_id_is_replaced():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health", headers={"X-Request-ID": "bad id with spaces"})

    request_id = response.headers["X-Request-ID"]
    assert request_id != "bad id with spaces"
    assert len(request_id) == 32
    int(request_id, 16)


def test_cookie_settings_follow_configured_scope(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "COOKIE_DOMAIN", ".example.com")
    monkeypatch.setattr(auth_module.settings, "COOKIE_SECURE", True)

    cookie_settings = auth_module._auth_cookie_settings()

    assert cookie_settings["domain"] == ".example.com"
    assert cookie_settings["secure"] is True
    assert cookie_settings["httponly"] is True
    assert cookie_settings["samesite"] == "lax"
    assert cookie_settings["path"] == "/"
