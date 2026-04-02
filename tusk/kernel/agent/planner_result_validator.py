from tusk.kernel.agent.agent_result import AgentResult

__all__ = ["PlannerResultValidator"]


class PlannerResultValidator:
    def validate(self, profile_id: str, result: AgentResult, allowed: set[str]) -> AgentResult:
        if profile_id != "planner" or result.status != "done":
            return result
        valid = self._selected_tools(result, allowed)
        if valid:
            return result
        return AgentResult("failed", result.session_id, self._message(allowed), self._message(allowed))

    def _selected_tools(self, result: AgentResult, allowed: set[str]) -> list[str]:
        items = result.payload.get("selected_tool_names", [])
        return [str(item) for item in items if str(item) in allowed]

    def _message(self, allowed: set[str]) -> str:
        names = ", ".join(sorted(allowed))
        return f"planner returned no valid selected_tool_names; allowed names: {names}"
