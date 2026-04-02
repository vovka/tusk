from dataclasses import dataclass

__all__ = ["RecoveryDecision"]


@dataclass(frozen=True)
class RecoveryDecision:
    action: str
    candidate_id: str = ""
    reason: str = ""
