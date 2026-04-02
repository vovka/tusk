from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.agent_run_request import AgentRunRequest

__all__ = ["ExecutorToolGuard"]


class ExecutorToolGuard:
    def validate(self, profile_id: str, request: AgentRunRequest, runtime_names: set[str]) -> AgentResult | None:
        if profile_id != "executor":
            return None
        if runtime_names:
            return None
        return AgentResult("need_tools", "", "executor requires runtime tools")
