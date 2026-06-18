from dataclasses import dataclass, field

__all__ = ["AgentResult"]


@dataclass(frozen=True)
class AgentResult:
    handled: bool
    reply: str
    session_id: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
