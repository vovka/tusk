from collections.abc import Callable

from tusk.kernel.agent.agent_profile import AgentProfile
from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.runtime_cancellation import RuntimeCancellation
from tusk.kernel.agent.runtime_turn_guards import RuntimeTurnGuards
from tusk.kernel.repeated_tool_call_guard import RepeatedToolCallGuard
from tusk.shared.schemas import ToolCall, ToolResult

__all__ = ["RuntimeTurnRunner"]


class RuntimeTurnRunner:
    def __init__(self, cancellation: RuntimeCancellation) -> None:
        self._cancel = cancellation

    def run(
        self, session_id: str, profile: AgentProfile, tools: list[dict[str, object]],
        messages: list[dict[str, str]], executor: Callable[[ToolCall, str], ToolResult],
        repeat: RepeatedToolCallGuard, guards: RuntimeTurnGuards, step: int,
        step_runner: Callable[..., AgentResult | None],
    ) -> AgentResult | None:
        cancelled = self._cancel.check(session_id)
        if cancelled is not None:
            return cancelled
        result = step_runner(session_id, profile, tools, messages, executor, repeat, guards, step)
        return self._cancel.check(session_id) or result
