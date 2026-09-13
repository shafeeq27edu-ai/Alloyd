import pytest
from app.db.models import ProviderKey
from sqlalchemy.future import select

@pytest.mark.asyncio
async def test_add_key(auth_client, db_session, test_user):
    response = await auth_client.post(
        "/api/keys/",
        json={"provider_name": "groq", "key": "mysecretkey"}
    )
    assert response.status_code == 201

    # Check db
    result = await db_session.execute(select(ProviderKey).where(ProviderKey.user_id == test_user.id))
    key = result.scalars().first()
    assert key is not None
    assert key.key_hint == "tkey" # last 4 of mysecretkey
    assert key.encrypted_key != "mysecretkey" # It should be encrypted

@pytest.mark.asyncio
async def test_get_keys(auth_client, db_session, test_user):
    response = await auth_client.post(
        "/api/keys/",
        json={"provider_name": "groq", "key": "mysecretkey"}
    )
    assert response.status_code == 201

    response = await auth_client.get("/api/keys/")
    assert response.status_code == 200
    keys = response.json()["keys"]
    assert len(keys) == 1
    assert keys[0]["provider_name"] == "groq"
    assert "tkey" in keys[0]["masked_key"]
    assert "mysecretkey" not in keys[0]["masked_key"]

@pytest.mark.asyncio
async def test_delete_key(auth_client, db_session, test_user):
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "mysecretkey"})
    
    response = await auth_client.delete("/api/keys/groq")
    assert response.status_code == 204

    # Verify deleted
    response = await auth_client.get("/api/keys/")
    assert len(response.json()["keys"]) == 0

@pytest.mark.asyncio
async def test_delete_other_user_key(auth_client, db_session, test_user_2):
    # Setup key for user 2
    from app.core.encryption import encrypt_key
    key = ProviderKey(user_id=test_user_2.id, provider_name="groq", encrypted_key=encrypt_key("secret"), key_hint="cret")
    db_session.add(key)
    await db_session.commit()

    # user 1 tries to delete
    response = await auth_client.delete("/api/keys/groq")
    assert response.status_code == 404
