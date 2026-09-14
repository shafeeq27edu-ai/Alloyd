import asyncio
from sqlalchemy.future import select
from app.db.database import AsyncSessionLocal
from app.db.models import Conversation, ProviderKey
from app.core.encryption import decrypt_key
from app.providers.registry import ProviderRegistry

async def generate_and_update_title(conversation_id: str, prompt: str, user_id: str):
    try:
        async with AsyncSessionLocal() as session:
            # Look for a groq key first (fastest), then try others
            keys_result = await session.execute(
                select(ProviderKey).where(ProviderKey.user_id == user_id)
            )
            keys = {pk.provider_name: pk.encrypted_key for pk in keys_result.scalars().all()}
            
            target_provider = None
            target_model = None
            
            if "groq" in keys:
                target_provider = "groq"
                target_model = "llama3-8b-8192"
            elif "gemini" in keys:
                target_provider = "gemini"
                target_model = "gemini-1.5-flash"
            elif "anthropic" in keys:
                target_provider = "anthropic"
                target_model = "claude-3-haiku-20240307"
            
            if not target_provider or not target_model:
                return

            plain_key = decrypt_key(keys[target_provider])
            adapter = ProviderRegistry.get_adapter(target_provider)
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a title generator. Generate a very short, concise title (max 4 words) for the following chat prompt. Do not use quotes or punctuation."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            title = await adapter.send_message(api_key=plain_key, model_id=target_model, messages=messages)
            clean_title = title.strip().replace('"', '').replace('.', '')
            if len(clean_title) > 50:
                clean_title = clean_title[:47] + "..."
                
            conv_result = await session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = conv_result.scalars().first()
            if conversation:
                conversation.title = clean_title
                await session.commit()
    except Exception as e:
        print(f"Failed to generate title: {e}")
