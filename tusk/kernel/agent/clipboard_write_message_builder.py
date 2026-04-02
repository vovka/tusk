from tusk.shared.schemas.tool_call import ToolCall
from tusk.shared.schemas.tool_result import ToolResult

__all__ = ["ClipboardWriteMessageBuilder"]


class ClipboardWriteMessageBuilder:
    def build(self, tool_call: ToolCall, tool_result: ToolResult) -> str | None:
        text = self._clipboard_text(tool_call, tool_result)
        return None if text is None else f"[clipboard-written]\n{text}"

    def _clipboard_text(self, tool_call: ToolCall, tool_result: ToolResult) -> str | None:
        if tool_call.tool_name != "gnome.write_clipboard" or not tool_result.data:
            return None
        text = tool_result.data.get("clipboard_text")
        return text if isinstance(text, str) else None
