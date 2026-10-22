from enum import StrEnum

__all__ = ["GateAction"]


class GateAction(StrEnum):
    FORWARD_CURRENT = "forward_current"
    FORWARD_RECOVERED = "forward_recovered"
    INTERRUPT = "interrupt"
    DROP = "drop"
