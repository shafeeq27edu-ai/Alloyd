import pytest
import json
from httpx import AsyncClient
from app.db.models import ProviderKey
from app.core.encryption import encrypt_key
from sqlalchemy.future import select

async def _add_key(db_session, user_id: str, provider: str, key_value: str):
    """Insert a provider key directly into the database, bypassing API validation.
    This allows chat tests to set up special mock key values (e.g., 'invalid',
    'rate_limit') that would be rejected by validate_key."""
    result = await db_session.execute(
        select(ProviderKey).where(
            ProviderKey.user_id == user_id,
            ProviderKey.provider_name == provider
        )
    )
    existing = result.scalars().first()
    encrypted = encrypt_key(key_value)
    hint = key_value[-4:] if len(key_value) > 4 else ("*" * len(key_value))
    if existing:
        existing.encrypted_key = encrypted
        existing.key_hint = hint
    else:
        db_session.add(ProviderKey(
            user_id=user_id, provider_name=provider,
            encrypted_key=encrypted, key_hint=hint
        ))
    await db_session.commit()

@pytest.mark.asyncio
async def test_chat_auto_routing(auth_client, db_session, test_user):
    # 1. primary provider success -> no fallback
    await _add_key(db_session, test_user.id, "groq", "validkey")
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello world"}
    )
    assert response.status_code == 200
    text = response.text
    # Should only route once
    assert text.count("event: routing") == 1
    assert '"mode": "auto"' in text
    assert "event: message" in text
    assert "mock response" in text
    assert "event: done" in text

@pytest.mark.asyncio
async def test_chat_manual_override(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "mock", "validkey")
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "manual", "provider": "mock", "model": "mock-model", "message": "hello world"}
    )
    assert response.status_code == 200
    text = response.text
    assert "event: routing" in text
    assert '"mode": "manual"' in text
    assert '"provider": "mock"' in text

@pytest.mark.asyncio
async def test_chat_skills_injection(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "anthropic", "validkey")
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "@brainstormer how do we do this?"}
    )
    assert response.status_code == 200
    text = response.text
    
    # We should see the routing category
    assert '"category": "PLANNING_DECISION"' in text
    # The mock provider echoes the system prompt
    assert "Generate and evaluate ideas" in text

@pytest.mark.asyncio
async def test_chat_timeout_fallback(auth_client, db_session, test_user):
    # 2. primary timeout -> fallback
    await _add_key(db_session, test_user.id, "groq", "timeout")
    await _add_key(db_session, test_user.id, "gemini", "validkey")
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    # Groq failed, should route again to gemini
    assert text.count("event: routing") == 2
    assert '"provider": "gemini"' in text
    assert "mock response" in text

@pytest.mark.asyncio
async def test_chat_rate_limit_fallback(auth_client, db_session, test_user):
    # 3. primary rate limit -> fallback
    await _add_key(db_session, test_user.id, "groq", "rate_limit")
    await _add_key(db_session, test_user.id, "gemini", "validkey")
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    assert text.count("event: routing") == 2
    assert '"provider": "gemini"' in text

@pytest.mark.asyncio
async def test_chat_unavailable_fallback(auth_client, db_session, test_user):
    # 4. primary unavailable -> fallback
    await _add_key(db_session, test_user.id, "groq", "unavailable")
    await _add_key(db_session, test_user.id, "gemini", "validkey")
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    assert text.count("event: routing") == 2
    assert '"provider": "gemini"' in text

@pytest.mark.asyncio
async def test_chat_invalid_api_key_no_fallback(auth_client, db_session, test_user):
    # 5. primary invalid API key -> NO fallback
    await _add_key(db_session, test_user.id, "groq", "invalid")
    await _add_key(db_session, test_user.id, "gemini", "validkey")
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    # Should only route once, no fallback
    assert text.count("event: routing") == 1
    assert "event: error" in text
    assert "INVALID_API_KEY" in text
    assert '"provider": "gemini"' not in text

@pytest.mark.asyncio
async def test_chat_bad_request_no_fallback(auth_client, db_session, test_user):
    # 6. primary bad request -> NO fallback
    await _add_key(db_session, test_user.id, "groq", "bad_request")
    await _add_key(db_session, test_user.id, "gemini", "validkey")
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    # Should only route once, no fallback
    assert text.count("event: routing") == 1
    assert "event: error" in text
    assert "BAD_REQUEST" in text
    assert '"provider": "gemini"' not in text

@pytest.mark.asyncio
async def test_chat_fallback_success(auth_client, db_session, test_user):
    # 7. fallback success
    await _add_key(db_session, test_user.id, "groq", "rate_limit")
    await _add_key(db_session, test_user.id, "gemini", "validkey")
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    assert text.count("event: routing") == 2
    assert "event: message" in text
    assert "mock response" in text
    assert "event: done" in text

@pytest.mark.asyncio
async def test_chat_fallback_failure(auth_client, db_session, test_user):
    # 8. fallback failure
    await _add_key(db_session, test_user.id, "groq", "rate_limit")
    await _add_key(db_session, test_user.id, "gemini", "rate_limit")
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    assert text.count("event: routing") == 2
    assert "event: error" in text
    assert "RATE_LIMIT" in text

@pytest.mark.asyncio
async def test_chat_no_infinite_retry(auth_client, db_session, test_user):
    # 9. no infinite retry
    # Even if we have more keys that fail, fallback only happens once.
    await _add_key(db_session, test_user.id, "groq", "rate_limit")
    await _add_key(db_session, test_user.id, "gemini", "rate_limit")
    await _add_key(db_session, test_user.id, "anthropic", "rate_limit")
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    # Attempt 1: groq (rate limit -> fallback)
    # Attempt 2: gemini (rate limit -> abort)
    # Never hits anthropic
    assert text.count("event: routing") == 2
    assert text.count("event: error") == 1

