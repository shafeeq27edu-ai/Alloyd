import copy

import pytest

from app.core.router import RuleRouter, TaskCategory, validate_catalog
from app.providers.base import BaseProviderAdapter, ModelDefinition
from app.providers.registry import ProviderRegistry
from app.providers.anthropic_adapter import AnthropicAdapter
from app.providers.gemini_adapter import GeminiAdapter
from app.providers.groq_adapter import GroqAdapter


def real_catalog():
    return {
        "groq": GroqAdapter().get_models(),
        "anthropic": AnthropicAdapter().get_models(),
        "gemini": GeminiAdapter().get_models(),
    }


class TempAdapter(BaseProviderAdapter):
    @property
    def provider_name(self) -> str:
        return "temp"

    def get_models(self):
        return [
            ModelDefinition(id="temp-large", name="Temp Large", capabilities=["chat"]),
            ModelDefinition(id="temp-fast", name="Temp Fast", capabilities=["chat", "fast"]),
        ]

    async def send_message(self, api_key, model_id, messages):
        return "ok"

    async def validate_key(self, api_key):
        return None

    async def stream_chat(self, api_key, model_id, messages):
        yield ("done", "")


@pytest.fixture
def temp_provider():
    ProviderRegistry.register("temp", TempAdapter)
    yield
    ProviderRegistry._providers.pop("temp", None)


def test_catalog_model_ids_are_current():
    assert {m.id for m in GroqAdapter().get_models()} == {
        "llama-3.3-70b-versatile", "llama-3.1-8b-instant",
    }
    assert {m.id for m in AnthropicAdapter().get_models()} == {
        "claude-sonnet-5-5", "claude-haiku-5-5",
    }
    assert {m.id for m in GeminiAdapter().get_models()} == {
        "gemini-4-argon", "gemini-3.8-flash",
    }


def test_router_config_matches_real_catalog():
    config = RuleRouter.load_config()
    validate_catalog(config, real_catalog())


def test_router_config_has_no_image_category():
    config = RuleRouter.load_config()
    assert "IMAGE_GENERATION" not in config["routes"]
    assert "IMAGE_GENERATION" not in {c.value for c in TaskCategory}


def test_validate_catalog_rejects_unknown_model():
    config = copy.deepcopy(RuleRouter.load_config())
    config["routes"]["GENERAL"]["primary"] = {
        "provider": "groq", "model": "llama3-8b-8192",
    }
    with pytest.raises(ValueError, match="unknown model"):
        validate_catalog(config, real_catalog())


def test_validate_catalog_rejects_unknown_provider():
    config = copy.deepcopy(RuleRouter.load_config())
    config["routes"]["GENERAL"]["primary"] = {
        "provider": "nope", "model": "whatever",
    }
    with pytest.raises(ValueError, match="unknown provider"):
        validate_catalog(config, real_catalog())


def test_validate_catalog_requires_every_category():
    config = copy.deepcopy(RuleRouter.load_config())
    del config["routes"]["GENERAL"]
    with pytest.raises(ValueError, match="missing categories"):
        validate_catalog(config, real_catalog())


def test_validate_catalog_rejects_unknown_category():
    config = copy.deepcopy(RuleRouter.load_config())
    config["routes"]["IMAGE_GENERATION"] = config["routes"]["GENERAL"]
    with pytest.raises(ValueError, match="unknown categories"):
        validate_catalog(config, real_catalog())


def test_registry_helpers(temp_provider):
    assert ProviderRegistry.fast_model("temp") == "temp-fast"
    assert ProviderRegistry.has_model("temp", "temp-large") is True
    assert ProviderRegistry.has_model("temp", "missing") is False
    assert ProviderRegistry.has_model("nope", "x") is False
    assert {m.id for m in ProviderRegistry.all_models()["temp"]} == {"temp-large", "temp-fast"}

    payload = {item["provider"]: item for item in ProviderRegistry.catalog_payload()}
    assert payload["temp"]["models"][1]["id"] == "temp-fast"


@pytest.mark.asyncio
async def test_models_endpoint_requires_auth(async_client):
    response = await async_client.get("/api/models")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_models_endpoint_returns_catalog(auth_client):
    response = await auth_client.get("/api/models")
    assert response.status_code == 200
    providers = {item["provider"]: item for item in response.json()["providers"]}
    assert "mock" in providers
    assert providers["mock"]["models"][0]["id"] == "mock-model"
