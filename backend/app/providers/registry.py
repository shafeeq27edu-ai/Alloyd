from typing import Dict, List, Type
from app.providers.base import BaseProviderAdapter, ModelDefinition

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

    @classmethod
    def all_models(cls) -> Dict[str, List[ModelDefinition]]:
        return {
            name: cls.get_adapter(name).get_models()
            for name in cls._providers
        }

    @classmethod
    def has_model(cls, provider: str, model_id: str) -> bool:
        adapter_class = cls._providers.get(provider)
        if not adapter_class:
            return False
        return any(m.id == model_id for m in adapter_class().get_models())

    @classmethod
    def fast_model(cls, provider: str) -> str:
        models = cls.get_adapter(provider).get_models()
        if not models:
            raise ValueError(f"Provider '{provider}' has no models in the catalog.")
        for model in models:
            if "fast" in model.capabilities:
                return model.id
        return models[0].id

    @classmethod
    def catalog_payload(cls) -> List[Dict]:
        return [
            {
                "provider": name,
                "models": [
                    {"id": m.id, "name": m.name, "capabilities": m.capabilities}
                    for m in cls.get_adapter(name).get_models()
                ],
            }
            for name in cls._providers
        ]
