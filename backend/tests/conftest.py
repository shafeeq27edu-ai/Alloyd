import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
import asyncio
import os
from cryptography.fernet import Fernet

# CI sets TEST_DATABASE_URL so the suite runs on Postgres; local runs default to
# an in-memory SQLite database for speed.
DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL"] = DATABASE_URL
os.environ["SECRET_KEY"] = "this_is_a_mock_secret_key_for_tests_that_is_long_enough"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
# Tests run over plain HTTP; turn off Secure cookies for the test client only.
os.environ["DEBUG"] = "true"

from app.main import app
from app.db import database
from app.db.database import get_db, Base
from app.core.security import get_password_hash
from app.db.models import User
from app.providers.base import BaseProviderAdapter, ModelDefinition
from app.providers.registry import ProviderRegistry
from app.core.errors import ProviderError, ErrorCode
from app.core.rate_limit import limiter
from typing import AsyncGenerator, List, Dict, Tuple
import json

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.state.clear()
    yield


# pytest-asyncio gives every test its own event loop, so pooled Postgres
# connections would be reused after their loop closes. NullPool keeps each
# connection scoped to the test that opened it. In-memory SQLite needs the
# default single-connection pool to keep the same database across the run.
_engine_options = (
    {"poolclass": NullPool} if DATABASE_URL.startswith("postgresql") else {}
)
engine = create_async_engine(DATABASE_URL, echo=False, **_engine_options)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture(scope="session", autouse=True)
def use_test_session_factory():
    # Background work (e.g. title generation) opens its own session instead of
    # using the injected request session. Point it at the test engine so it
    # never creates pooled connections on the app engine that outlive the
    # per-test event loop.
    from app.core import title_generator

    original = database.AsyncSessionLocal
    database.AsyncSessionLocal = TestingSessionLocal
    title_generator.AsyncSessionLocal = TestingSessionLocal
    yield
    database.AsyncSessionLocal = original
    title_generator.AsyncSessionLocal = original

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
    user = User(email="test@example.com", hashed_password=get_password_hash("test-password-123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def test_user_2(db_session):
    user = User(email="other@example.com", hashed_password=get_password_hash("test-password-123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def csrf_headers(async_client):
    csrf_response = await async_client.get("/api/auth/csrf")
    csrf_token = csrf_response.json()["csrf_token"]
    return {
        "X-CSRF-Token": csrf_token,
        "Origin": "http://localhost:3000",
    }

@pytest_asyncio.fixture
async def auth_client(async_client, test_user, csrf_headers):
    response = await async_client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "test-password-123"},
        headers=csrf_headers
    )
    assert response.status_code == 200
    # The session lives in the HttpOnly cookie set by the login response.
    async_client.headers.update(csrf_headers)
    return async_client

class MockAdapter(BaseProviderAdapter):
    @property
    def provider_name(self) -> str:
        return "mock"
    def get_models(self) -> List[ModelDefinition]:
        return [ModelDefinition(id="mock-model", name="Mock Model", capabilities=["chat"])]
    
    async def send_message(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> str:
        return "mock response"

    async def validate_key(self, api_key: str) -> None:
        if api_key == "invalid":
            raise ProviderError(ErrorCode.INVALID_API_KEY, self.provider_name, "Invalid mock API key.", False)
        elif api_key == "timeout":
            raise ProviderError(ErrorCode.TIMEOUT, self.provider_name, "Mock timeout.", True)
        elif api_key == "unavailable":
            raise ProviderError(ErrorCode.PROVIDER_UNAVAILABLE, self.provider_name, "Mock unavailable.", True)
        elif api_key == "rate_limit":
            raise ProviderError(ErrorCode.RATE_LIMIT, self.provider_name, "Mock rate limit.", True)
        # Success otherwise

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
        if api_key == "model_unavailable":
            yield ("error", json.dumps(ProviderError(ErrorCode.MODEL_UNAVAILABLE, "mock", "model unavailable", False).to_dict()))
            return
        if api_key == "slow":
            await asyncio.sleep(0.2)

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
