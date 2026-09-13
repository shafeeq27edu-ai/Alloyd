from app.providers.registry import ProviderRegistry
from app.providers.groq_adapter import GroqAdapter
from app.providers.anthropic_adapter import AnthropicAdapter
from app.providers.gemini_adapter import GeminiAdapter

# Register providers
ProviderRegistry.register("groq", GroqAdapter)
ProviderRegistry.register("anthropic", AnthropicAdapter)
ProviderRegistry.register("gemini", GeminiAdapter)
