import pytest

@pytest.mark.asyncio
async def test_register(async_client):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "test-password-123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_register_duplicate(async_client, test_user):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "test-password-123"}
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_register_short_password(async_client):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "short-passw"} # 11 chars
    )
    assert response.status_code == 422
    assert "at least 12 characters" in response.text

@pytest.mark.asyncio
async def test_register_exact_12_password(async_client):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "exact12@example.com", "password": "exact12chars"} # 12 chars
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_register_exceeds_byte_limit(async_client):
    # password that exceeds 72 bytes. "a" * 73 is 73 bytes.
    # We can also use a 37-character multibyte string to easily exceed 72 bytes.
    # 'a' * 73
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "long@example.com", "password": "a" * 73}
    )
    assert response.status_code == 422
    assert "too long" in response.text

@pytest.mark.asyncio
async def test_register_multibyte_near_boundary(async_client):
    # 24 times '😊' is 24 * 4 = 96 bytes, which exceeds 72 bytes, even though it's 24 chars (satisfies min 12).
    # Wait, '😊' is 4 bytes. 18 * 4 = 72 bytes.
    # 18 '😊' is exactly 72 bytes and 18 chars (>=12).
    # 19 '😊' is 76 bytes.
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "multibyte@example.com", "password": "😊" * 19}
    )
    assert response.status_code == 422
    assert "too long" in response.text
    
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "multibyte2@example.com", "password": "😊" * 18}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_login(async_client, test_user):
    response = await async_client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "test-password-123"}
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
