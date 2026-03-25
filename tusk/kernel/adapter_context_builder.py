from tusk.kernel.schemas.app_entry import AppEntry
from tusk.kernel.schemas.desktop_context import DesktopContext
from tusk.kernel.schemas.window_info import WindowInfo

__all__ = ["AdapterContextBuilder"]


class AdapterContextBuilder:
    def build(self, result: dict | None) -> DesktopContext:
        if result is None:
            return DesktopContext("", "")
        return DesktopContext(
            active_window_title=result.get("active_window_title", ""),
            active_application=result.get("active_application", ""),
            open_windows=[WindowInfo(**item) for item in result.get("open_windows", [])],
            available_applications=[AppEntry(**item) for item in result.get("available_applications", [])],
        )
