import json
import httpx
from google import genai
from google.genai import types
from google.genai.errors import APIError
from typing import AsyncGenerator, List, Dict, Tuple
from app.providers.base import BaseProviderAdapter, ModelDefinition
from app.core.errors import ProviderError, ErrorCode, provider_error_from_status, timeout_error
from app.config import settings

class GeminiAdapter(BaseProviderAdapter):
    @property
    def provider_name(self) -> str:
        return "gemini"

    def get_models(self) -> List[ModelDefinition]:
        return [
            ModelDefinition(id="gemini-4-argon", name="Gemini 4 Argon", capabilities=["chat", "reasoning", "multimodal", "long_context"]),
            ModelDefinition(id="gemini-3.8-flash", name="Gemini 3.8 Flash", capabilities=["chat", "fast", "multimodal"])
        ]

    def _map_error(self, e: Exception) -> ProviderError:
        if isinstance(e, (TimeoutError, httpx.TimeoutException)):
            return timeout_error(self.provider_name)
        if isinstance(e, httpx.RequestError):
            return ProviderError(
                ErrorCode.PROVIDER_UNAVAILABLE, self.provider_name,
                "Failed to connect to Gemini.", True
            )
        if isinstance(e, APIError):
            # Google returns 400 with API_KEY_INVALID for bad keys, not 401.
            message = str(e).lower()
            if "api_key_invalid" in message or "invalid api key" in message:
                return ProviderError(
                    ErrorCode.INVALID_API_KEY, self.provider_name,
                    "The Gemini API key appears to be invalid.", False
                )
            if isinstance(getattr(e, "code", None), int):
                return provider_error_from_status(self.provider_name, e.code)
        return ProviderError(ErrorCode.UNKNOWN, self.provider_name, "Gemini request failed.", False)

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict]:
        gemini_messages = []
        for m in messages:
            if m["role"] == "system":
                continue
            role = "user" if m["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [{"text": m["content"]}]})
        return gemini_messages

    def _system_instruction(self, messages: List[Dict[str, str]]) -> str | None:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        return "\n\n".join(system_parts) if system_parts else None

    def _client(self, api_key: str) -> genai.Client:
        timeout_ms = int(settings.PROVIDER_TIMEOUT_SECONDS * 1000)
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_ms)
        )

    async def validate_key(self, api_key: str) -> None:
        client = self._client(api_key)
        try:
            # List models so key validation does not depend on one model's availability.
            await client.aio.models.list()
        except Exception as e:
            raise self._map_error(e)

    async def send_message(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> str:
        client = self._client(api_key)
        try:
            gemini_messages = self._convert_messages(messages)
            system = self._system_instruction(messages)
            config = types.GenerateContentConfig(system_instruction=system) if system else None
            response = await client.aio.models.generate_content(
                model=model_id, contents=gemini_messages, config=config
            )
            return response.text
        except Exception as e:
            raise self._map_error(e)

    async def stream_chat(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> AsyncGenerator[Tuple[str, str], None]:
        client = self._client(api_key)
        try:
            gemini_messages = self._convert_messages(messages)
            system = self._system_instruction(messages)
            config = types.GenerateContentConfig(system_instruction=system) if system else None

            response = await client.aio.models.generate_content_stream(
                model=model_id,
                contents=gemini_messages,
                config=config
            )

            async for chunk in response:
                if chunk.text:
                    yield ("message", chunk.text)
            yield ("done", "")
        except Exception as e:
            err = self._map_error(e)
            yield ("error", json.dumps(err.to_dict()))
