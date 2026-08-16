import asyncio
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import AsyncSessionLocal
from app.models import AppSetting, Conversation, JobStatus, LlmJob, LlmTurn, Message, MessageDirection, OutboundJob
from app.services.reservation_agent import ReservationAgentRuntime

runtime = ReservationAgentRuntime()


async def _is_global_llm_paused(db: AsyncSession) -> bool:
    row = await db.get(AppSetting, "global_llm_paused")
    if not row:
        return settings.global_llm_paused
    return row.value.lower() == "true"


async def _claim_jobs(db: AsyncSession) -> list[LlmJob]:
    stmt = (
        select(LlmJob)
        .where(LlmJob.status == JobStatus.pending)
        .order_by(LlmJob.created_at.asc())
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


async def _build_history(db: AsyncSession, conversation_id: int) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(settings.llm_history_limit)
    )
    rows = list(result.scalars().all())
    rows.reverse()
    return [
        {
            "role": "assistant" if row.direction == MessageDirection.outbound else "user",
            "content": row.text or "[non-text message]",
        }
        for row in rows
    ]


async def _process_job(db: AsyncSession, job: LlmJob) -> None:
    conversation = await db.get(Conversation, job.conversation_id)
    if not conversation:
        job.status = JobStatus.failed
        job.error_message = "conversation_not_found"
        job.updated_at = datetime.utcnow()
        await db.commit()
        return

    if conversation.llm_paused or await _is_global_llm_paused(db) or not settings.llm_enabled:
        job.status = JobStatus.done
        job.updated_at = datetime.utcnow()
        await db.commit()
        return

    history = await _build_history(db, conversation.id)
    run_mode = "shadow" if settings.llm_shadow_mode else "active"

    try:
        result = await runtime.run(history)
        reply_text = "\n".join(result.decision.messages)
        llm_turn = LlmTurn(
            conversation_id=conversation.id,
            inbound_message_id=job.inbound_message_id,
            model_name=result.model_name,
            intent=result.decision.intent.value,
            confidence=result.decision.confidence,
            requires_human=result.decision.requires_human,
            reply_text=reply_text,
            required_capabilities_json=[c.value for c in result.decision.required_capabilities],
            next_actions_json=result.decision.next_actions,
            safety_flags_json=result.decision.safety_flags,
            input_messages_count=result.input_messages_count,
            latency_ms=result.latency_ms,
            run_mode=run_mode,
            policy_action=result.policy_action.value,
            auto_reply_eligible=result.auto_reply_eligible,
        )
        db.add(llm_turn)
        await db.flush()

        if run_mode == "active" and result.auto_reply_eligible and result.decision.messages:
            for idx, msg in enumerate(result.decision.messages):
                outbound_job = OutboundJob(
                    conversation_id=conversation.id,
                    llm_turn_id=llm_turn.id,
                    recipient_platform_id=conversation.customer_platform_id,
                    reply_text=msg,
                    idempotency_key=f"{conversation.id}:{job.inbound_message_id}:{llm_turn.id}:{idx}",
                    status=JobStatus.pending,
                )
                db.add(outbound_job)

        job.status = JobStatus.done
        job.updated_at = datetime.utcnow()
        await db.commit()
    except Exception as exc:
        job.status = JobStatus.failed
        job.error_message = str(exc)
        job.updated_at = datetime.utcnow()
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
