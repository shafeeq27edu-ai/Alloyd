import pytest
import json
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_chat_auto_routing(auth_client, db_session):
    # Add key first
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "validkey"})
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "hello world"}
    )
    assert response.status_code == 200
    
    # Check SSE content
    # In httpx, async response generation requires streaming or just reading the body if not strictly streaming client
    text = response.text
    assert "event: routing" in text
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
    await auth_client.post("/api/keys/", json={"provider_name": "groq", "key": "validkey"})
    await auth_client.post("/api/keys/", json={"provider_name": "anthropic", "key": "validkey"})
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "auto", "message": "@architect how do we do this?"}
    )
    assert response.status_code == 200
    text = response.text
    
    # We should see the routing category
    assert '"category": "PLANNING_DECISION"' in text
    # The mock provider echoes the system prompt
    assert "You are an expert system architect" in text

@pytest.mark.asyncio
async def test_chat_error_handling(auth_client):
    await auth_client.post("/api/keys/", json={"provider_name": "mock", "key": "invalid"})
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "manual", "provider": "mock", "model": "mock-model", "message": "hello"}
    )
    assert response.status_code == 200
    text = response.text
    # Should get INVALID_API_KEY from mock
    assert "event: error" in text
    assert "INVALID_API_KEY" in text

@pytest.mark.asyncio
async def test_chat_rate_limit(auth_client):
    await auth_client.post("/api/keys/", json={"provider_name": "mock", "key": "rate_limit"})
    
    response = await auth_client.post(
        "/api/chat/",
        json={"mode": "manual", "provider": "mock", "model": "mock-model", "message": "hello"}
    )
    assert response.status_code == 200
    text = response.text
    # Should get RATE_LIMIT from mock
    assert "event: error" in text
    assert "RATE_LIMIT" in text
