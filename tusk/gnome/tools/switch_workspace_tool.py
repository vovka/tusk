import subprocess

from tusk.interfaces.agent_tool import AgentTool
from tusk.schemas.tool_result import ToolResult

__all__ = ["SwitchWorkspaceTool"]


class SwitchWorkspaceTool(AgentTool):
    @property
    def name(self) -> str:
        return "switch_workspace"

    @property
    def description(self) -> str:
        return "Switch to a virtual desktop by number"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"workspace_number": "<n>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        number = parameters["workspace_number"]
        subprocess.run(["wmctrl", "-s", number], check=False)
        return ToolResult(success=True, message=f"switched to workspace: {number}")
