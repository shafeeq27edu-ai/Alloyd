import pytest
import json
from httpx import AsyncClient
from app.db.models import ProviderKey, Conversation, Message
from app.core.encryption import encrypt_key
from app.api.chat import _resolve_legacy_route
from app.config import settings
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


@pytest.mark.asyncio
async def test_chat_model_unavailable_fallback(auth_client, db_session, test_user, caplog):
    await _add_key(db_session, test_user.id, "groq", "model_unavailable")
    await _add_key(db_session, test_user.id, "gemini", "validkey")

    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    assert text.count("event: routing") == 2
    assert '"provider": "gemini"' in text
    assert "mock response" in text
    assert "Model unavailable" in caplog.text


@pytest.mark.asyncio
async def test_chat_manual_error_never_falls_back(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "mock", "rate_limit")
    await _add_key(db_session, test_user.id, "gemini", "validkey")

    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "manual", "provider": "mock", "model": "mock-model", "message": "hello"}
    )
    text = response.text
    assert text.count("event: routing") == 1
    assert "event: error" in text
    assert "RATE_LIMIT" in text
    assert '"provider": "gemini"' not in text


@pytest.mark.asyncio
async def test_chat_first_chunk_timeout_falls_back(auth_client, db_session, test_user, monkeypatch):
    monkeypatch.setattr(settings, "PROVIDER_FIRST_CHUNK_TIMEOUT_SECONDS", 0.01)
    await _add_key(db_session, test_user.id, "groq", "slow")
    await _add_key(db_session, test_user.id, "gemini", "validkey")

    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    assert text.count("event: routing") == 2
    assert '"provider": "gemini"' in text
    assert "mock response" in text


@pytest.mark.asyncio
async def test_chat_stream_headers(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "groq", "validkey")

    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    assert response.headers["cache-control"] == "no-cache, no-transform"
    assert response.headers["x-accel-buffering"] == "no"


def test_legacy_null_mode_resolves_to_auto():
    mode, notice = _resolve_legacy_route(None, None, None)
    assert mode == "auto"
    assert "predates routing modes" in notice


def test_legacy_retired_model_resolves_to_auto():
    mode, notice = _resolve_legacy_route("manual", "groq", "llama3-8b-8192")
    assert mode == "auto"
    assert "no longer available" in notice


def test_valid_manual_route_is_untouched():
    mode, notice = _resolve_legacy_route("manual", "mock", "mock-model")
    assert mode == "manual"
    assert notice is None


@pytest.mark.asyncio
async def test_chat_legacy_retired_model_uses_auto(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "groq", "validkey")
    conversation = Conversation(
        user_id=test_user.id, title="legacy", mode="manual",
        provider="groq", model="llama3-8b-8192"
    )
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello", "conversation_id": conversation.id}
    )
    text = response.text
    assert '"mode": "auto"' in text
    assert "no longer available" in text


@pytest.mark.asyncio
async def test_chat_rejects_oversized_message(auth_client):
    response = await auth_client.post(
        "/api/chat/",
        json={"message": "x" * 20001}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_switch_mode_on_existing_conversation(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "mock", "validkey")
    conversation = Conversation(
        user_id=test_user.id, title="switch", mode="auto", provider=None, model=None
    )
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    response = await auth_client.post(
        "/api/chat/",
        json={
            "mode": "manual", "provider": "mock", "model": "mock-model",
            "message": "hello", "conversation_id": conversation.id,
        },
    )
    text = response.text
    assert '"mode": "manual"' in text
    assert '"provider": "mock"' in text

    await db_session.refresh(conversation)
    assert conversation.mode == "manual"
    assert conversation.provider == "mock"
    assert conversation.model == "mock-model"


@pytest.mark.asyncio
async def test_chat_undecryptable_key_returns_actionable_error(auth_client, db_session, test_user):
    db_session.add(ProviderKey(
        user_id=test_user.id, provider_name="groq",
        encrypted_key="not-a-valid-token", key_hint="test",
    ))
    await db_session.commit()

    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"},
    )
    assert response.status_code == 400
    assert "re-save" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_request_body_limit(async_client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_REQUEST_BYTES", 64)
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "large@example.com", "password": "x" * 100}
    )
    assert response.status_code == 413


async def _stored_rows(db_session):
    conversations = (await db_session.execute(select(Conversation))).scalars().all()
    messages = (await db_session.execute(select(Message).order_by(Message.created_at))).scalars().all()
    return conversations, messages


@pytest.mark.asyncio
async def test_failed_manual_route_persists_nothing(auth_client, db_session, test_user):
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "manual", "provider": "mock", "model": "does-not-exist", "message": "hello"},
    )
    assert response.status_code == 400

    conversations, messages = await _stored_rows(db_session)
    assert conversations == []
    assert messages == []


@pytest.mark.asyncio
async def test_missing_provider_key_persists_nothing(auth_client, db_session, test_user):
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "manual", "provider": "mock", "model": "mock-model", "message": "hello"},
    )
    assert response.status_code == 400

    conversations, messages = await _stored_rows(db_session)
    assert conversations == []
    assert messages == []


@pytest.mark.asyncio
async def test_failed_manual_switch_leaves_conversation_and_history_unchanged(
    auth_client, db_session, test_user
):
    await _add_key(db_session, test_user.id, "mock", "validkey")
    conversation = Conversation(user_id=test_user.id, title="stable", mode="auto")
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    response = await auth_client.post(
        "/api/chat/",
        json={
            "mode": "manual", "provider": "mock", "model": "does-not-exist",
            "message": "hello", "conversation_id": conversation.id,
        },
    )
    assert response.status_code == 400

    await db_session.refresh(conversation)
    assert conversation.mode == "auto"
    assert conversation.provider is None
    assert conversation.model is None
    _conversations, messages = await _stored_rows(db_session)
    assert messages == []


@pytest.mark.asyncio
async def test_successful_send_stores_exactly_one_user_message(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "mock", "validkey")

    response = await auth_client.post(
        "/api/chat/", json={"mode": "auto", "message": "hello world"}
    )
    assert response.status_code == 200

    _conversations, messages = await _stored_rows(db_session)
    assert [(m.role, m.content) for m in messages] == [
        ("user", "hello world"),
        ("assistant", "mock response"),
    ]


@pytest.mark.asyncio
async def test_regenerate_reuses_last_user_message_and_replaces_the_answer(
    auth_client, db_session, test_user
):
    await _add_key(db_session, test_user.id, "mock", "validkey")
    conversation = Conversation(user_id=test_user.id, title="regen", mode="auto")
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)
    db_session.add_all([
        Message(conversation_id=conversation.id, role="user", content="first question"),
        Message(conversation_id=conversation.id, role="assistant", content="old answer"),
    ])
    await db_session.commit()

    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "conversation_id": conversation.id, "regenerate": True},
    )
    assert response.status_code == 200
    assert "mock response" in response.text

    _conversations, messages = await _stored_rows(db_session)
    assert [(m.role, m.content) for m in messages] == [
        ("user", "first question"),
        ("assistant", "mock response"),
    ]


@pytest.mark.asyncio
async def test_regenerate_requires_a_user_message(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "mock", "validkey")
    conversation = Conversation(user_id=test_user.id, title="empty", mode="auto")
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "conversation_id": conversation.id, "regenerate": True},
    )
    assert response.status_code == 400
    _conversations, messages = await _stored_rows(db_session)
    assert messages == []


@pytest.mark.asyncio
async def test_regenerate_requires_a_conversation(auth_client):
    response = await auth_client.post(
        "/api/chat/", json={"mode": "auto", "message": "hello", "regenerate": True}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_trimmed_history_is_announced(auth_client, db_session, test_user, monkeypatch):
    monkeypatch.setattr(settings, "HISTORY_MAX_CHARS", 20)
    await _add_key(db_session, test_user.id, "mock", "validkey")
    conversation = Conversation(user_id=test_user.id, title="long", mode="auto")
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)
    db_session.add_all([
        Message(conversation_id=conversation.id, role="user", content="o" * 40),
        Message(conversation_id=conversation.id, role="assistant", content="a" * 40),
    ])
    await db_session.commit()

    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "latest", "conversation_id": conversation.id},
    )
    assert response.status_code == 200
    assert "omitted to fit the model's context window" in response.text
