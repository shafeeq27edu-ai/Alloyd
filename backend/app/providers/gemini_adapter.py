import google.generativeai as genai
from typing import AsyncGenerator, List, Dict, Tuple
from app.providers.base import BaseProviderAdapter

class GeminiAdapter(BaseProviderAdapter):
    async def stream_chat(self, api_key: str, messages: List[Dict[str, str]]) -> AsyncGenerator[Tuple[str, str], None]:
        genai.configure(api_key=api_key)
        
        # Convert messages to Gemini format
        # Gemini uses 'user' and 'model'
        gemini_messages = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [m["content"]]})
            
        try:
            model = genai.GenerativeModel("gemini-1.5-pro")
            
            # Use generate_content_async for async streaming
            response = await model.generate_content_async(
                contents=gemini_messages,
                stream=True
            )
            
            async for chunk in response:
                if chunk.text:
                    yield ("message", chunk.text)
                    
            yield ("done", "")
            
        except Exception as e:
            err_msg = str(e)
            if "API_KEY_INVALID" in err_msg or "invalid API key" in err_msg.lower():
                yield ("error", "Invalid API Key")
            else:
                yield ("error", "Provider error occurred")
