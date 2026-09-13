import pytest

@pytest.mark.asyncio
async def test_register(async_client):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_register_duplicate(async_client, test_user):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_login(async_client, test_user):
    response = await async_client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "password"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_unauthenticated(async_client):
    response = await async_client.get("/api/auth/me")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_authenticated(auth_client, test_user):
    response = await auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
