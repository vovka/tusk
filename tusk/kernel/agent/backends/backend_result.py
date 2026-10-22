from dataclasses import dataclass, field

__all__ = ["BackendResult"]


@dataclass(frozen=True)
class BackendResult:
    handled: bool
    reply: str
    session_id: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
    status: str = ""
    raw_output: object = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", self.status or _status_from_handled(self.handled))


def _status_from_handled(handled: bool) -> str:
    if handled:
        return "success"
    return "failed"
