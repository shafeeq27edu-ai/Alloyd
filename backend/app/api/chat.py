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
    mode: str = "auto" # "auto" or "manual"
    provider: Optional[str] = None
    model: Optional[str] = None
    message: str
    conversation_id: Optional[str] = None

@router.post("/")
async def stream_chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.providers.router import RuleRouter
    
    # 1. Routing Logic
    if req.mode == "auto":
        target_provider, target_model = RuleRouter.route(req.message)
    else:
        if not req.provider or not req.model:
            raise HTTPException(status_code=400, detail="Manual mode requires provider and model.")
        target_provider = req.provider
        target_model = req.model

    # 2. Fetch provider key
    result = await db.execute(
        select(ProviderKey).where(
            ProviderKey.user_id == current_user.id,
            ProviderKey.provider_name == target_provider
        )
    )
    provider_key_record = result.scalars().first()
    if not provider_key_record:
        raise HTTPException(status_code=400, detail=f"No API key configured for provider {target_provider}")
    
    plain_key = decrypt_key(provider_key_record.encrypted_key)
    
    # 3. Setup conversation
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

    # 4. Save user message
    user_msg = Message(conversation_id=conversation.id, role="user", content=req.message)
    db.add(user_msg)
    await db.commit()

    # 5. Fetch history for context
    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    messages_history = msg_result.scalars().all()
    
    api_messages = [{"role": m.role, "content": m.content} for m in messages_history]

    # 6. Provider abstraction
    from app.providers.registry import ProviderRegistry
    
    try:
        adapter = ProviderRegistry.get_adapter(target_provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Provider {target_provider} is not supported.")
        
    async def generate():
        # Emit routing metadata first so frontend knows who is answering
        routing_meta = {
            "provider": target_provider,
            "model": target_model,
            "mode": req.mode
        }
        yield f"event: routing\ndata: {json.dumps(routing_meta)}\n\n"

        full_response = ""
        
        # Note: We pass model to the adapter, though currently groq_adapter hardcodes it.
        # We will update adapters to accept model in Phase 2.2
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
