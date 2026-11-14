from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List
from app.db.database import get_db
from app.db.models import Conversation, Message, UsageEvent, User
from app.api.deps import get_current_user, verify_csrf

router = APIRouter()


def _usage_payload(event: UsageEvent) -> dict:
    return {
        "input_tokens": event.input_tokens,
        "output_tokens": event.output_tokens,
        "token_source": event.token_source,
        "estimated_cost_usd": event.estimated_cost_usd,
    }

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

    usage_result = await db.execute(
        select(UsageEvent)
        .where(
            UsageEvent.conversation_id == conversation_id,
            UsageEvent.message_id.is_not(None),
        )
        .order_by(UsageEvent.created_at)
    )
    usage_by_message = {event.message_id: event for event in usage_result.scalars().all()}
    return {
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
                "usage": _usage_payload(usage_by_message[m.id]) if m.id in usage_by_message else None,
            }
            for m in messages
        ]
    }

@router.delete("/{conversation_id}", dependencies=[Depends(verify_csrf)])
async def delete_conversation(
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

    await db.delete(conversation)
    await db.commit()
    return {"status": "success"}
