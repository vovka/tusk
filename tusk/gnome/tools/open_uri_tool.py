import subprocess

from tusk.interfaces.agent_tool import AgentTool
from tusk.schemas.tool_result import ToolResult

__all__ = ["OpenUriTool"]


class OpenUriTool(AgentTool):
    @property
    def name(self) -> str:
        return "open_uri"

    @property
    def description(self) -> str:
        return "Open a URL or file path with the default application"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"uri": "<url_or_path>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        uri = parameters["uri"]
        subprocess.Popen(["xdg-open", uri], start_new_session=True)
        return ToolResult(success=True, message=f"opened: {uri}")
