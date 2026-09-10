import json
import groq
from typing import AsyncGenerator, List, Dict, Tuple
from app.providers.base import BaseProviderAdapter, ModelDefinition
from app.core.errors import ProviderError, ErrorCode

class GroqAdapter(BaseProviderAdapter):
    @property
    def provider_name(self) -> str:
        return "groq"

    def get_models(self) -> List[ModelDefinition]:
        return [
            ModelDefinition(id="llama3-8b-8192", name="Llama 3 8B", capabilities=["chat", "fast", "reasoning"]),
            ModelDefinition(id="llama3-70b-8192", name="Llama 3 70B", capabilities=["chat", "reasoning"])
        ]

    def _map_error(self, e: Exception) -> ProviderError:
        if isinstance(e, groq.AuthenticationError):
            return ProviderError(ErrorCode.INVALID_API_KEY, self.provider_name, "Invalid Groq API key.", False)
        elif isinstance(e, groq.RateLimitError):
            return ProviderError(ErrorCode.RATE_LIMIT, self.provider_name, "Groq rate limit exceeded.", True)
        elif isinstance(e, groq.APIConnectionError):
            return ProviderError(ErrorCode.PROVIDER_UNAVAILABLE, self.provider_name, "Failed to connect to Groq.", True)
        elif isinstance(e, groq.APIError):
            return ProviderError(ErrorCode.BAD_REQUEST, self.provider_name, f"Groq API Error: {str(e)}", False)
        return ProviderError(ErrorCode.UNKNOWN, self.provider_name, str(e), False)

    async def send_message(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> str:
        client = groq.AsyncGroq(api_key=api_key)
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
        client = groq.AsyncGroq(api_key=api_key)
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
