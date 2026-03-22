import subprocess

from tusk.interfaces.agent_tool import AgentTool
from tusk.schemas.tool_result import ToolResult

__all__ = ["MaximizeWindowTool"]


class MaximizeWindowTool(AgentTool):
    @property
    def name(self) -> str:
        return "maximize_window"

    @property
    def description(self) -> str:
        return "Maximize a window by its title"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"window_title": "<title>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        title = parameters["window_title"]
        subprocess.run(
            ["wmctrl", "-r", title, "-b", "add,maximized_vert,maximized_horz"],
            check=False,
        )
        return ToolResult(success=True, message=f"maximized: {title}")
