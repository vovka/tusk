from dataclasses import dataclass

try:
    from window_info import WindowInfo
except ImportError:  # pragma: no cover
    from adapters.gnome.window_info import WindowInfo

__all__ = ["DesktopContext"]


@dataclass(frozen=True)
class DesktopContext:
    active_window_title: str
    active_application: str
    open_windows: list[WindowInfo]
    available_applications: list[object]
