from dataclasses import dataclass, field

from tusk.shared.schemas.tool_sequence_plan import ToolSequencePlan

__all__ = ["AgentRunRequest"]


@dataclass(frozen=True)
class AgentRunRequest:
    instruction: str
    profile_id: str = "default"
    session_id: str = ""
    parent_session_id: str = ""
    parent_call_id: str = ""
    runtime_tool_names: tuple[str, ...] = ()
    session_refs: tuple[str, ...] = ()
    execution_mode: str = "normal"
    sequence_plan: ToolSequencePlan | None = None
    metadata: dict[str, object] = field(default_factory=dict)
