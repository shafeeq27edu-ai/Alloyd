import json
from typing import AsyncGenerator, List, Dict, Tuple
from anthropic import AsyncAnthropic, APIError, APIConnectionError, RateLimitError, AuthenticationError
from app.providers.base import BaseProviderAdapter, ModelDefinition
from app.core.errors import ProviderError, ErrorCode

class AnthropicAdapter(BaseProviderAdapter):
    @property
    def provider_name(self) -> str:
        return "anthropic"

    def get_models(self) -> List[ModelDefinition]:
        return [
            ModelDefinition(id="claude-3-5-sonnet-20240620", name="Claude 3.5 Sonnet", capabilities=["chat", "reasoning", "multimodal"]),
            ModelDefinition(id="claude-3-haiku-20240307", name="Claude 3 Haiku", capabilities=["chat", "fast"])
        ]

    def _map_error(self, e: Exception) -> ProviderError:
        if isinstance(e, AuthenticationError):
            return ProviderError(ErrorCode.INVALID_API_KEY, self.provider_name, "Invalid Anthropic API key.", False)
        elif isinstance(e, RateLimitError):
            return ProviderError(ErrorCode.RATE_LIMIT, self.provider_name, "Anthropic rate limit exceeded.", True)
        elif isinstance(e, APIConnectionError):
            return ProviderError(ErrorCode.PROVIDER_UNAVAILABLE, self.provider_name, "Failed to connect to Anthropic.", True)
        elif isinstance(e, APIError):
            return ProviderError(ErrorCode.BAD_REQUEST, self.provider_name, f"Anthropic API Error: {str(e)}", False)
        return ProviderError(ErrorCode.UNKNOWN, self.provider_name, str(e), False)

    async def send_message(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> str:
        client = AsyncAnthropic(api_key=api_key)
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
        client = AsyncAnthropic(api_key=api_key)
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
