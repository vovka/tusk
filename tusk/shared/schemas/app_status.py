from enum import Enum

__all__ = ["AppStatus"]


class AppStatus(Enum):
    STARTING = "starting"
    LISTENING = "listening"
    REACTING = "reacting"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"
