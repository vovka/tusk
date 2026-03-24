import subprocess

from tusk.interfaces.agent_tool import AgentTool
from tusk.schemas.tool_result import ToolResult

__all__ = ["MinimizeWindowTool"]


class MinimizeWindowTool(AgentTool):
    @property
    def name(self) -> str:
        return "minimize_window"

    @property
    def description(self) -> str:
        return "Minimize a window by its title"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"window_title": "<title>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        title = parameters["window_title"]
        result = subprocess.run(
            ["xdotool", "search", "--name", title],
            capture_output=True,
            text=True,
            check=False,
        )
        window_id = self._first_window_id(result.stdout)
        if not window_id:
            return ToolResult(success=False, message=f"window not found: {title}")
        subprocess.run(["xdotool", "windowminimize", window_id], check=False)
        return ToolResult(success=True, message=f"minimized: {title}")

    def _first_window_id(self, output: str) -> str:
        lines = output.strip().splitlines()
        return lines[0] if lines else ""
