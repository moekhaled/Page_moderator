import asyncio
import os

os.environ["SESSION_SECRET_KEY"] = "test-secret"
os.environ["LLM_PROVIDER"] = "gemini"
os.environ["LLM_ALLOWED_AUTOREPLY_INTENTS"] = "price_inquiry"
os.environ["LLM_PRICE_INQUIRY_MIN_CONFIDENCE"] = "0.8"

from app.services.llm_contracts import AgentDecision, AgentIntent, PolicyAction
from app.services.reservation_agent import ReservationAgentRuntime


def _decision(intent: AgentIntent, confidence: float = 0.95) -> AgentDecision:
    return AgentDecision(
        intent=intent,
        messages=["sample"],
        confidence=confidence,
        requires_human=False,
        required_capabilities=[],
        next_actions=[],
        safety_flags=[],
    )


def test_policy_allows_only_price_inquiry_with_confidence():
    runtime = ReservationAgentRuntime()
    action, eligible = asyncio.run(runtime.evaluate_policy(_decision(AgentIntent.price_inquiry, 0.92)))
    assert action == PolicyAction.allow_autoreply
    assert eligible is True


def test_policy_blocks_low_confidence_price_inquiry():
    runtime = ReservationAgentRuntime()
    decision = _decision(AgentIntent.price_inquiry, 0.55)
    action, eligible = asyncio.run(runtime.evaluate_policy(decision))
    assert action == PolicyAction.escalate_human
    assert eligible is False
    assert "low_confidence_price_inquiry" in decision.safety_flags


def test_policy_discards_hiring_and_model_and_moderator_intents():
    runtime = ReservationAgentRuntime()
    for intent in [AgentIntent.hiring_inquiry, AgentIntent.model_application, AgentIntent.moderator_message]:
        action, eligible = asyncio.run(runtime.evaluate_policy(_decision(intent, 0.99)))
        assert action == PolicyAction.discard
        assert eligible is False
