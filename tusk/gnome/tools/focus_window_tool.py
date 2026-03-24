import subprocess

from tusk.interfaces.agent_tool import AgentTool
from tusk.schemas.tool_result import ToolResult

__all__ = ["FocusWindowTool"]


class FocusWindowTool(AgentTool):
    @property
    def name(self) -> str:
        return "focus_window"

    @property
    def description(self) -> str:
        return "Bring a window to the foreground by its title"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"window_title": "<title>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        title = parameters["window_title"]
        subprocess.run(["wmctrl", "-a", title], check=False)
        return ToolResult(success=True, message=f"focused: {title}")
