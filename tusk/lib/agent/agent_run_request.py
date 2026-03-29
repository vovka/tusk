from dataclasses import dataclass, field

__all__ = ["AgentRunRequest"]


@dataclass(frozen=True)
class AgentRunRequest:
    instruction: str
    profile_id: str = "default"
    session_id: str = ""
    parent_session_id: str = ""
    parent_call_id: str = ""
    runtime_tool_names: tuple[str, ...] = field(default_factory=tuple)
    session_refs: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, object] = field(default_factory=dict)
