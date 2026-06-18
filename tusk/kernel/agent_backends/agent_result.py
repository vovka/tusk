from dataclasses import dataclass, field

__all__ = ["AgentResult"]


@dataclass(frozen=True)
class AgentResult:
    handled: bool
    reply: str
    session_id: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
    status: str = ""
    final_text: str = ""
    raw_output: object = None

    def __post_init__(self) -> None:
        status = self.status or _status_from_handled(self.handled)
        final_text = self.final_text or self.reply
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "final_text", final_text)


def _status_from_handled(handled: bool) -> str:
    if handled:
        return "success"
    return "failed"
