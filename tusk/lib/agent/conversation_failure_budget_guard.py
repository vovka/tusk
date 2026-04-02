from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.schemas.tool_result import ToolResult

__all__ = ["ConversationFailureBudgetGuard"]


class ConversationFailureBudgetGuard:
    def __init__(self, max_failures: int = 2) -> None:
        self._max_failures = max_failures
        self._failures = 0

    def violation(self, profile_id: str, tool_call: ToolCall) -> str | None:
        if profile_id != "conversation" or tool_call.tool_name != "run_agent":
            return None
        if self._failures < self._max_failures:
            return None
        return "conversation exceeded executor retry budget; call done instead of delegating again"

    def observe(self, tool_call: ToolCall, tool_result: ToolResult) -> None:
        if self._failed_child(tool_call, tool_result):
            self._failures += 1

    def _failed_child(self, tool_call: ToolCall, tool_result: ToolResult) -> bool:
        if tool_call.tool_name != "run_agent" or not tool_result.data:
            return False
        child = tool_result.data.get("child_result")
        if not isinstance(child, dict):
            return False
        status = str(child.get("status", ""))
        profile_id = str(child.get("profile_id", ""))
        return profile_id in {"executor", "default"} and status in {"failed", "need_tools"}
