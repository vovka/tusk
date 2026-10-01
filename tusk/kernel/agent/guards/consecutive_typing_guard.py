from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult

__all__ = ["ConsecutiveTypingGuard"]

_TYPE_TEXT = "gnome.type_text"


class ConsecutiveTypingGuard:
    """Refuses typing again right after a successful typing, e.g. a model looping on 'type a poem'."""

    def __init__(self) -> None:
        self._just_typed = False

    def refusal(self, profile_id: str, tool_call: ToolCall) -> str | None:
        if profile_id not in ("executor", "command") or not self._just_typed or tool_call.tool_name != _TYPE_TEXT:
            return None
        return "refused: this text was already typed. If the request is satisfied, call done now."

    def observe(self, tool_call: ToolCall, tool_result: ToolResult) -> None:
        if tool_result.success:
            self._just_typed = tool_call.tool_name == _TYPE_TEXT
