from dataclasses import dataclass, field

__all__ = ["GateResult"]


@dataclass(frozen=True)
class GateResult:
    is_directed_at_tusk: bool
    cleaned_command: str
    confidence: float
    metadata: dict[str, str] = field(default_factory=dict)
