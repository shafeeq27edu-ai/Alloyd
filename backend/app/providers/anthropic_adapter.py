import json
from typing import AsyncGenerator, List, Dict, Tuple
from anthropic import AsyncAnthropic, APIConnectionError, APITimeoutError, APIStatusError
from app.providers.base import BaseProviderAdapter, ModelDefinition
from app.core.errors import ProviderError, ErrorCode, provider_error_from_status, timeout_error
from app.config import settings

class AnthropicAdapter(BaseProviderAdapter):
    @property
    def provider_name(self) -> str:
        return "anthropic"

    def get_models(self) -> List[ModelDefinition]:
        return [
            ModelDefinition(id="claude-sonnet-5-5", name="Claude Sonnet 5.5", capabilities=["chat", "reasoning", "multimodal"]),
            ModelDefinition(id="claude-haiku-5-5", name="Claude Haiku 5.5", capabilities=["chat", "fast"])
        ]

    def _map_error(self, e: Exception) -> ProviderError:
        if isinstance(e, APITimeoutError):
            return timeout_error(self.provider_name)
        if isinstance(e, APIConnectionError):
            return ProviderError(ErrorCode.PROVIDER_UNAVAILABLE, self.provider_name, "Failed to connect to Anthropic.", True)
        if isinstance(e, APIStatusError):
            return provider_error_from_status(self.provider_name, e.status_code)
        return ProviderError(ErrorCode.UNKNOWN, self.provider_name, "Anthropic request failed.", False)

    async def validate_key(self, api_key: str) -> None:
        client = AsyncAnthropic(api_key=api_key, timeout=settings.PROVIDER_TIMEOUT_SECONDS)
        try:
            await client.models.list()
        except Exception as e:
            raise self._map_error(e)

    async def send_message(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> str:
        client = AsyncAnthropic(api_key=api_key, timeout=settings.PROVIDER_TIMEOUT_SECONDS)
        try:
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
            api_messages = [m for m in messages if m["role"] != "system"]
            kwargs = {
                "model": model_id,
                "max_tokens": 4096,
                "messages": api_messages,
            }
            if system_msg:
                kwargs["system"] = system_msg
                
            response = await client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            raise self._map_error(e)

    async def stream_chat(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> AsyncGenerator[Tuple[str, str], None]:
        client = AsyncAnthropic(api_key=api_key, timeout=settings.PROVIDER_TIMEOUT_SECONDS)
        try:
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
            api_messages = [m for m in messages if m["role"] != "system"]
            kwargs = {
                "model": model_id,
                "max_tokens": 4096,
                "messages": api_messages,
            }
            if system_msg:
                kwargs["system"] = system_msg

            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield "message", text
            yield "done", ""
        except Exception as e:
            err = self._map_error(e)
            yield "error", json.dumps(err.to_dict())
