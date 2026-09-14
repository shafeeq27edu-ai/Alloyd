import pytest
import json
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_chat_auto_routing(auth_client, db_session):
    # 1. primary provider success -> no fallback
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "validkey"})
    
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
async def test_chat_manual_override(auth_client):
    await auth_client.post("/api/keys/", json={"provider_name": "mock", "key": "validkey"})
    
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
async def test_chat_skills_injection(auth_client):
    await auth_client.post("/api/keys/", json={"provider_name": "anthropic", "key": "validkey"})
    
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
async def test_chat_timeout_fallback(auth_client):
    # 2. primary timeout -> fallback
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "timeout"})
    await auth_client.post("/api/keys/", json={"provider_name": "gemini", "key": "validkey"})
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    # Groq failed, should route again to anthropic
    assert text.count("event: routing") == 2
    assert '"provider": "gemini"' in text
    assert "mock response" in text

@pytest.mark.asyncio
async def test_chat_rate_limit_fallback(auth_client):
    # 3. primary rate limit -> fallback
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "rate_limit"})
    await auth_client.post("/api/keys/", json={"provider_name": "gemini", "key": "validkey"})
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    assert text.count("event: routing") == 2
    assert '"provider": "gemini"' in text

@pytest.mark.asyncio
async def test_chat_unavailable_fallback(auth_client):
    # 4. primary unavailable -> fallback
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "unavailable"})
    await auth_client.post("/api/keys/", json={"provider_name": "gemini", "key": "validkey"})
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    assert text.count("event: routing") == 2
    assert '"provider": "gemini"' in text

@pytest.mark.asyncio
async def test_chat_invalid_api_key_no_fallback(auth_client):
    # 5. primary invalid API key -> NO fallback
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "invalid"})
    await auth_client.post("/api/keys/", json={"provider_name": "gemini", "key": "validkey"})
    
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
async def test_chat_bad_request_no_fallback(auth_client):
    # 6. primary bad request -> NO fallback
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "bad_request"})
    await auth_client.post("/api/keys/", json={"provider_name": "gemini", "key": "validkey"})
    
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
async def test_chat_fallback_success(auth_client):
    # 7. fallback success
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "rate_limit"})
    await auth_client.post("/api/keys/", json={"provider_name": "gemini", "key": "validkey"})
    
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
async def test_chat_fallback_failure(auth_client):
    # 8. fallback failure
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "rate_limit"})
    await auth_client.post("/api/keys/", json={"provider_name": "gemini", "key": "rate_limit"})
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello"}
    )
    text = response.text
    assert text.count("event: routing") == 2
    assert "event: error" in text
    assert "RATE_LIMIT" in text

@pytest.mark.asyncio
async def test_chat_no_infinite_retry(auth_client):
    # 9. no infinite retry
    # Even if we have more keys that fail, fallback only happens once.
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "rate_limit"})
    await auth_client.post("/api/keys/", json={"provider_name": "gemini", "key": "rate_limit"})
    await auth_client.post("/api/keys/", json={"provider_name": "anthropic", "key": "rate_limit"})
    
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
