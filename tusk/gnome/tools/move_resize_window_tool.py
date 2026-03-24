import subprocess

from tusk.interfaces.agent_tool import AgentTool
from tusk.schemas.tool_result import ToolResult

__all__ = ["MoveResizeWindowTool"]


class MoveResizeWindowTool(AgentTool):
    @property
    def name(self) -> str:
        return "move_resize_window"

    @property
    def description(self) -> str:
        return "Move and resize a window by title and geometry"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"window_title": "<title>", "geometry": "<x>,<y>,<w>,<h>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        title = parameters["window_title"]
        geometry = parameters["geometry"]
        subprocess.run(
            ["wmctrl", "-r", title, "-e", f"0,{geometry}"],
            check=False,
        )
        return ToolResult(success=True, message=f"moved/resized: {title} to {geometry}")
