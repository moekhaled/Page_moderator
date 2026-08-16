from enum import Enum

from pydantic import BaseModel, Field


class ToolCapability(str, Enum):
    calendar_read = "calendar_read"
    calendar_write = "calendar_write"
    whatsapp_verify = "whatsapp_verify"
    deposit_verify = "deposit_verify"


class AgentIntent(str, Enum):
    price_inquiry = "price_inquiry"
    hiring_inquiry = "hiring_inquiry"
    model_application = "model_application"
    moderator_message = "moderator_message"
    unknown = "unknown"


class PolicyAction(str, Enum):
    allow_autoreply = "allow_autoreply"
    discard = "discard"
    escalate_human = "escalate_human"


class AgentDecision(BaseModel):
    intent: AgentIntent
    messages: list[str] = Field(min_length=1, max_length=6)
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human: bool
    required_capabilities: list[ToolCapability] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)


class LlmRunResult(BaseModel):
    decision: AgentDecision
    model_name: str
    latency_ms: int
    input_messages_count: int
    policy_action: PolicyAction
    auto_reply_eligible: bool
