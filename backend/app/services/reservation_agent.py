from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import settings
from app.services.llm_contracts import AgentDecision, AgentIntent, LlmRunResult, PolicyAction
from app.services.tool_registry import build_tool_registry


class ReservationAgentRuntime:
    def __init__(self) -> None:
        self._tool_specs = build_tool_registry()
        self._system_prompt_template = self._load_system_prompt_template()

    def _load_system_prompt_template(self) -> str:
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "reservation_system_prompt.txt"
        if not prompt_path.exists():
            raise RuntimeError(f"System prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    def _build_system_prompt(self) -> str:
        tool_lines = []
        for tool in self._tool_specs:
            tool_lines.append(f"- {tool.capability.value}: enabled={str(tool.enabled).lower()} - {tool.description}")

        return self._system_prompt_template.format(tool_lines="\n".join(tool_lines))

    def _build_messages(self, history: list[dict]) -> list[BaseMessage]:
        messages: list[BaseMessage] = [SystemMessage(content=self._build_system_prompt())]
        for item in history:
            role = item.get("role")
            content = item.get("content", "")
            if role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        return messages

    def _build_model(self):
        provider = settings.llm_provider.strip().lower()
        if provider == "gemini":
            if not settings.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
            return ChatGoogleGenerativeAI(
                model=settings.llm_model,
                google_api_key=settings.gemini_api_key,
                temperature=settings.llm_temperature,
                timeout=settings.llm_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )

        if provider == "openai":
            if not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
            return ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.openai_api_key,
                temperature=settings.llm_temperature,
                timeout=settings.llm_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )

        raise RuntimeError("Unsupported LLM_PROVIDER. Use gemini or openai.")

    async def evaluate_policy(self, decision: AgentDecision) -> tuple[PolicyAction, bool]:
        if decision.intent in {AgentIntent.hiring_inquiry, AgentIntent.model_application, AgentIntent.moderator_message}:
            return (PolicyAction.discard, False)

        if decision.intent != AgentIntent.price_inquiry:
            return (PolicyAction.escalate_human, False)

        if decision.confidence < settings.llm_price_inquiry_min_confidence:
            decision.safety_flags.append("low_confidence_price_inquiry")
            decision.requires_human = True
            return (PolicyAction.escalate_human, False)

        allowed = {x.strip() for x in settings.llm_allowed_autoreply_intents.split(",") if x.strip()}
        if decision.intent.value not in allowed:
            decision.safety_flags.append("intent_not_in_allowlist")
            decision.requires_human = True
            return (PolicyAction.escalate_human, False)

        if decision.requires_human:
            return (PolicyAction.escalate_human, False)

        return (PolicyAction.allow_autoreply, True)

    async def run(self, history: list[dict]) -> LlmRunResult:
        llm = self._build_model()
        model = llm.with_structured_output(AgentDecision)
        messages = self._build_messages(history)
        started = datetime.now(timezone.utc)
        decision = await model.ainvoke(messages)
        latency_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        policy_action, auto_reply_eligible = await self.evaluate_policy(decision)

        return LlmRunResult(
            decision=decision,
            model_name=f"{settings.llm_provider}:{settings.llm_model}",
            latency_ms=latency_ms,
            input_messages_count=len(messages),
            policy_action=policy_action,
            auto_reply_eligible=auto_reply_eligible,
        )
