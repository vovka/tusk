from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.kernel.agent.guards.consecutive_typing_guard import ConsecutiveTypingGuard
from tusk.kernel.agent.guards.conversation_delegation_guard import ConversationDelegationGuard
from tusk.kernel.agent.guards.executor_clipboard_guard import ExecutorClipboardGuard

__all__ = ["TurnGuards"]


class TurnGuards:
    def __init__(self) -> None:
        self._guards = [ConversationDelegationGuard(), ExecutorClipboardGuard()]
        self._typing = ConsecutiveTypingGuard()
        self._last_success: str | None = None

    def violation(self, profile_id: str, tool_call: ToolCall) -> str | None:
        for guard in self._guards:
            message = guard.violation(profile_id, tool_call)
            if message is not None:
                return message
        return None

    def refusal(self, profile_id: str, tool_call: ToolCall) -> ToolResult | None:
        # unlike a violation, a refusal is returned to the model as a failed tool result and the run goes on
        message = self._typing.refusal(profile_id, tool_call)
        return ToolResult(False, message) if message else None

    def observe(self, tool_call: ToolCall, tool_result: ToolResult) -> None:
        self._typing.observe(tool_call, tool_result)
        if tool_result.success:
            self._last_success = tool_result.message
        for guard in self._guards:
            guard.observe(tool_call, tool_result)

    def partial_done(self, profile_id: str) -> ToolCall | None:
        # ponytail: a command whose tool already ran counts as done when only the follow-up LLM call failed;
        # multi-step commands report just the last success, track remaining steps if that misleads users
        if profile_id != "command" or self._last_success is None:
            return None
        return ToolCall("done", {"status": "done", "summary": self._last_success, "text": self._last_success})
