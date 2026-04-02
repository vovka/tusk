from dataclasses import dataclass, field

from tusk.shared.schemas.app_entry import AppEntry
from tusk.shared.schemas.window_info import WindowInfo

__all__ = ["DesktopContext"]


@dataclass(frozen=True)
class DesktopContext:
    active_window_title: str
    active_application: str
    open_windows: list[WindowInfo] = field(default_factory=list)
    available_applications: list[AppEntry] = field(default_factory=list)
