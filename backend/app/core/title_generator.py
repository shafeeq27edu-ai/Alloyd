import logging
from sqlalchemy.future import select
from app.db.database import AsyncSessionLocal
from app.db.models import Conversation, ProviderKey
from app.core.encryption import decrypt_key
from app.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

async def generate_and_update_title(conversation_id: str, prompt: str, user_id: str):
    try:
        async with AsyncSessionLocal() as session:
            keys_result = await session.execute(
                select(ProviderKey).where(ProviderKey.user_id == user_id)
            )
            keys = {pk.provider_name: pk.encrypted_key for pk in keys_result.scalars().all()}

            target_provider = next(
                (name for name in ("groq", "gemini", "anthropic") if name in keys),
                None,
            )
            if not target_provider:
                return

            target_model = ProviderRegistry.fast_model(target_provider)

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
    except Exception:
        logger.warning("Title generation failed for conversation %s", conversation_id)
