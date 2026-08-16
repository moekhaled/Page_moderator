from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models import AuthorType, Conversation, JobStatus, LlmJob, Message, MessageDirection, MessageSource, SendStatus, WebhookEvent
from app.services.instagram import normalize_messages, payload_hash, verify_meta_signature

router = APIRouter(prefix="/webhook/meta", tags=["meta-webhook"])


@router.get("")
async def verify_webhook(
    mode: str = Query(alias="hub.mode"),
    challenge: str = Query(alias="hub.challenge"),
    verify_token: str = Query(alias="hub.verify_token"),
):
    if mode == "subscribe" and verify_token == settings.meta_verify_token:
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("")
async def ingest_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_meta_signature(signature, raw_body):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    if payload.get("object") != "instagram":
        return {"status": "ignored"}

    normalized_messages = normalize_messages(payload)
    payload_digest = payload_hash(payload)

    for item in normalized_messages:
        existing = await db.execute(select(WebhookEvent).where(WebhookEvent.event_key == item.event_key))
        if existing.scalar_one_or_none():
            continue

        db.add(
            WebhookEvent(
                event_key=item.event_key,
                object_type="instagram",
                payload_json=payload,
                payload_hash=payload_digest,
                processed_at=datetime.utcnow(),
            )
        )

        page_id = settings.instagram_business_account_id
        customer_id = item.sender_id if item.sender_id != page_id else item.recipient_id
        page_party_id = item.recipient_id if item.sender_id != page_id else item.sender_id

        conversation_result = await db.execute(
            select(Conversation).where(
                Conversation.channel == "instagram",
                Conversation.customer_platform_id == customer_id,
                Conversation.page_platform_id == page_party_id,
            )
        )
        conversation = conversation_result.scalar_one_or_none()
        if not conversation:
            conversation = Conversation(
                channel="instagram",
                customer_platform_id=customer_id,
                page_platform_id=page_party_id,
                last_message_at=item.event_timestamp,
            )
            db.add(conversation)
            await db.flush()

        is_outbound = item.sender_id == page_id
        message = Message(
            conversation_id=conversation.id,
            platform_message_id=item.platform_message_id,
            direction=MessageDirection.outbound if is_outbound else MessageDirection.inbound,
            author_type=AuthorType.human_moderator if is_outbound else AuthorType.customer,
            author_id=item.sender_id,
            text=item.text,
            attachments_json=item.attachments,
            source=MessageSource.meta_webhook,
            send_status=SendStatus.received,
            created_at=item.event_timestamp,
            updated_at=item.event_timestamp,
        )
        db.add(message)
        conversation.last_message_at = item.event_timestamp
        conversation.updated_at = datetime.utcnow()
        await db.flush()

        if not is_outbound:
            db.add(
                LlmJob(
                    conversation_id=conversation.id,
                    inbound_message_id=message.id,
                    status=JobStatus.pending,
                )
            )

        try:
            await db.commit()
        except Exception:
            await db.rollback()

    return {"status": "ok", "processed": len(normalized_messages)}
