from tusk.kernel.tool_registry import ToolRegistry
from tusk.kernel.agent.agent_profile import AgentProfile
from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.static_tool_schemas import (
    DEFAULT_DONE,
    EXECUTE_TOOL_SEQUENCE,
    PLANNER_DONE,
    RUN_AGENT,
)

__all__ = ["AgentToolsetBuilder"]


class AgentToolsetBuilder:
    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._registry = tool_registry

    def build(self, profile: AgentProfile, request: AgentRunRequest) -> list[dict[str, object]]:
        tools: list[dict[str, object]] = [self._done_tool(profile)]
        self._add_static_tools(tools, profile, request)
        self._add_runtime_tools(tools, profile, request)
        return tools

    def runtime_names(self, profile: AgentProfile, request: AgentRunRequest) -> set[str]:
        if not profile.runtime_allowed_tool_names:
            return set()
        if "*" in profile.runtime_allowed_tool_names:
            return self._filter_runtime(request.runtime_tool_names)
        return set(profile.runtime_allowed_tool_names)

    def _add_static_tools(self, tools: list[dict[str, object]], profile: AgentProfile, request: AgentRunRequest) -> None:
        if "run_agent" in profile.static_tool_names:
            tools.append(self._run_agent_tool())
        if self._sequence_mode(profile, request):
            tools.append(self._sequence_tool())

    def _add_runtime_tools(
        self, tools: list[dict[str, object]], profile: AgentProfile, request: AgentRunRequest,
    ) -> None:
        if self._sequence_mode(profile, request):
            return
        names = self.runtime_names(profile, request)
        if names:
            tools.extend(self._registry.definitions_for(names))

    def _filter_runtime(self, names: tuple[str, ...]) -> set[str]:
        real = self._registry.real_tool_names()
        return {name for name in names if name in real}

    def _done_tool(self, profile: AgentProfile) -> dict[str, object]:
        schema = PLANNER_DONE if profile.profile_id == "planner" else DEFAULT_DONE
        return {"type": "function", "function": {"name": "done", "description": "Finish and return a result.", "parameters": schema}}

    def _run_agent_tool(self) -> dict[str, object]:
        return {"type": "function", "function": {"name": "run_agent", "description": "Delegate work to a sub-agent.", "parameters": RUN_AGENT}}

    def _sequence_tool(self) -> dict[str, object]:
        text = "Execute a validated sequence of sequence-callable tools without extra LLM reasoning."
        return {"type": "function", "function": {"name": "execute_tool_sequence", "description": text, "parameters": EXECUTE_TOOL_SEQUENCE}}

    def _sequence_mode(self, profile: AgentProfile, request: AgentRunRequest) -> bool:
        return profile.profile_id == "executor" and request.execution_mode == "sequence" and request.sequence_plan is not None
