from app.providers.registry import ProviderRegistry
from app.providers.groq_adapter import GroqAdapter

# Register providers
ProviderRegistry.register("groq", GroqAdapter)
