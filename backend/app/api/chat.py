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
from app.providers.registry import ProviderRegistry
from app.core.router import RuleRouter
from app.core.classifier import TaskClassifier

router = APIRouter()

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
    # Setup conversation
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
        req_mode = conversation.mode
        req_provider = conversation.provider
        req_model = conversation.model
    else:
        conversation = Conversation(
            user_id=current_user.id, 
            title=req.message[:50],
            mode=req.mode,
            provider=req.provider if req.mode == "manual" else None,
            model=req.model if req.mode == "manual" else None
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        req_mode = req.mode
        req_provider = req.provider
        req_model = req.model

    # Save user message
    user_msg = Message(conversation_id=conversation.id, role="user", content=req.message)
    db.add(user_msg)
    await db.commit()

    # Routing Logic
    if req_mode == "auto":
        keys_result = await db.execute(select(ProviderKey).where(ProviderKey.user_id == current_user.id))
        available_keys = {pk.provider_name: pk.encrypted_key for pk in keys_result.scalars().all()}
        
        groq_key_encrypted = available_keys.get("groq")
        groq_api_key = decrypt_key(groq_key_encrypted) if groq_key_encrypted else None
        
        category = await TaskClassifier.classify(req.message, groq_api_key)
        
        provider_availability = {name: True for name in available_keys.keys()}
        target_provider, target_model = RuleRouter.route(category, provider_availability)
    else:
        if not req_provider or not req_model:
            raise HTTPException(status_code=400, detail="Manual mode requires provider and model.")
        target_provider = req_provider
        target_model = req_model

    # Fetch provider key
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
    
    # Fetch history for context
    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    messages_history = msg_result.scalars().all()
    api_messages = [{"role": m.role, "content": m.content} for m in messages_history]

    try:
        adapter = ProviderRegistry.get_adapter(target_provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Provider {target_provider} is not supported.")
        
    async def generate():
        routing_meta = {
            "provider": target_provider,
            "model": target_model,
            "mode": req_mode,
            "conversation_id": conversation.id
        }
        yield f"event: routing\ndata: {json.dumps(routing_meta)}\n\n"

        full_response = ""
        try:
            async for event, data in adapter.stream_chat(api_key=plain_key, model_id=target_model, messages=api_messages):
                if event == "message":
                    full_response += data
                    yield f"event: message\ndata: {json.dumps({'content': data})}\n\n"
                elif event == "done":
                    assistant_msg = Message(conversation_id=conversation.id, role="assistant", content=full_response)
                    db.add(assistant_msg)
                    await db.commit()
                    yield "event: done\ndata: {}\n\n"
                elif event == "error":
                    yield f"event: error\ndata: {data}\n\n"
        except Exception as e:
            if hasattr(e, "to_dict"):
                yield f"event: error\ndata: {json.dumps(e.to_dict())}\n\n"
            else:
                yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
            
    return StreamingResponse(generate(), media_type="text/event-stream")
