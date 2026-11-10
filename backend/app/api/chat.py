import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, Field, model_validator
from typing import Optional
from app.db.database import get_db
from app.db.models import ProviderKey, User, Conversation, Message
from app.core.encryption import decrypt_key
from app.api.deps import get_current_user, verify_csrf
from app.providers.registry import ProviderRegistry
from app.core.router import RuleRouter
from app.core.classifier import TaskClassifier
from app.core.title_generator import generate_and_update_title
from app.core.rate_limit import check_rate_limit
from app.core.errors import ProviderError, ErrorCode
from app.core.history import trim_history
from app.config import settings
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)


def _should_fallback(err: dict) -> bool:
    return bool(err.get("retryable")) or err.get("code") == ErrorCode.MODEL_UNAVAILABLE.value


def _resolve_legacy_route(mode: str | None, provider: str | None, model: str | None):
    """Treat pre-catalog conversations as Auto instead of failing, with a notice."""
    if mode not in ("auto", "manual"):
        return "auto", "This conversation predates routing modes. Using Auto."
    if mode == "manual" and (
        not provider or not model or not ProviderRegistry.has_model(provider, model)
    ):
        return "auto", "This conversation used a model that is no longer available. Using Auto."
    return mode, None


def decrypt_key_safely(cipher_text: str, provider: str) -> str:
    try:
        return decrypt_key(cipher_text)
    except Exception:
        logger.warning(
            "Stored key for provider %s could not be decrypted; asking the user to re-save it.",
            provider,
        )
        raise HTTPException(
            status_code=400,
            detail="Your saved key can no longer be read. Re-save it in Settings.",
        )


async def _stream_with_first_chunk_timeout(adapter, api_key: str, model_id: str, messages, provider: str):
    stream = adapter.stream_chat(api_key=api_key, model_id=model_id, messages=messages)
    try:
        try:
            first = await asyncio.wait_for(
                stream.__anext__(),
                timeout=settings.PROVIDER_FIRST_CHUNK_TIMEOUT_SECONDS,
            )
        except StopAsyncIteration:
            return
        except asyncio.TimeoutError:
            yield ("error", json.dumps(ProviderError(
                ErrorCode.TIMEOUT, provider,
                f"{provider} took too long to start responding.", True
            ).to_dict()))
            return
        yield first
        async for event in stream:
            yield event
    finally:
        await stream.aclose()

class ChatRequest(BaseModel):
    mode: str = Field(default="auto", max_length=16) # "auto" or "manual"
    provider: Optional[str] = Field(default=None, max_length=32)
    model: Optional[str] = Field(default=None, max_length=64)
    message: str = Field(default="", max_length=20000)
    conversation_id: Optional[str] = Field(default=None, max_length=64)
    regenerate: bool = False

    @model_validator(mode="after")
    def require_message_unless_regenerating(self):
        if not self.regenerate and not self.message.strip():
            raise ValueError("Message cannot be empty.")
        return self

@router.post("/", dependencies=[Depends(verify_csrf)])
async def stream_chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Enforce Rate Limiting
    await check_rate_limit(
        f"chat:{current_user.id}",
        settings.CHAT_RATE_LIMIT,
        settings.CHAT_RATE_WINDOW
    )

    # Resolve the conversation and routing mode without writing anything yet.
    legacy_notice = None
    conversation: Conversation | None = None
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
        _, legacy_notice = _resolve_legacy_route(
            conversation.mode, conversation.provider, conversation.model
        )
        if req.mode == "manual":
            req_mode = "manual"
            req_provider = req.provider or conversation.provider
            req_model = req.model or conversation.model
            unchanged_legacy_route = legacy_notice and (
                req_provider == conversation.provider and req_model == conversation.model
            )
            if unchanged_legacy_route:
                req_mode, req_provider, req_model = "auto", None, None
        else:
            req_mode, req_provider, req_model = "auto", None, None
    else:
        if req.regenerate:
            raise HTTPException(status_code=400, detail="Regenerate requires an existing conversation.")
        req_mode, req_provider, req_model = req.mode, req.provider, req.model

    # Regenerate reuses the last stored user message and replaces the answers
    # that followed it, so no duplicate user message is written.
    replacement_ids: list[str] = []
    history_snapshot: list[dict] | None = None
    if req.regenerate:
        history_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
        )
        stored_messages = history_result.scalars().all()
        last_user_index = next(
            (i for i in range(len(stored_messages) - 1, -1, -1) if stored_messages[i].role == "user"),
            None,
        )
        if last_user_index is None:
            raise HTTPException(status_code=400, detail="There is no user message to regenerate.")
        message_text = stored_messages[last_user_index].content
        history_snapshot = [
            {"role": m.role, "content": m.content} for m in stored_messages[:last_user_index + 1]
        ]
        replacement_ids = [m.id for m in stored_messages[last_user_index + 1:]]
    else:
        message_text = req.message

    # Routing and key access must succeed before the conversation is touched.
    category = None
    provider_availability = {}
    if req_mode == "auto":
        keys_result = await db.execute(select(ProviderKey).where(ProviderKey.user_id == current_user.id))
        available_keys = {pk.provider_name: pk.encrypted_key for pk in keys_result.scalars().all()}

        category = TaskClassifier.classify(message_text)

        provider_availability = {name: True for name in available_keys.keys()}
        target_provider, target_model = RuleRouter.route(category, provider_availability)
    else:
        if not req_provider or not req_model:
            raise HTTPException(status_code=400, detail="Manual mode requires provider and model.")
        if not ProviderRegistry.has_model(req_provider, req_model):
            raise HTTPException(status_code=400, detail="Selected model is not available.")
        target_provider = req_provider
        target_model = req_model

    result = await db.execute(
        select(ProviderKey).where(
            ProviderKey.user_id == current_user.id,
            ProviderKey.provider_name == target_provider
        )
    )
    provider_key_record = result.scalars().first()
    if not provider_key_record:
        raise HTTPException(status_code=400, detail=f"No API key configured for provider {target_provider}")

    plain_key = decrypt_key_safely(provider_key_record.encrypted_key, target_provider)

    try:
        adapter = ProviderRegistry.get_adapter(target_provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Provider {target_provider} is not supported.")

    # Persist the conversation (and the new user message) only now.
    is_new_conversation = conversation is None
    if is_new_conversation:
        conversation = Conversation(
            user_id=current_user.id,
            title=message_text[:50],
            mode=req_mode,
            provider=req_provider if req_mode == "manual" else None,
            model=req_model if req_mode == "manual" else None
        )
        db.add(conversation)
        await db.flush()
    elif (conversation.mode, conversation.provider, conversation.model) != (
        req_mode, req_provider, req_model
    ):
        conversation.mode = req_mode
        conversation.provider = req_provider
        conversation.model = req_model

    if not req.regenerate:
        db.add(Message(conversation_id=conversation.id, role="user", content=message_text))
    await db.commit()

    if is_new_conversation:
        asyncio.create_task(generate_and_update_title(conversation.id, message_text, current_user.id))

    from app.core.skills import SKILLS
    if history_snapshot is None:
        msg_result = await db.execute(
            select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
        )
        history_snapshot = [{"role": m.role, "content": m.content} for m in msg_result.scalars().all()]
    api_messages = history_snapshot

    for skill_name, skill in SKILLS.items():
        if f"@{skill_name}" in message_text:
            api_messages.insert(0, {"role": "system", "content": skill.system_prompt})
            break

    api_messages, dropped_messages = trim_history(api_messages, settings.HISTORY_MAX_CHARS)
    notices = []
    if legacy_notice:
        notices.append(legacy_notice)
    if dropped_messages:
        noun = "message" if dropped_messages == 1 else "messages"
        notices.append(f"{dropped_messages} older {noun} omitted to fit the model's context window.")
    notice_text = " ".join(notices) if notices else None

    async def generate():
        nonlocal target_provider, target_model, adapter, plain_key
        fallback_attempted = False

        while True:
            routing_meta = {
                "provider": target_provider,
                "model": target_model,
                "mode": req_mode,
                "conversation_id": conversation.id,
                "category": getattr(category, "value", str(category)) if req_mode == "auto" else "MANUAL"
            }
            if notice_text:
                routing_meta["notice"] = notice_text
            yield f"event: routing\ndata: {json.dumps(routing_meta)}\n\n"

            full_response = ""
            first_chunk_received = False
            error_event_data = None

            try:
                async for event, data in _stream_with_first_chunk_timeout(
                    adapter, plain_key, target_model, api_messages, target_provider
                ):
                    if event == "message":
                        first_chunk_received = True
                        full_response += data
                        yield f"event: message\ndata: {json.dumps({'content': data})}\n\n"
                    elif event == "done":
                        if replacement_ids:
                            await db.execute(delete(Message).where(Message.id.in_(replacement_ids)))
                        assistant_msg = Message(conversation_id=conversation.id, role="assistant", content=full_response)
                        db.add(assistant_msg)
                        await db.commit()
                        yield "event: done\ndata: {}\n\n"
                    elif event == "error":
                        if not first_chunk_received and not fallback_attempted and req_mode == "auto":
                            try:
                                err_dict = json.loads(data)
                                if _should_fallback(err_dict):
                                    if err_dict.get("code") == ErrorCode.MODEL_UNAVAILABLE.value:
                                        logger.warning(
                                            "Model unavailable for %s/%s; falling back (auto mode).",
                                            target_provider, target_model,
                                        )
                                    error_event_data = data
                                    break
                            except json.JSONDecodeError:
                                pass
                        yield f"event: error\ndata: {data}\n\n"
            except Exception as e:
                err_dict = e.to_dict() if hasattr(e, "to_dict") else {"detail": "Provider request failed."}
                if not first_chunk_received and not fallback_attempted and req_mode == "auto" and _should_fallback(err_dict):
                    if err_dict.get("code") == ErrorCode.MODEL_UNAVAILABLE.value:
                        logger.warning(
                            "Model unavailable for %s/%s; falling back (auto mode).",
                            target_provider, target_model,
                        )
                    error_event_data = json.dumps(err_dict)
                else:
                    yield f"event: error\ndata: {json.dumps(err_dict)}\n\n"
                    break

            if error_event_data and not fallback_attempted:
                fallback_attempted = True
                # Try fallback provider
                provider_availability[target_provider] = False
                fallback_provider, fallback_model = RuleRouter.route(category, provider_availability)

                if fallback_provider == target_provider:
                    # No fallback available
                    yield f"event: error\ndata: {error_event_data}\n\n"
                    break

                logger.warning(
                    "Auto fallback: %s/%s -> %s/%s",
                    target_provider, target_model, fallback_provider, fallback_model,
                )

                # Fetch fallback provider key
                result = await db.execute(
                    select(ProviderKey).where(
                        ProviderKey.user_id == current_user.id,
                        ProviderKey.provider_name == fallback_provider
                    )
                )
                fallback_key_record = result.scalars().first()
                if not fallback_key_record:
                    yield f"event: error\ndata: {error_event_data}\n\n"
                    break

                target_provider = fallback_provider
                target_model = fallback_model
                try:
                    plain_key = decrypt_key(fallback_key_record.encrypted_key)
                except Exception:
                    logger.warning(
                        "Stored key for provider %s could not be decrypted; asking the user to re-save it.",
                        fallback_provider,
                    )
                    yield (
                        "event: error\ndata: "
                        + json.dumps({"detail": "Your saved key can no longer be read. Re-save it in Settings."})
                        + "\n\n"
                    )
                    break
                try:
                    adapter = ProviderRegistry.get_adapter(target_provider)
                except ValueError:
                    yield f"event: error\ndata: {error_event_data}\n\n"
                    break
                continue

            break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
