from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult

__all__ = ["ConversationDelegationGuard"]

_WORKER_PROFILES = {"executor", "default"}


class ConversationDelegationGuard:
    def __init__(self, max_failures: int = 2) -> None:
        self._max_failures = max_failures
        self._failures = 0
        self._child_profile = ""
        self._child_status = ""

    def violation(self, profile_id: str, tool_call: ToolCall) -> str | None:
        if profile_id != "conversation" or tool_call.tool_name != "run_agent":
            return None
        if self._failures >= self._max_failures:
            return "conversation exceeded executor retry budget; call done instead of delegating again"
        if self._child_status == "done" and self._child_profile in _WORKER_PROFILES:
            return f"conversation must call done after {self._child_profile} returns status=done"
        return None

    def observe(self, tool_call: ToolCall, tool_result: ToolResult) -> None:
        child = self._child_result(tool_call, tool_result)
        self._child_profile = str(child.get("profile_id", "")) if child else ""
        self._child_status = str(child.get("status", "")) if child else ""
        if self._child_profile in _WORKER_PROFILES and self._child_status in {"failed", "need_tools"}:
            self._failures += 1

    def _child_result(self, tool_call: ToolCall, tool_result: ToolResult) -> dict[str, object] | None:
        if tool_call.tool_name != "run_agent" or not tool_result.data:
            return None
        child = tool_result.data.get("child_result")
        return child if isinstance(child, dict) else None
