import json
from google import genai
from google.genai.errors import APIError
from typing import AsyncGenerator, List, Dict, Tuple
from app.providers.base import BaseProviderAdapter, ModelDefinition
from app.core.errors import ProviderError, ErrorCode

class GeminiAdapter(BaseProviderAdapter):
    @property
    def provider_name(self) -> str:
        return "gemini"

    def get_models(self) -> List[ModelDefinition]:
        return [
            ModelDefinition(id="gemini-1.5-pro", name="Gemini 1.5 Pro", capabilities=["chat", "multimodal", "long_context"]),
            ModelDefinition(id="gemini-1.5-flash", name="Gemini 1.5 Flash", capabilities=["chat", "fast", "multimodal"])
        ]

    def _map_error(self, e: Exception) -> ProviderError:
        err_msg = str(e)
        if isinstance(e, APIError):
            if e.code == 403 or "API_KEY_INVALID" in err_msg or "invalid API key" in err_msg.lower():
                return ProviderError(ErrorCode.INVALID_API_KEY, self.provider_name, "Invalid Gemini API key.", False)
            elif e.code == 429:
                return ProviderError(ErrorCode.RATE_LIMIT, self.provider_name, "Gemini rate limit exceeded.", True)
            elif e.code == 503:
                return ProviderError(ErrorCode.PROVIDER_UNAVAILABLE, self.provider_name, "Gemini service unavailable.", True)
            elif e.code == 400:
                return ProviderError(ErrorCode.BAD_REQUEST, self.provider_name, f"Gemini API Error: {err_msg}", False)
        elif "API_KEY_INVALID" in err_msg or "invalid API key" in err_msg.lower():
            return ProviderError(ErrorCode.INVALID_API_KEY, self.provider_name, "Invalid Gemini API key.", False)
        return ProviderError(ErrorCode.UNKNOWN, self.provider_name, err_msg, False)

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict]:
        gemini_messages = []
        for m in messages:
            if m["role"] == "system":
                continue 
            role = "user" if m["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [{"text": m["content"]}]})
        return gemini_messages

    async def send_message(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> str:
        client = genai.Client(api_key=api_key)
        try:
            gemini_messages = self._convert_messages(messages)
            response = await client.aio.models.generate_content(model=model_id, contents=gemini_messages)
            return response.text
        except Exception as e:
            raise self._map_error(e)

    async def stream_chat(self, api_key: str, model_id: str, messages: List[Dict[str, str]]) -> AsyncGenerator[Tuple[str, str], None]:
        client = genai.Client(api_key=api_key)
        try:
            gemini_messages = self._convert_messages(messages)
            
            response = await client.aio.models.generate_content_stream(
                model=model_id,
                contents=gemini_messages
            )
            
            async for chunk in response:
                if chunk.text:
                    yield ("message", chunk.text)
            yield ("done", "")
        except Exception as e:
            err = self._map_error(e)
            yield ("error", json.dumps(err.to_dict()))
