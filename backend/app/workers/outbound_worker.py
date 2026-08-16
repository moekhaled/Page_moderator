import asyncio
from datetime import datetime

from sqlalchemy import select

from app.config import settings
from app.db import AsyncSessionLocal
from app.models import AuthorType, JobStatus, Message, MessageDirection, MessageSource, OutboundJob, SendStatus
from app.services.meta_send import MetaSendClient

client = MetaSendClient()


async def _claim_jobs(db):
    stmt = (
        select(OutboundJob)
        .where(OutboundJob.status == JobStatus.pending)
        .order_by(OutboundJob.created_at.asc())
        .limit(settings.worker_batch_size)
        .with_for_update(skip_locked=True)
    )
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    for job in jobs:
        job.status = JobStatus.processing
        job.attempts += 1
        job.updated_at = datetime.utcnow()
    await db.commit()
    return jobs


async def _process_job(db, job: OutboundJob):
    try:
        meta_result = await client.send_text(job.recipient_platform_id, job.reply_text)
        job.status = JobStatus.done
        job.meta_response_json = meta_result
        job.updated_at = datetime.utcnow()

        db.add(
            Message(
                conversation_id=job.conversation_id,
                platform_message_id=None,
                direction=MessageDirection.outbound,
                author_type=AuthorType.llm_agent,
                author_id="llm-agent",
                text=job.reply_text,
                attachments_json=[],
                source=MessageSource.llm_worker,
                send_status=SendStatus.sent,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        await db.commit()
    except Exception as exc:
        job.error_message = str(exc)
        job.updated_at = datetime.utcnow()
        job.status = JobStatus.failed if job.attempts >= settings.outbound_max_attempts else JobStatus.pending
        await db.commit()


async def run_loop() -> None:
    while True:
        async with AsyncSessionLocal() as db:
            jobs = await _claim_jobs(db)
            for job in jobs:
                await _process_job(db, job)
        await asyncio.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(run_loop())
