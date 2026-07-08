from dataclasses import dataclass

from tusk.shared.schemas.gate_classification import GateClassification

__all__ = ["GateResult"]


@dataclass(frozen=True)
class GateResult:
    is_directed_at_tusk: bool
    cleaned_command: str
    confidence: float
    classification: GateClassification = GateClassification.AMBIENT
