import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.main import app
from app.db.database import get_db, Base
from app.core.security import get_password_hash
from app.db.models import User
from app.providers.base import BaseProviderAdapter, ModelDefinition
from app.providers.registry import ProviderRegistry
from app.core.errors import ProviderError, ErrorCode
from typing import AsyncGenerator, List, Dict, Tuple
import json

engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def override_get_db(db_session):
    async def _override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def async_client(override_get_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(email="test@example.com", hashed_password=get_password_hash("password"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def test_user_2(db_session):
    user = User(email="other@example.com", hashed_password=get_password_hash("password"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def auth_client(async_client, test_user):
    response = await async_client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "password"}
    )
    token = response.json()["access_token"]
    async_client.headers = {"Authorization": f"Bearer {token}"}
    return async_client

class MockAdapter(BaseProviderAdapter):
    @property
    def provider_name(self) -> str:
        return "mock"
    def get_models(self) -> List[ModelDefinition]:
        return [ModelDefinition(id="mock-model", name="Mock Model", capabilities=["chat"])]
    
    async def send_message(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> str:
        return "mock response"

    async def stream_chat(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> AsyncGenerator[Tuple[str, str], None]:
        if api_key == "invalid":
            yield ("error", json.dumps(ProviderError(ErrorCode.INVALID_API_KEY, "mock", "invalid key", False).to_dict()))
            return
        if api_key == "bad_request":
            yield ("error", json.dumps(ProviderError(ErrorCode.BAD_REQUEST, "mock", "bad request", False).to_dict()))
            return
        if api_key == "rate_limit":
            yield ("error", json.dumps(ProviderError(ErrorCode.RATE_LIMIT, "mock", "rate limited", True).to_dict()))
            return
        if api_key == "timeout":
            yield ("error", json.dumps(ProviderError(ErrorCode.TIMEOUT, "mock", "timed out", True).to_dict()))
            return
        if api_key == "unavailable":
            yield ("error", json.dumps(ProviderError(ErrorCode.PROVIDER_UNAVAILABLE, "mock", "unavailable", True).to_dict()))
            return
            
        yield ("message", "mock response")
        # Echo the system prompt back to easily test it
        sys_prompts = [m["content"] for m in messages if m["role"] == "system"]
        if sys_prompts:
            yield ("message", " " + sys_prompts[0])
            
        yield ("done", "")

@pytest.fixture(autouse=True)
def setup_mock_provider():
    ProviderRegistry.register("mock", MockAdapter)
    ProviderRegistry.register("groq", MockAdapter)
    ProviderRegistry.register("anthropic", MockAdapter)
    ProviderRegistry.register("gemini", MockAdapter)
    yield
