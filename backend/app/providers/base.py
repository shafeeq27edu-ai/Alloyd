from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Tuple, Any
from pydantic import BaseModel

class ModelDefinition(BaseModel):
    id: str
    name: str
    capabilities: List[str]  # e.g., "chat", "multimodal", "long_context"

class BaseProviderAdapter(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def get_models(self) -> List[ModelDefinition]:
        pass

    @abstractmethod
    async def send_message(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> str:
        """
        Sends a single prompt and waits for the full response string.
        Should raise ProviderError on failure.
        """
        pass

    @abstractmethod
    async def stream_chat(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> AsyncGenerator[Tuple[str, str], None]:
        """
        Streams chat responses using the provider SDK.
        Yields tuples of (event_type, data).
        event_type can be 'message', 'error', or 'done'.
        Should yield ProviderError dict on failure as an 'error' event.
        """
        pass
