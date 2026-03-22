from dataclasses import dataclass, field

from tusk.schemas.app_entry import AppEntry

__all__ = ["WindowInfo", "DesktopContext"]


@dataclass(frozen=True)
class WindowInfo:
    window_id: str
    title: str
    application: str
    is_active: bool


@dataclass(frozen=True)
class DesktopContext:
    active_window_title: str
    active_application: str
    open_windows: list[WindowInfo] = field(default_factory=list)
    available_applications: list[AppEntry] = field(default_factory=list)
