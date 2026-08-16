import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ConversationStatus(str, enum.Enum):
    open = "open"
    pending = "pending"
    closed = "closed"


class MessageDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"


class AuthorType(str, enum.Enum):
    customer = "customer"
    human_moderator = "human_moderator"
    llm_agent = "llm_agent"
    system = "system"


class MessageSource(str, enum.Enum):
    meta_webhook = "meta_webhook"
    api_send = "api_send"
    llm_worker = "llm_worker"


class SendStatus(str, enum.Enum):
    received = "received"
    queued = "queued"
    sent = "sent"
    failed = "failed"


class JobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(32), default="instagram", nullable=False)
    customer_platform_id: Mapped[str] = mapped_column(String(128), nullable=False)
    page_platform_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[ConversationStatus] = mapped_column(Enum(ConversationStatus), default=ConversationStatus.open, nullable=False)
    llm_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all,delete-orphan")

    __table_args__ = (
        UniqueConstraint("channel", "customer_platform_id", "page_platform_id", name="uq_conversation_party"),
        Index("ix_conversations_last_message_at", "last_message_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    platform_message_id: Mapped[str | None] = mapped_column(String(191), nullable=True)
    direction: Mapped[MessageDirection] = mapped_column(Enum(MessageDirection), nullable=False)
    author_type: Mapped[AuthorType] = mapped_column(Enum(AuthorType), nullable=False)
    author_id: Mapped[str] = mapped_column(String(128), nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachments_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    source: Mapped[MessageSource] = mapped_column(Enum(MessageSource), default=MessageSource.meta_webhook, nullable=False)
    send_status: Mapped[SendStatus] = mapped_column(Enum(SendStatus), default=SendStatus.received, nullable=False)
    reply_to_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    __table_args__ = (
        UniqueConstraint("platform_message_id", name="uq_messages_platform_message_id"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_key: Mapped[str] = mapped_column(String(191), nullable=False, unique=True)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class MessageSummary(Base):
    __tablename__ = "message_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    covered_until_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_message_summaries_conversation", "conversation_id"),)


class LlmTurn(Base):
    __tablename__ = "llm_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    inbound_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    requires_human: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_capabilities_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    next_actions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    safety_flags_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    input_messages_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    run_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="shadow")
    policy_action: Mapped[str] = mapped_column(String(32), nullable=False, default="discard")
    auto_reply_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_llm_turns_conversation_created", "conversation_id", "created_at"),
        Index("ix_llm_turns_inbound_message", "inbound_message_id"),
    )


class LlmJob(Base):
    __tablename__ = "llm_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    inbound_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_llm_jobs_status_created", "status", "created_at"),)


class OutboundJob(Base):
    __tablename__ = "outbound_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    llm_turn_id: Mapped[int | None] = mapped_column(ForeignKey("llm_turns.id", ondelete="SET NULL"), nullable=True)
    recipient_platform_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reply_text: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(191), nullable=False, unique=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meta_response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_outbound_jobs_status_created", "status", "created_at"),)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
