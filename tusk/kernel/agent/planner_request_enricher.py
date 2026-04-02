from dataclasses import replace

from tusk.kernel.agent.agent_run_request import AgentRunRequest

__all__ = ["PlannerRequestEnricher"]


class PlannerRequestEnricher:
    def enrich(self, request: AgentRunRequest, planner_tool_names: set[str]) -> AgentRunRequest:
        if request.profile_id != "planner":
            return request
        suffix = self._tool_list(planner_tool_names)
        return replace(request, instruction=f"{request.instruction}\n{suffix}")

    def _tool_list(self, names: set[str]) -> str:
        joined = ", ".join(sorted(names))
        return f"Available tool names for selection: {joined}"
