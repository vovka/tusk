from tusk.lib.agent.agent_result import AgentResult
from tusk.lib.agent.agent_run_request import AgentRunRequest

__all__ = ["ExecutorToolGuard"]


class ExecutorToolGuard:
    def validate(self, profile_id: str, request: AgentRunRequest, tool_names: set[str]) -> AgentResult | None:
        if profile_id != "executor":
            return None
        if tool_names:
            return None
        return AgentResult("need_tools", request.session_id, self._message(), self._message())

    def _message(self) -> str:
        return "executor started without runtime tools"
