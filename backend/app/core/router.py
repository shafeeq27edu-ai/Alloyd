import yaml
from enum import Enum
from typing import Tuple, Dict, Any, Optional
from pathlib import Path
from app.providers.registry import ProviderRegistry

class TaskCategory(Enum):
    CODING = "CODING"
    RESEARCH = "RESEARCH"
    WRITING = "WRITING"
    PLANNING_DECISION = "PLANNING_DECISION"
    GENERAL = "GENERAL"

class RuleRouter:
    _config: Dict[str, Any] = {}
    CONFIG_PATH = Path(__file__).parent.parent.parent / "router_config.yaml"

    @classmethod
    def load_config(cls, path: Optional[Path] = None) -> Dict[str, Any]:
        config_path = Path(path) if path is not None else cls.CONFIG_PATH
        if path is not None or not cls._config:
            with open(config_path, "r") as f:
                cls._config = yaml.safe_load(f)
        return cls._config

    @classmethod
    def load_and_validate(cls) -> Dict[str, Any]:
        config = cls.load_config()
        validate_catalog(config)
        return config

    @classmethod
    def route(cls, category: TaskCategory, provider_availability: Dict[str, bool]) -> Tuple[str, str]:
        config = cls.load_config()
        route_info = config["routes"].get(category.value) or config["routes"][TaskCategory.GENERAL.value]

        primary = route_info["primary"]
        if provider_availability.get(primary["provider"], False):
            return primary["provider"], primary["model"]

        fallback = route_info["fallback"]
        return fallback["provider"], fallback["model"]


def validate_catalog(config: Dict[str, Any], catalog: Optional[Dict[str, list]] = None) -> None:
    """Fail fast if router_config references a provider or model outside the adapter catalog."""
    routes = (config or {}).get("routes")
    if not isinstance(routes, dict) or not routes:
        raise ValueError("Router config has no routes.")

    catalog = catalog if catalog is not None else ProviderRegistry.all_models()
    known_categories = {category.value for category in TaskCategory}
    missing = known_categories - set(routes)
    if missing:
        raise ValueError(f"Router config is missing categories: {', '.join(sorted(missing))}.")
    unknown = set(routes) - known_categories
    if unknown:
        raise ValueError(f"Router config has unknown categories: {', '.join(sorted(unknown))}.")

    for category, route in routes.items():
        for slot in ("primary", "fallback"):
            target = route.get(slot)
            if not isinstance(target, dict) or not target.get("provider") or not target.get("model"):
                raise ValueError(f"Router config {category}.{slot} must define provider and model.")
            provider = target["provider"]
            model = target["model"]
            if provider not in catalog:
                raise ValueError(
                    f"Router config {category}.{slot} references unknown provider '{provider}'."
                )
            if model not in {m.id for m in catalog[provider]}:
                raise ValueError(
                    f"Router config {category}.{slot} references unknown model "
                    f"'{model}' for provider '{provider}'."
                )
