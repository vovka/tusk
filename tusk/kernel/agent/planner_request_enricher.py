from dataclasses import replace

from tusk.kernel.agent.agent_run_request import AgentRunRequest

__all__ = ["PlannerRequestEnricher"]


class PlannerRequestEnricher:
    def enrich(self, request: AgentRunRequest, tool_catalog: str) -> AgentRunRequest:
        if request.profile_id != "planner":
            return request
        return replace(request, instruction=f"{request.instruction}\n{tool_catalog}")
