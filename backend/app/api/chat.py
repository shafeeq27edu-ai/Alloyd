import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional
from app.db.database import get_db
from app.db.models import ProviderKey, User, Conversation, Message
from app.core.encryption import decrypt_key
from app.api.deps import get_current_user
import groq

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    provider: str
    message: str
    conversation_id: Optional[str] = None

@router.post("/")
async def stream_chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch provider key
    result = await db.execute(
        select(ProviderKey).where(
            ProviderKey.user_id == current_user.id,
            ProviderKey.provider_name == req.provider
        )
    )
    provider_key_record = result.scalars().first()
    if not provider_key_record:
        raise HTTPException(status_code=400, detail=f"No API key configured for provider {req.provider}")
    
    plain_key = decrypt_key(provider_key_record.encrypted_key)
    
    # 2. Setup conversation
    if req.conversation_id:
        conv_result = await db.execute(
            select(Conversation).where(
                Conversation.id == req.conversation_id,
                Conversation.user_id == current_user.id
            )
        )
        conversation = conv_result.scalars().first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(user_id=current_user.id, title=req.message[:50])
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    # 3. Save user message
    user_msg = Message(conversation_id=conversation.id, role="user", content=req.message)
    db.add(user_msg)
    await db.commit()

    # 4. Fetch history for context
    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    messages_history = msg_result.scalars().all()
    
    api_messages = [{"role": m.role, "content": m.content} for m in messages_history]

    # 5. Provider abstraction
    from app.providers.registry import ProviderRegistry
    
    try:
        adapter = ProviderRegistry.get_adapter(req.provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Provider {req.provider} is not supported.")
        
    async def generate():
        full_response = ""
        
        async for event, data in adapter.stream_chat(api_key=plain_key, messages=api_messages):
            if event == "message":
                full_response += data
                yield f"event: message\ndata: {json.dumps({'content': data})}\n\n"
            elif event == "done":
                # Save assistant message after stream completes
                assistant_msg = Message(conversation_id=conversation.id, role="assistant", content=full_response)
                db.add(assistant_msg)
                await db.commit()
                yield "event: done\ndata: {}\n\n"
            elif event == "error":
                yield f"event: error\ndata: {json.dumps({'detail': data})}\n\n"
            
    return StreamingResponse(generate(), media_type="text/event-stream")
