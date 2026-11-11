"""Deterministic provider used only by end-to-end tests.

It is registered only when ``ENABLE_MOCK_PROVIDER`` is set, so it never ships
in a normal deployment. It performs no network calls.
"""
from typing import AsyncGenerator, Dict, List, Tuple

from app.core.errors import ErrorCode, ProviderError
from app.providers.base import BaseProviderAdapter, ModelDefinition


class MockAdapter(BaseProviderAdapter):
    @property
    def provider_name(self) -> str:
        return "mock"

    def get_models(self) -> List[ModelDefinition]:
        return [
            ModelDefinition(id="mock-model", name="Mock Model", capabilities=["chat", "fast"]),
            ModelDefinition(id="mock-model-pro", name="Mock Model Pro", capabilities=["chat"]),
        ]

    async def send_message(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> str:
        return self._reply(messages)

    async def validate_key(self, api_key: str) -> None:
        if not api_key.strip():
            raise ProviderError(
                ErrorCode.INVALID_API_KEY, self.provider_name, "Mock key is empty.", False
            )

    async def stream_chat(
        self, api_key: str, model_id: str, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[Tuple[str, str], None]:
        yield ("message", self._reply(messages))
        yield ("done", "")

    @staticmethod
    def _reply(messages: List[Dict[str, str]]) -> str:
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
        )
        return f"Mock reply from {last_user[:80]}"
