from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Tuple

class BaseProviderAdapter(ABC):
    @abstractmethod
    async def stream_chat(self, api_key: str, messages: List[Dict[str, str]]) -> AsyncGenerator[Tuple[str, str], None]:
        """
        Streams chat responses using the provider SDK.
        Yields tuples of (event_type, data).
        event_type can be 'message', 'error', or 'done'.
        """
        pass
