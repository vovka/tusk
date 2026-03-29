from dataclasses import replace

from tusk.lib.agent.agent_run_request import AgentRunRequest
from tusk.lib.agent.agent_session_store import AgentSessionStore

__all__ = ["PlannerRuntimeToolResolver"]


class PlannerRuntimeToolResolver:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store

    def resolve(self, request: AgentRunRequest, allowed: set[str]) -> AgentRunRequest:
        if request.profile_id != "executor" or request.runtime_tool_names:
            return request
        names = self._tool_names(request, allowed)
        return replace(request, runtime_tool_names=tuple(names))

    def _tool_names(self, request: AgentRunRequest, allowed: set[str]) -> list[str]:
        for ref in request.session_refs:
            result = self._store.final_result(ref)
            if result is None:
                continue
            names = result.payload.get("selected_tool_names", [])
            selected = [str(name) for name in names if str(name) in allowed]
            if selected:
                return selected
        return []
