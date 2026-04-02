from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.lib.agent.conversation_failure_budget_guard import ConversationFailureBudgetGuard
from tusk.lib.agent.conversation_run_agent_guard import ConversationRunAgentGuard
from tusk.lib.agent.executor_clipboard_guard import ExecutorClipboardGuard

__all__ = ["RuntimeTurnGuards"]


class RuntimeTurnGuards:
    def __init__(self) -> None:
        self._guards = [ConversationRunAgentGuard(), ConversationFailureBudgetGuard(), ExecutorClipboardGuard()]

    def violation(self, profile_id: str, tool_call: ToolCall) -> str | None:
        for guard in self._guards:
            message = guard.violation(profile_id, tool_call)
            if message is not None:
                return message
        return None

    def observe(self, tool_call: ToolCall, tool_result: ToolResult) -> None:
        for guard in self._guards:
            guard.observe(tool_call, tool_result)
