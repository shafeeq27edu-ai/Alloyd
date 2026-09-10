from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List
from app.db.database import get_db
from app.db.models import Conversation, Message, User
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/")
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(desc(Conversation.created_at))
    )
    conversations = result.scalars().all()
    return {
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "mode": c.mode,
                "provider": c.provider,
                "model": c.model,
                "created_at": c.created_at
            }
            for c in conversations
        ]
    }

@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify ownership
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = conv_result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()
    return {
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at
            }
            for m in messages
        ]
    }
