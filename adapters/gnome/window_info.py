from dataclasses import dataclass

__all__ = ["WindowInfo"]


@dataclass(frozen=True)
class WindowInfo:
    window_id: str
    title: str
    application: str
    is_active: bool
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
