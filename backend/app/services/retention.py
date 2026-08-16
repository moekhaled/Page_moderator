from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Message, MessageSummary, WebhookEvent


async def summarize_messages_older_than_retention(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.retention_days)
    conv_rows = await db.execute(select(Message.conversation_id).where(Message.created_at < cutoff).distinct())
    conv_ids = [row[0] for row in conv_rows.all()]
    summaries_created = 0

    for conversation_id in conv_ids:
        msg_rows = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.created_at < cutoff)
            .order_by(Message.created_at.asc())
        )
        rows = msg_rows.scalars().all()
        if not rows:
            continue

        inbound_count = sum(1 for m in rows if m.direction.value == "inbound")
        outbound_count = sum(1 for m in rows if m.direction.value == "outbound")
        first_ts = rows[0].created_at
        last_ts = rows[-1].created_at
        summary_text = (
            f"Summary window {first_ts} to {last_ts}. "
            f"Inbound messages: {inbound_count}. Outbound messages: {outbound_count}."
        )
        db.add(
            MessageSummary(
                conversation_id=conversation_id,
                covered_until_message_id=rows[-1].id,
                summary_text=summary_text,
            )
        )
        summaries_created += 1

    await db.commit()
    return summaries_created


async def prune_old_data(db: AsyncSession) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    message_cutoff = now - timedelta(days=settings.retention_days)
    raw_cutoff = now - timedelta(days=settings.raw_event_retention_days)

    result1 = await db.execute(delete(Message).where(Message.created_at < message_cutoff))
    result2 = await db.execute(delete(WebhookEvent).where(WebhookEvent.processed_at < raw_cutoff))
    await db.commit()

    return {
        "pruned_messages": int(result1.rowcount or 0),
        "pruned_webhook_events": int(result2.rowcount or 0),
    }
