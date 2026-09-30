import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.core.rate_limit import limiter
from app.config import settings

@pytest.mark.asyncio
async def test_login_rate_limit(async_client: AsyncClient, test_user: dict):
    await limiter.clear_for_test()
    # Perform requests up to the limit
    for _ in range(settings.LOGIN_RATE_LIMIT):
        response = await async_client.post(
            "/api/auth/token",
            data={"username": test_user.email, "password": "wrong-password-123"},
            headers={"X-Forwarded-For": "1.2.3.4"}
        )
        assert response.status_code == 401

    # Next request should be rate limited
    response = await async_client.post(
        "/api/auth/token",
        data={"username": test_user.email, "password": "wrong-password-123"},
        headers={"X-Forwarded-For": "1.2.3.4"}
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers

@pytest.mark.asyncio
async def test_register_rate_limit(async_client: AsyncClient):
    await limiter.clear_for_test()
    for i in range(settings.REGISTRATION_RATE_LIMIT):
        response = await async_client.post(
            "/api/auth/register",
            json={"email": f"test{i}@example.com", "password": "test-password-123"},
            headers={"X-Forwarded-For": "5.6.7.8"}
        )
        assert response.status_code == 200

    response = await async_client.post(
        "/api/auth/register",
        json={"email": f"test_fail@example.com", "password": "test-password-123"},
        headers={"X-Forwarded-For": "5.6.7.8"}
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
