from typing import Dict, Type
from app.providers.base import BaseProviderAdapter

class ProviderRegistry:
    _providers: Dict[str, Type[BaseProviderAdapter]] = {}

    @classmethod
    def register(cls, name: str, adapter: Type[BaseProviderAdapter]):
        cls._providers[name] = adapter

    @classmethod
    def get_adapter(cls, name: str) -> BaseProviderAdapter:
        adapter_class = cls._providers.get(name)
        if not adapter_class:
            raise ValueError(f"Provider '{name}' not found in registry.")
        return adapter_class()
