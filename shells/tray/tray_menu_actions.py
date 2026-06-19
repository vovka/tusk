from collections.abc import Callable
from dataclasses import dataclass

__all__ = ["TrayMenuActions"]


@dataclass(frozen=True)
class TrayMenuActions:
    pause: Callable[[], None]
    resume: Callable[[], None]
    open_logs: Callable[[], None]
    restart: Callable[[], None]
    exit: Callable[[], None]
