import re

from tusk.kernel import ToolRegistry

__all__ = ["DesktopProbe"]

_GEOMETRY = re.compile(r"\[(\d+)x(\d+) at (-?\d+),(-?\d+)\]")


class DesktopProbe:
    """Reads desktop state through the same gnome tools the agent uses."""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._tools = tool_registry

    def windows(self) -> str:
        return self._tools.get("gnome.list_windows").execute({}).message

    def active_window(self) -> str:
        return self._tools.get("gnome.get_active_window").execute({}).message

    def geometry(self, title_fragment: str) -> tuple[int, int, int, int] | None:
        for line in self.windows().splitlines():
            if title_fragment.lower() in line.lower():
                return self._parse(line)
        return None

    def _parse(self, line: str) -> tuple[int, int, int, int] | None:
        match = _GEOMETRY.search(line)
        if match is None:
            return None
        width, height, x, y = (int(value) for value in match.groups())
        return x, y, width, height
