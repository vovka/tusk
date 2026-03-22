from tusk.interfaces.agent_tool import AgentTool
from tusk.interfaces.clipboard_provider import ClipboardProvider
from tusk.schemas.tool_result import ToolResult

__all__ = ["WriteClipboardTool"]


class WriteClipboardTool(AgentTool):
    def __init__(self, clipboard: ClipboardProvider) -> None:
        self._clipboard = clipboard

    @property
    def name(self) -> str:
        return "write_clipboard"

    @property
    def description(self) -> str:
        return "Write text to the clipboard"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"text": "<text>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        text = parameters["text"]
        self._clipboard.write(text)
        return ToolResult(success=True, message=f"clipboard set: {text[:50]}")
