import pytest
from app.db.models import Conversation
from sqlalchemy.future import select

@pytest.mark.asyncio
async def test_get_conversations_empty(auth_client):
    response = await auth_client.get("/api/conversations/")
    assert response.status_code == 200
    assert response.json() == {"conversations": []}

@pytest.mark.asyncio
async def test_get_conversations(auth_client, db_session, test_user):
    conv = Conversation(user_id=test_user.id, title="Test", mode="auto")
    db_session.add(conv)
    await db_session.commit()

    response = await auth_client.get("/api/conversations/")
    assert response.status_code == 200
    assert len(response.json()["conversations"]) == 1
    assert response.json()["conversations"][0]["title"] == "Test"

@pytest.mark.asyncio
async def test_get_messages_unauthorized(auth_client, db_session, test_user_2):
    # test_user_2 owns this conversation
    conv = Conversation(user_id=test_user_2.id, title="Test 2", mode="auto")
    db_session.add(conv)
    await db_session.commit()

    # auth_client is test_user, so it should not be able to access test_user_2's conversation
    response = await auth_client.get(f"/api/conversations/{conv.id}/messages")
    assert response.status_code == 404
