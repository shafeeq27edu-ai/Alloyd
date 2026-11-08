import json
import groq
from typing import AsyncGenerator, List, Dict, Tuple
from app.providers.base import BaseProviderAdapter, ModelDefinition
from app.core.errors import ProviderError, ErrorCode, provider_error_from_status, timeout_error
from app.config import settings

class GroqAdapter(BaseProviderAdapter):
    @property
    def provider_name(self) -> str:
        return "groq"

    def get_models(self) -> List[ModelDefinition]:
        return [
            ModelDefinition(id="llama-3.3-70b-versatile", name="Llama 3.3 70B Versatile", capabilities=["chat", "reasoning"]),
            ModelDefinition(id="llama-3.1-8b-instant", name="Llama 3.1 8B Instant", capabilities=["chat", "fast"])
        ]

    def _map_error(self, e: Exception) -> ProviderError:
        if isinstance(e, groq.APITimeoutError):
            return timeout_error(self.provider_name)
        if isinstance(e, groq.APIConnectionError):
            return ProviderError(ErrorCode.PROVIDER_UNAVAILABLE, self.provider_name, "Failed to connect to Groq.", True)
        if isinstance(e, groq.APIStatusError):
            return provider_error_from_status(self.provider_name, e.status_code)
        return ProviderError(ErrorCode.UNKNOWN, self.provider_name, "Groq request failed.", False)

    async def validate_key(self, api_key: str) -> None:
        client = groq.AsyncGroq(api_key=api_key, timeout=settings.PROVIDER_TIMEOUT_SECONDS)
        try:
            await client.models.list()
        except Exception as e:
            raise self._map_error(e)

    async def send_message(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> str:
        client = groq.AsyncGroq(api_key=api_key, timeout=settings.PROVIDER_TIMEOUT_SECONDS)
        try:
            response = await client.chat.completions.create(
                messages=messages,
                model=model_id,
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            raise self._map_error(e)

    async def stream_chat(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> AsyncGenerator[Tuple[str, str], None]:
        client = groq.AsyncGroq(api_key=api_key, timeout=settings.PROVIDER_TIMEOUT_SECONDS)
        try:
            stream = await client.chat.completions.create(
                messages=messages,
                model=model_id,
                stream=True
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield ("message", content)
            yield ("done", "")
        except Exception as e:
            err = self._map_error(e)
            yield ("error", json.dumps(err.to_dict()))
