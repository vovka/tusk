from dataclasses import dataclass

__all__ = ["GateResult"]


@dataclass(frozen=True)
class GateResult:
    is_directed_at_tusk: bool
    cleaned_command: str
    confidence: float
