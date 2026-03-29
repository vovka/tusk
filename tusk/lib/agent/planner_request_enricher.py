from dataclasses import replace

from tusk.lib.agent.agent_run_request import AgentRunRequest

__all__ = ["PlannerRequestEnricher"]


class PlannerRequestEnricher:
    def enrich(self, request: AgentRunRequest, tool_names: set[str]) -> AgentRunRequest:
        if request.profile_id != "planner" or not tool_names:
            return request
        return replace(request, instruction=self._instruction(request, tool_names))

    def _instruction(self, request: AgentRunRequest, tool_names: set[str]) -> str:
        names = "\n".join(f"- {name}" for name in sorted(tool_names))
        return f"{request.instruction}\n\nAllowed runtime tool names:\n{names}"
