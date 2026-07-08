from enum import StrEnum

__all__ = ["GateState"]


class GateState(StrEnum):
    PENDING = "pending"
    CONSUMED = "consumed"
    DROPPED = "dropped"
    FORWARDED = "forwarded"
    RECOVERED = "recovered"
