import pytest
from app.config import settings


def access_token_cookie(response) -> str:
    cookies = [h for h in response.headers.get_list("set-cookie") if h.startswith("access_token=")]
    assert len(cookies) == 1
    return cookies[0].lower()


@pytest.mark.asyncio
async def test_register(async_client, csrf_headers):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "test-password-123"},
        headers=csrf_headers
    )
    assert response.status_code == 200
    assert "access_token" not in response.json()
    assert response.cookies.get("access_token")

    cookie = access_token_cookie(response)
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "secure" not in cookie


@pytest.mark.asyncio
async def test_register_duplicate(async_client, test_user, csrf_headers):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "test-password-123"},
        headers=csrf_headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_requires_csrf(async_client):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "nocsrf@example.com", "password": "test-password-123"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_register_rejects_foreign_origin(async_client, csrf_headers):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "evil@example.com", "password": "test-password-123"},
        headers={**csrf_headers, "Origin": "https://evil.example"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_register_short_password(async_client, csrf_headers):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "short-passw"}, # 11 chars
        headers=csrf_headers
    )
    assert response.status_code == 422
    assert "at least 12 characters" in response.text


@pytest.mark.asyncio
async def test_register_exact_12_password(async_client, csrf_headers):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "exact12@example.com", "password": "exact12chars"}, # 12 chars
        headers=csrf_headers
    )
    assert response.status_code == 200
    assert "access_token" not in response.json()
    assert response.cookies.get("access_token")


@pytest.mark.asyncio
async def test_register_exceeds_byte_limit(async_client, csrf_headers):
    # password that exceeds 72 bytes. "a" * 73 is 73 bytes.
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "long@example.com", "password": "a" * 73},
        headers=csrf_headers
    )
    assert response.status_code == 422
    assert "too long" in response.text


@pytest.mark.asyncio
async def test_register_multibyte_near_boundary(async_client, csrf_headers):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "multibyte@example.com", "password": "😊" * 19},
        headers=csrf_headers
    )
    assert response.status_code == 422
    assert "too long" in response.text
    
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "multibyte2@example.com", "password": "😊" * 18},
        headers=csrf_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login(async_client, test_user, csrf_headers):
    response = await async_client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "test-password-123"},
        headers=csrf_headers
    )
    assert response.status_code == 200
    assert "access_token" not in response.json()
    assert response.cookies.get("access_token")

    cookie = access_token_cookie(response)
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


@pytest.mark.asyncio
async def test_login_requires_csrf(async_client, test_user):
    response = await async_client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "test-password-123"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_cookie_is_secure_when_debug_off(async_client, test_user, csrf_headers, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    response = await async_client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "test-password-123"},
        headers=csrf_headers
    )
    assert response.status_code == 200
    assert "secure" in access_token_cookie(response)


@pytest.mark.asyncio
async def test_unauthenticated(async_client):
    response = await async_client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated(auth_client, test_user):
    response = await auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
