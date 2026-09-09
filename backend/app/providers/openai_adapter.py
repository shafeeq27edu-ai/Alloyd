import openai
from typing import AsyncGenerator, List, Dict, Tuple
from app.providers.base import BaseProviderAdapter

class OpenAIAdapter(BaseProviderAdapter):
    async def stream_chat(self, api_key: str, messages: List[Dict[str, str]]) -> AsyncGenerator[Tuple[str, str], None]:
        client = openai.AsyncOpenAI(api_key=api_key)
        try:
            # Hardcode gpt-4o for now until model parameter is piped through adapter in Phase 2.3
            stream = await client.chat.completions.create(
                messages=messages,
                model="gpt-4o",
                stream=True
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield ("message", content)
                    
            yield ("done", "")
            
        except openai.AuthenticationError:
            yield ("error", "Invalid API Key")
        except openai.RateLimitError:
            yield ("error", "Rate limit exceeded")
        except Exception as e:
            yield ("error", "Provider error occurred")
