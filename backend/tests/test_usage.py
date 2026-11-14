import json

import pytest
from sqlalchemy.future import select

from app.core.usage import estimate_cost, parse_prices, resolve_usage
from app.core.encryption import encrypt_key
from app.db.models import Message, ProviderKey, UsageEvent
from app.config import settings


async def _add_key(db_session, user_id: str, provider: str, key_value: str):
    db_session.add(ProviderKey(
        user_id=user_id,
        provider_name=provider,
        encrypted_key=encrypt_key(key_value),
        key_hint=key_value[-4:],
    ))
    await db_session.commit()


def _sse_events(text: str) -> list[tuple[str, str]]:
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        name = "message"
        data = []
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line[len("event: "):]
            elif line.startswith("data: "):
                data.append(line[len("data: "):])
        events.append((name, "\n".join(data)))
    return events


async def _usage_rows(db_session) -> list[UsageEvent]:
    result = await db_session.execute(select(UsageEvent).order_by(UsageEvent.created_at))
    return list(result.scalars().all())


async def _conversation_id(response_text: str) -> str:
    for name, data in _sse_events(response_text):
        if name == "routing":
            return json.loads(data)["conversation_id"]
    raise AssertionError("no routing event in response")


def test_resolve_usage_prefers_provider_counts():
    messages = [{"role": "user", "content": "x" * 400}]
    assert resolve_usage({"input_tokens": 30, "output_tokens": 12}, messages, "y" * 40) == (
        30, 12, "provider"
    )


def test_resolve_usage_estimates_missing_counts():
    messages = [{"role": "user", "content": "x" * 400}]
    input_tokens, output_tokens, source = resolve_usage(None, messages, "y" * 40)
    assert (input_tokens, output_tokens, source) == (100, 10, "estimated")


def test_estimated_usage_is_labelled_when_only_one_count_arrives():
    messages = [{"role": "user", "content": "x" * 8}]
    input_tokens, output_tokens, source = resolve_usage(
        {"input_tokens": 5, "output_tokens": None}, messages, "y" * 8
    )
    assert (input_tokens, output_tokens, source) == (5, 2, "estimated")


def test_parse_prices_rejects_bad_values():
    with pytest.raises(ValueError):
        parse_prices('{"groq/x": {"input": -1, "output": 1}}')
    with pytest.raises(ValueError):
        parse_prices("not json")
    assert parse_prices("") == {}


def test_price_table_computes_cost_and_leaves_unknown_models_unpriced():
    prices = parse_prices('{"groq/openai/gpt-oss-20b": {"input": 1.0, "output": 2.0}}')
    assert estimate_cost("groq", "openai/gpt-oss-20b", 12, 4, prices) == 0.00002
    assert estimate_cost("groq", "unknown-model", 12, 4, prices) is None


@pytest.mark.asyncio
async def test_successful_message_records_usage_without_content(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "groq", "validkey")
    prompt = "hello world, this prompt must never be stored in usage"

    response = await auth_client.post("/api/chat/", json={"mode": "auto", "message": prompt})
    assert response.status_code == 200

    events = _sse_events(response.text)
    names = [name for name, _ in events]
    assert "usage" in names
    assert names.index("usage") < names.index("done")

    usage_event = dict(events)["usage"]
    payload = json.loads(usage_event)
    assert payload["input_tokens"] == 12
    assert payload["output_tokens"] == 4
    assert payload["token_source"] == "provider"
    assert payload["estimated_cost_usd"] is None

    rows = await _usage_rows(db_session)
    assert len(rows) == 1
    row = rows[0]
    assert row.provider == "groq"
    assert row.status == "success"
    assert row.mode == "auto"
    assert row.category == "GENERAL"
    assert row.fallback_from is None
    assert row.token_source == "provider"
    assert row.estimated_cost_usd is None
    assert row.latency_ms >= 0
    assert row.message_id is not None

    assistant = await db_session.execute(
        select(Message).where(Message.role == "assistant")
    )
    assistant_message = assistant.scalars().one()
    assert row.message_id == assistant_message.id

    # The event must not retain the prompt or the response text.
    assert "content" not in UsageEvent.__table__.columns
    for value in vars(row).values():
        assert prompt not in str(value)


@pytest.mark.asyncio
async def test_failed_message_records_error_usage(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "groq", "invalid")

    response = await auth_client.post("/api/chat/", json={"mode": "auto", "message": "hello"})
    assert response.status_code == 200
    assert "INVALID_API_KEY" in response.text

    rows = await _usage_rows(db_session)
    assert len(rows) == 1
    assert rows[0].status == "error"
    assert rows[0].error_code == "INVALID_API_KEY"
    assert rows[0].message_id is None
    assert rows[0].input_tokens is None
    assert rows[0].estimated_cost_usd is None


@pytest.mark.asyncio
async def test_fallback_records_both_attempts(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "groq", "timeout")
    await _add_key(db_session, test_user.id, "gemini", "validkey")

    response = await auth_client.post("/api/chat/", json={"mode": "auto", "message": "hello"})
    assert response.status_code == 200
    assert response.text.count("event: routing") == 2

    rows = await _usage_rows(db_session)
    assert len(rows) == 2
    failed, succeeded = rows
    assert (failed.provider, failed.status, failed.error_code) == ("groq", "error", "TIMEOUT")
    assert failed.fallback_from is None
    assert succeeded.provider == "gemini"
    assert succeeded.status == "success"
    assert succeeded.fallback_from == f"groq/{failed.model}"
    assert succeeded.message_id is not None


@pytest.mark.asyncio
async def test_cost_uses_configured_prices(auth_client, db_session, test_user, monkeypatch):
    monkeypatch.setattr(
        settings,
        "PRICING_JSON",
        '{"groq/openai/gpt-oss-20b": {"input": 1.0, "output": 2.0}}',
    )
    await _add_key(db_session, test_user.id, "groq", "validkey")

    response = await auth_client.post("/api/chat/", json={"mode": "auto", "message": "hello"})
    assert response.status_code == 200

    rows = await _usage_rows(db_session)
    assert rows[0].estimated_cost_usd == pytest.approx(0.00002)
    assert json.loads(dict(_sse_events(response.text))["usage"])["estimated_cost_usd"] == pytest.approx(0.00002)


@pytest.mark.asyncio
async def test_messages_endpoint_returns_usage_for_assistant_only(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "groq", "validkey")
    response = await auth_client.post("/api/chat/", json={"mode": "auto", "message": "hello"})
    conversation_id = await _conversation_id(response.text)

    messages = (await auth_client.get(f"/api/conversations/{conversation_id}/messages")).json()["messages"]
    user_message = next(m for m in messages if m["role"] == "user")
    assistant_message = next(m for m in messages if m["role"] == "assistant")
    assert user_message["usage"] is None
    assert assistant_message["usage"] == {
        "input_tokens": 12,
        "output_tokens": 4,
        "token_source": "provider",
        "estimated_cost_usd": None,
    }


@pytest.mark.asyncio
async def test_deleting_conversation_removes_its_usage(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "groq", "validkey")
    response = await auth_client.post("/api/chat/", json={"mode": "auto", "message": "hello"})
    conversation_id = await _conversation_id(response.text)
    assert len(await _usage_rows(db_session)) == 1

    deleted = await auth_client.delete(f"/api/conversations/{conversation_id}")
    assert deleted.status_code == 200
    assert await _usage_rows(db_session) == []


@pytest.mark.asyncio
async def test_deleting_account_removes_usage(auth_client, db_session, test_user):
    await _add_key(db_session, test_user.id, "groq", "validkey")
    await auth_client.post("/api/chat/", json={"mode": "auto", "message": "hello"})
    assert len(await _usage_rows(db_session)) == 1

    deleted = await auth_client.request(
        "DELETE", "/api/auth/account", json={"password": "test-password-123"}
    )
    assert deleted.status_code == 200
    assert await _usage_rows(db_session) == []
