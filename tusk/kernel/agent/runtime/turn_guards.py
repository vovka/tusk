from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.kernel.agent.guards.consecutive_typing_guard import ConsecutiveTypingGuard
from tusk.kernel.agent.guards.conversation_failure_budget_guard import ConversationFailureBudgetGuard
from tusk.kernel.agent.guards.conversation_run_agent_guard import ConversationRunAgentGuard
from tusk.kernel.agent.guards.executor_clipboard_guard import ExecutorClipboardGuard

__all__ = ["TurnGuards"]


class TurnGuards:
    def __init__(self) -> None:
        self._guards = [ConversationRunAgentGuard(), ConversationFailureBudgetGuard(), ExecutorClipboardGuard()]
        self._typing = ConsecutiveTypingGuard()

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
        for guard in self._guards:
            guard.observe(tool_call, tool_result)
