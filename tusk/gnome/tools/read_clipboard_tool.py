from tusk.interfaces.agent_tool import AgentTool
from tusk.interfaces.clipboard_provider import ClipboardProvider
from tusk.schemas.tool_result import ToolResult

__all__ = ["ReadClipboardTool"]


class ReadClipboardTool(AgentTool):
    def __init__(self, clipboard: ClipboardProvider) -> None:
        self._clipboard = clipboard

    @property
    def name(self) -> str:
        return "read_clipboard"

    @property
    def description(self) -> str:
        return "Read the current clipboard contents"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        content = self._clipboard.read()
        if not content:
            return ToolResult(success=False, message="clipboard is empty")
        return ToolResult(success=True, message=content)
