from dataclasses import dataclass, field

__all__ = ["AgentRequest"]


@dataclass(frozen=True)
class AgentRequest:
    user_text: str
    mode: str
    session_id: str = ""
    context: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
