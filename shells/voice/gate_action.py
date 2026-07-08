from enum import StrEnum

__all__ = ["GateAction"]


class GateAction(StrEnum):
    FORWARD_CURRENT = "forward_current"
    FORWARD_RECOVERED = "forward_recovered"
    FORWARD_CLARIFICATION = "forward_clarification"
    INTERRUPT = "interrupt"
    DROP = "drop"
