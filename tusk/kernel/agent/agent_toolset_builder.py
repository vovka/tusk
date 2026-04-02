from tusk.kernel.tool_registry import ToolRegistry
from tusk.kernel.agent.agent_profile import AgentProfile
from tusk.kernel.agent.agent_run_request import AgentRunRequest

__all__ = ["AgentToolsetBuilder"]


class AgentToolsetBuilder:
    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._registry = tool_registry

    def build(self, profile: AgentProfile, request: AgentRunRequest) -> list[dict[str, object]]:
        tools: list[dict[str, object]] = [self._done_tool(profile)]
        self._add_static_tools(tools, profile)
        self._add_runtime_tools(tools, profile, request)
        return tools

    def runtime_names(self, profile: AgentProfile, request: AgentRunRequest) -> set[str]:
        if not profile.runtime_allowed_tool_names:
            return set()
        if "*" in profile.runtime_allowed_tool_names:
            return self._filter_runtime(request.runtime_tool_names)
        return set(profile.runtime_allowed_tool_names)

    def _add_static_tools(self, tools: list[dict[str, object]], profile: AgentProfile) -> None:
        if "run_agent" in profile.static_tool_names:
            tools.append(self._run_agent_tool())
        if "list_available_tools" in profile.static_tool_names:
            tools.append(self._list_tools_tool())

    def _add_runtime_tools(
        self, tools: list[dict[str, object]], profile: AgentProfile, request: AgentRunRequest,
    ) -> None:
        names = self.runtime_names(profile, request)
        if names:
            tools.extend(self._registry.definitions_for(names))

    def _filter_runtime(self, names: tuple[str, ...]) -> set[str]:
        real = self._registry.real_tool_names()
        return {name for name in names if name in real}

    def _done_tool(self, profile: AgentProfile) -> dict[str, object]:
        schema = _PLANNER_DONE if profile.profile_id == "planner" else _DEFAULT_DONE
        return {"type": "function", "function": {"name": "done", "description": "Finish and return a result.", "parameters": schema}}

    def _run_agent_tool(self) -> dict[str, object]:
        return {"type": "function", "function": {"name": "run_agent", "description": "Delegate work to a sub-agent.", "parameters": _RUN_AGENT}}

    def _list_tools_tool(self) -> dict[str, object]:
        return {"type": "function", "function": {"name": "list_available_tools", "description": "List available runtime tools.", "parameters": _LIST_TOOLS}}


_DEFAULT_DONE: dict[str, object] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["done", "clarify", "unknown", "failed", "need_tools"]},
        "summary": {"type": "string"},
        "text": {"type": "string"},
        "payload": {"type": "object"},
        "artifact_refs": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["status", "summary"],
    "additionalProperties": False,
}

_PLANNER_DONE: dict[str, object] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["done", "clarify", "unknown", "failed"]},
        "summary": {"type": "string"},
        "text": {"type": "string"},
        "payload": {
            "type": "object",
            "properties": {
                "selected_tool_names": {"type": "array", "items": {"type": "string"}},
                "plan_text": {"type": "string"},
            },
            "required": ["selected_tool_names"],
        },
        "artifact_refs": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["status", "summary"],
    "additionalProperties": False,
}

_RUN_AGENT: dict[str, object] = {
    "type": "object",
    "properties": {
        "profile_id": {"type": "string", "enum": ["planner", "executor", "default"]},
        "instruction": {"type": "string"},
        "runtime_tool_names": {"type": "array", "items": {"type": "string"}},
        "session_refs": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["profile_id", "instruction"],
    "additionalProperties": False,
}

_LIST_TOOLS: dict[str, object] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}
