from tusk.shared.schemas.tool_call import ToolCall
from tusk.shared.schemas.tool_result import ToolResult

__all__ = ["ConversationRunAgentGuard"]


class ConversationRunAgentGuard:
    def __init__(self) -> None:
        self._child_profile = ""
        self._child_status = ""

    def violation(self, profile_id: str, tool_call: ToolCall) -> str | None:
        if profile_id != "conversation" or tool_call.tool_name != "run_agent":
            return None
        if self._child_status != "done":
            return None
        if self._child_profile not in {"executor", "default"}:
            return None
        return f"conversation must call done after {self._child_profile} returns status=done"

    def observe(self, tool_call: ToolCall, tool_result: ToolResult) -> None:
        child = self._child_result(tool_call, tool_result)
        self._child_profile = str(child.get("profile_id", "")) if child else ""
        self._child_status = str(child.get("status", "")) if child else ""

    def _child_result(self, tool_call: ToolCall, tool_result: ToolResult) -> dict[str, object] | None:
        if tool_call.tool_name != "run_agent" or not tool_result.data:
            return None
        child = tool_result.data.get("child_result")
        return child if isinstance(child, dict) else None
