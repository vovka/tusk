import subprocess

from tusk.interfaces.agent_tool import AgentTool
from tusk.schemas.tool_result import ToolResult

__all__ = ["CloseWindowTool"]


class CloseWindowTool(AgentTool):
    @property
    def name(self) -> str:
        return "close_window"

    @property
    def description(self) -> str:
        return "Close a window by its title"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"window_title": "<title>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        window_title = parameters["window_title"]
        subprocess.run(["wmctrl", "-c", window_title], check=False)
        return ToolResult(success=True, message=f"closed: {window_title}")
