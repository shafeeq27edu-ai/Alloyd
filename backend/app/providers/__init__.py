from app.providers.registry import ProviderRegistry
from app.providers.groq_adapter import GroqAdapter
from app.providers.openai_adapter import OpenAIAdapter
from app.providers.gemini_adapter import GeminiAdapter

# Register providers
ProviderRegistry.register("groq", GroqAdapter)
ProviderRegistry.register("openai", OpenAIAdapter)
ProviderRegistry.register("gemini", GeminiAdapter)
