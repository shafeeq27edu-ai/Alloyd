import groq
from typing import AsyncGenerator, List, Dict, Tuple
from app.providers.base import BaseProviderAdapter

class GroqAdapter(BaseProviderAdapter):
    async def stream_chat(self, api_key: str, messages: List[Dict[str, str]]) -> AsyncGenerator[Tuple[str, str], None]:
        client = groq.AsyncGroq(api_key=api_key)
        try:
            stream = await client.chat.completions.create(
                messages=messages,
                model="llama3-8b-8192",
                stream=True
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield ("message", content)
                    
            yield ("done", "")
            
        except groq.AuthenticationError:
            yield ("error", "Invalid API Key")
        except groq.RateLimitError:
            yield ("error", "Rate limit exceeded")
        except Exception as e:
            yield ("error", "Provider error occurred")
