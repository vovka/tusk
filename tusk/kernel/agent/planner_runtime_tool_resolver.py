from dataclasses import replace

from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.agent_session_store import AgentSessionStore

__all__ = ["PlannerRuntimeToolResolver"]


class PlannerRuntimeToolResolver:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store

    def resolve(self, request: AgentRunRequest, real_names: set[str]) -> AgentRunRequest:
        if request.profile_id != "executor":
            return request
        if request.runtime_tool_names:
            return request
        resolved = self._from_refs(request.session_refs, real_names)
        return replace(request, runtime_tool_names=tuple(resolved))

    def _from_refs(self, refs: tuple[str, ...], real_names: set[str]) -> list[str]:
        for ref in refs:
            tools = self._extract_tools(ref)
            valid = [name for name in tools if name in real_names]
            if valid:
                return valid
        return []

    def _extract_tools(self, session_id: str) -> list[str]:
        result = self._store.final_result(session_id)
        if result is None:
            return []
        return list(result.payload.get("selected_tool_names", []))
