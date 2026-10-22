from enum import StrEnum

__all__ = ["GateClassification"]


class GateClassification(StrEnum):
    COMMAND = "command"
    CONVERSATION = "conversation"
    AMBIENT = "ambient"
    INTERRUPT = "interrupt"
