from collections.abc import Callable
from dataclasses import dataclass

__all__ = ["TrayMenuItem"]


@dataclass(frozen=True)
class TrayMenuItem:
    label: str
    action: Callable[[], None] | None = None
    enabled: bool = False
    children: tuple["TrayMenuItem", ...] = ()
