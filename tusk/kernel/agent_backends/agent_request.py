from dataclasses import dataclass, field

__all__ = ["AgentRequest"]


@dataclass(frozen=True)
class AgentRequest:
    user_text: str
    mode: str
    session_id: str = ""
    context: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
    working_directory: str = ""
    timeout_seconds: float | None = None
    environment: dict[str, str] = field(default_factory=dict)
