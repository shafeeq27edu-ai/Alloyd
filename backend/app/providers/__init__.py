import logging

from app.config import settings
from app.providers.registry import ProviderRegistry
from app.providers.groq_adapter import GroqAdapter
from app.providers.anthropic_adapter import AnthropicAdapter
from app.providers.gemini_adapter import GeminiAdapter

# Register providers
ProviderRegistry.register("groq", GroqAdapter)
ProviderRegistry.register("anthropic", AnthropicAdapter)
ProviderRegistry.register("gemini", GeminiAdapter)

if settings.ENABLE_MOCK_PROVIDER:
    from app.providers.mock_adapter import MockAdapter

    # End-to-end tests only. The compose stack leaves this off by default.
    ProviderRegistry.register("mock", MockAdapter)
    logging.getLogger("alloyd.api").warning(
        "ENABLE_MOCK_PROVIDER is on: the mock provider serves chat without network calls. "
        "Never enable this in production."
    )
