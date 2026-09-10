import yaml
from enum import Enum
from typing import Tuple, Dict, Any
from pathlib import Path

class TaskCategory(Enum):
    WRITING = "WRITING"
    IMAGE_GENERATION = "IMAGE_GENERATION"
    PLANNING_DECISION = "PLANNING_DECISION"
    GENERAL = "GENERAL"

class RuleRouter:
    _config: Dict[str, Any] = {}

    @classmethod
    def load_config(cls):
        if not cls._config:
            config_path = Path(__file__).parent.parent.parent / "router_config.yaml"
            with open(config_path, "r") as f:
                cls._config = yaml.safe_load(f)

    @classmethod
    def route(cls, category: TaskCategory, provider_availability: Dict[str, bool]) -> Tuple[str, str]:
        cls.load_config()
        route_info = cls._config["routes"].get(category.value)
        if not route_info:
            return "groq", "llama3-8b-8192"

        primary = route_info["primary"]
        if provider_availability.get(primary["provider"], False):
            return primary["provider"], primary["model"]
            
        fallback = route_info["fallback"]
        return fallback["provider"], fallback["model"]
