import pytest
from httpx import AsyncClient
from starlette.requests import Request
from app.core.rate_limit import get_client_ip, limiter
from app.config import settings


def make_request(peer: str, forwarded: str | None = None) -> Request:
    headers = []
    if forwarded:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


@pytest.mark.asyncio
async def test_login_rate_limit(async_client: AsyncClient, test_user, csrf_headers, monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "127.0.0.1")
    await limiter.clear_for_test()
    # Perform requests up to the limit
    for _ in range(settings.LOGIN_RATE_LIMIT):
        response = await async_client.post(
            "/api/auth/token",
            data={"username": test_user.email, "password": "wrong-password-123"},
            headers={**csrf_headers, "X-Forwarded-For": "1.2.3.4"}
        )
        assert response.status_code == 401

    # Next request should be rate limited
    response = await async_client.post(
        "/api/auth/token",
        data={"username": test_user.email, "password": "wrong-password-123"},
        headers={**csrf_headers, "X-Forwarded-For": "1.2.3.4"}
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_register_rate_limit(async_client: AsyncClient, csrf_headers, monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "127.0.0.1")
    await limiter.clear_for_test()
    headers = {**csrf_headers, "X-Forwarded-For": "5.6.7.8"}
    for i in range(settings.REGISTRATION_RATE_LIMIT):
        response = await async_client.post(
            "/api/auth/register",
            json={"email": f"test{i}@example.com", "password": "test-password-123"},
            headers=headers
        )
        assert response.status_code == 200

    response = await async_client.post(
        "/api/auth/register",
        json={"email": "test_fail@example.com", "password": "test-password-123"},
        headers=headers
    )
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_chat_rate_limit(async_client: AsyncClient, auth_client: AsyncClient):
    await limiter.clear_for_test()
    # Fetch CSRF token
    csrf_response = await auth_client.get("/api/auth/csrf")
    csrf_token = csrf_response.json()["csrf_token"]
    
    headers = {
        "X-CSRF-Token": csrf_token,
        "Origin": "http://localhost:3000"
    }

    # Setup API key to avoid 400 Bad Request
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "testkey"}, headers=headers)

    # Simulate messages up to the limit
    for _ in range(settings.CHAT_RATE_LIMIT):
        response = await auth_client.post(
            "/api/chat/",
            json={"message": "hello"},
            headers=headers
        )
        assert response.status_code == 200

    # Next message should fail with 429 before streaming
    response = await auth_client.post(
        "/api/chat/",
        json={"message": "hello again"},
        headers=headers
    )
    assert response.status_code == 429


def test_forwarded_for_ignored_from_untrusted_peer(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "")
    assert get_client_ip(make_request("127.0.0.1", "1.2.3.4")) == "127.0.0.1"


def test_forwarded_for_used_from_trusted_proxy(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "127.0.0.1")
    assert get_client_ip(make_request("127.0.0.1", "1.2.3.4, 5.6.7.8")) == "1.2.3.4"


def test_forwarded_for_used_from_trusted_cidr(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "10.0.0.0/8")
    assert get_client_ip(make_request("10.1.2.3", "9.9.9.9")) == "9.9.9.9"


def test_invalid_trusted_proxy_entry_is_ignored(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "not-an-ip")
    assert get_client_ip(make_request("127.0.0.1", "1.2.3.4")) == "127.0.0.1"
