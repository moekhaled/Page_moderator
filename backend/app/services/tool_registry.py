from dataclasses import dataclass

from app.services.llm_contracts import ToolCapability


@dataclass(frozen=True)
class ToolSpec:
    capability: ToolCapability
    title: str
    description: str
    enabled: bool


def build_tool_registry() -> list[ToolSpec]:
    # Tools are declared now and can be implemented in later phases without changing the agent contract.
    return [
        ToolSpec(
            capability=ToolCapability.calendar_read,
            title="Calendar Read",
            description="Read available reservation slots and business calendar constraints.",
            enabled=False,
        ),
        ToolSpec(
            capability=ToolCapability.calendar_write,
            title="Calendar Write",
            description="Create or update reservation events once required checks pass.",
            enabled=False,
        ),
        ToolSpec(
            capability=ToolCapability.whatsapp_verify,
            title="WhatsApp Self Verification",
            description="Verify reservation request with owner or manager by WhatsApp before committing.",
            enabled=False,
        ),
        ToolSpec(
            capability=ToolCapability.deposit_verify,
            title="Deposit Verification",
            description="Verify deposit transfer status before confirming reservation.",
            enabled=False,
        ),
    ]
