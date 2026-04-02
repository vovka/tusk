from dataclasses import replace

from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.agent_session_store import AgentSessionStore
from tusk.shared.schemas.tool_sequence_plan import ToolSequencePlan

__all__ = ["PlannerRuntimeToolResolver"]


class PlannerRuntimeToolResolver:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store

    def resolve(self, request: AgentRunRequest, real_names: set[str]) -> AgentRunRequest:
        if request.profile_id != "executor":
            return request
        payload = self._payload(request.session_refs)
        plan = request.sequence_plan or self._plan(payload)
        names = self._names(request, payload, real_names, plan)
        mode = str(payload.get("execution_mode", request.execution_mode))
        return replace(request, runtime_tool_names=tuple(names), execution_mode=mode, sequence_plan=plan)

    def _payload(self, refs: tuple[str, ...]) -> dict[str, object]:
        for ref in refs:
            result = self._store.final_result(ref)
            if result is not None:
                return result.payload
        return {}

    def _tool_names(self, payload: dict[str, object], real_names: set[str]) -> list[str]:
        items = payload.get("selected_tool_names", [])
        return [str(item) for item in items if str(item) in real_names]

    def _plan(self, payload: dict[str, object]) -> ToolSequencePlan | None:
        return ToolSequencePlan.from_dict(payload.get("sequence_plan") or payload.get("planned_steps"))

    def _names(
        self,
        request: AgentRunRequest,
        payload: dict[str, object],
        real_names: set[str],
        plan: ToolSequencePlan | None,
    ) -> tuple[str, ...]:
        if plan is not None:
            return plan.ordered_tool_names()
        return request.runtime_tool_names or tuple(self._tool_names(payload, real_names))
