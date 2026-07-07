from dataclasses import dataclass

from tusk.shared.schemas.window_info import WindowInfo

__all__ = ["DesktopContext"]


@dataclass(frozen=True)
class DesktopContext:
    active_window_title: str
    active_application: str
    open_windows: list[WindowInfo]
    available_applications: list[object]
